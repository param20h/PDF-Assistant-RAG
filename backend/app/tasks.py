"""Celery tasks for document processing."""
import logging
import traceback
from datetime import datetime, timezone

import httpx

from app.celery_app import celery_app
from app.database import get_db_session
from app.exceptions import (
    ExternalServiceException,
    RateLimitException,
)
from app.models import Document
from app.services.document_ingestion import ingest_document as _ingest_document

logger = logging.getLogger(__name__)

# Errors that are worth retrying. ValidationException, NotFoundException,
# UnauthorizedException, ForbiddenException, ConflictException, UnsafePromptException,
# ValueError, KeyError, TypeError and other programming bugs are intentionally
# excluded: re-running them just wastes worker time and hits external APIs.
TRANSIENT_ERRORS: tuple[type[BaseException], ...] = (
    ExternalServiceException,
    RateLimitException,
    ConnectionError,
    TimeoutError,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.ConnectTimeout,
    httpx.RemoteProtocolError,
    httpx.NetworkError,
    OSError,
)


@celery_app.task(
    bind=True,
    name="app.tasks.process_document",
    max_retries=3,
    autoretry_for=TRANSIENT_ERRORS,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_document(
    self,
    document_id: str,
    filepath: str,
    original_name: str,
    user_id: str,
) -> dict[str, str]:
    """Run the RAG ingestion pipeline for a stored document.

    This task is a thin dispatch wrapper around
    ``app.services.document_ingestion.ingest_document``, which is the single
    source of truth for the ingestion state machine (status, progress,
    chunk_count, page_count, summary, URL extraction, knowledge graph, and
    vector storage). The task itself only records retry bookkeeping before
    delegating; it does not open a second DB session that writes the same
    Document row, since ingest_document manages its own SessionLocal()
    session end-to-end and commits/rolls back independently.
    """
    with get_db_session() as db:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.processing_started_at = datetime.now(timezone.utc)
            doc.retry_count = (doc.retry_count or 0) + 1
            db.commit()

    logger.info("Dispatching ingestion pipeline for document: %s", original_name)

    try:
        _ingest_document(
            document_id=document_id,
            filepath=filepath,
            original_name=original_name,
            user_id=user_id,
        )
    except Exception as exc:
        is_transient = isinstance(exc, TRANSIENT_ERRORS)
        logger.error(
            "Document %s processing failed (attempt %s, transient=%s): %s",
            document_id,
            self.request.retries + 1,
            is_transient,
            exc,
        )
        with get_db_session() as db:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                # For non-transient errors, retrying won't help - mark failed now.
                # For transient errors, only mark failed once retries are exhausted.
                should_mark_failed = (
                    not is_transient
                    or self.request.retries >= (self.max_retries or 3) - 1
                )
                if should_mark_failed:
                    doc.status = "failed"
                    doc.last_error_traceback = traceback.format_exc()[:2000]
                    doc.processing_progress = 0
                    db.commit()
        raise

    with get_db_session() as db:
        doc = db.query(Document).filter(Document.id == document_id).first()
        final_status = doc.status if doc else "unknown"

    if final_status == "failed":
        raise RuntimeError(
            f"Ingestion pipeline marked document {document_id} as failed"
        )

    return {"document_id": document_id, "status": final_status}
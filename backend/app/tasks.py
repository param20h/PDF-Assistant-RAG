"""Celery tasks for document processing."""
import logging
import traceback
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.database import get_db_session
from app.models import Document
from app.services.document_ingestion import ingest_document as _ingest_document

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.process_document",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
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
        logger.error(
            "Document %s processing failed (attempt %s): %s",
            document_id,
            self.request.retries + 1,
            exc,
        )
        with get_db_session() as db:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc and self.request.retries >= (self.max_retries or 3) - 1:
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
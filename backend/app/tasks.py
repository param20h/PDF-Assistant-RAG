"""Celery tasks for document processing."""
import traceback
import logging

from app.celery_app import celery_app
from app.services.document_ingestion import ingest_document
from app.database import get_db_session
from app.models import Document

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
    """Run the RAG ingestion pipeline for a stored document."""
    try:
        with get_db_session() as db:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.processing_started_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                doc.retry_count = (doc.retry_count or 0) + 1
                db.commit()

        ingest_document(
            document_id=document_id,
            filepath=filepath,
            original_name=original_name,
            user_id=user_id,
        )
        return {"document_id": document_id, "status": "completed"}
    except Exception as exc:
        logger.error("Document %s processing failed (attempt %s): %s", document_id, self.request.retries + 1, exc)
        with get_db_session() as db:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc and self.request.retries >= (self.max_retries or 3) - 1:
                doc.status = "failed"
                doc.last_error_traceback = traceback.format_exc()[:2000]
                doc.processing_progress = 0
                db.commit()
        raise


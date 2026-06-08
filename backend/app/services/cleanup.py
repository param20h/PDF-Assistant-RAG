"""Background cleanup jobs for stale and deleted documents."""
import logging
from datetime import datetime, timedelta, timezone

from app.database import get_db_session
from app.config import get_settings
from app.models import Document

logger = logging.getLogger(__name__)
settings = get_settings()


def cleanup_stale_documents():
    """Mark documents stuck in 'processing' beyond the timeout as failed."""
    timeout_minutes = settings.DOC_PROCESSING_TIMEOUT_MINUTES
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

    with get_db_session() as db:
        stale = (
            db.query(Document)
            .filter(
                Document.status == "processing",
                Document.processing_started_at.isnot(None),
                Document.processing_started_at < cutoff,
                Document.is_deleted.is_(False),
            )
            .all()
        )

        for doc in stale:
            logger.warning(
                "Recovering stale document %s (stuck at '%s' since %s)",
                doc.id,
                doc.processing_stage,
                doc.processing_started_at,
            )
            doc.status = "failed"
            doc.processing_progress = 0
            doc.error_message = f"Processing timed out after {timeout_minutes} minutes"
            doc.last_error_traceback = "Timed out: no progress update received within the configured timeout window."

        if stale:
            logger.info("Marked %d stale document(s) as failed", len(stale))


def cleanup_old_deleted_documents():
    """Permanently delete documents soft-deleted beyond the max age."""
    max_age_days = settings.DOC_CLEANUP_MAX_AGE_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    with get_db_session() as db:
        old = (
            db.query(Document)
            .filter(
                Document.is_deleted.is_(True),
                Document.deleted_at.isnot(None),
                Document.deleted_at < cutoff,
            )
            .all()
        )

        for doc in old:
            logger.info(
                "Purging old deleted document %s ('%s', deleted %s)",
                doc.id,
                doc.original_name,
                doc.deleted_at,
            )
            try:
                from app.rag.vectorstore import delete_document_chunks

                delete_document_chunks(document_id=doc.id, user_id=doc.user_id)
            except Exception as e:
                logger.warning("Error cleaning vectors for %s: %s", doc.id, e)

            try:
                import os

                filepath = os.path.join(settings.UPLOAD_DIR, doc.user_id, doc.filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                logger.warning("Error deleting file for %s: %s", doc.id, e)

            db.delete(doc)

        if old:
            logger.info("Permanently deleted %d old document(s)", len(old))

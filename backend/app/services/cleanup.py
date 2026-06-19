"""Background cleanup jobs for stale, inactive, and deleted documents.

All cleanup functions use batched pagination and transaction-safe patterns
to avoid race conditions, double-deletes, and database lock contention.
"""
import logging
from datetime import datetime, timedelta, timezone

from app.database import get_db_session
from app.config import get_settings
from app.models import Document

logger = logging.getLogger(__name__)
settings = get_settings()

_CLEANUP_BATCH_SIZE = 100


def _hard_delete_document(db, doc):
    """Perform the three-step permanent deletion for a single document.

    Wrapped in try/except so that a failure on one document does not block
    the remaining documents in the batch.
    """
    doc_id = doc.id
    user_id = doc.user_id
    name = doc.original_name

    try:
        from app.rag.vectorstore import delete_document_chunks
        delete_document_chunks(document_id=doc_id, user_id=user_id)
    except Exception as e:
        logger.warning("Cleanup: error deleting vectors for %s: %s", doc_id, e)

    try:
        import os
        filepath = os.path.join(settings.UPLOAD_DIR, user_id, doc.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        logger.warning("Cleanup: error deleting file for %s: %s", doc_id, e)

    try:
        db.delete(doc)
    except Exception as e:
        logger.warning("Cleanup: error deleting DB record for %s: %s", doc_id, e)


def cleanup_stale_documents():
    """Mark documents stuck in 'processing' beyond the timeout as failed."""
    timeout_minutes = settings.DOC_PROCESSING_TIMEOUT_MINUTES
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

    with get_db_session() as db:
        offset = 0
        while True:
            batch = (
                db.query(Document)
                .filter(
                    Document.status == "processing",
                    Document.processing_started_at.isnot(None),
                    Document.processing_started_at < cutoff,
                    Document.is_deleted.is_(False),
                )
                .limit(_CLEANUP_BATCH_SIZE)
                .offset(offset)
                .all()
            )
            if not batch:
                break
            for doc in batch:
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
                logger.info("Marked stale document %s as failed", doc.id)
            offset += _CLEANUP_BATCH_SIZE


def cleanup_old_deleted_documents():
    """Permanently delete documents soft-deleted beyond the max age."""
    max_age_days = settings.DOC_CLEANUP_MAX_AGE_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    with get_db_session() as db:
        offset = 0
        while True:
            batch = (
                db.query(Document)
                .filter(
                    Document.is_deleted.is_(True),
                    Document.deleted_at.isnot(None),
                    Document.deleted_at < cutoff,
                )
                .limit(_CLEANUP_BATCH_SIZE)
                .offset(offset)
                .all()
            )
            if not batch:
                break
            for doc in batch:
                logger.info(
                    "Purging old deleted document %s ('%s', deleted %s)",
                    doc.id,
                    doc.original_name,
                    doc.deleted_at,
                )
                _hard_delete_document(db, doc)
                logger.info(
                    "Permanently deleted old document %s ('%s')",
                    doc.id,
                    doc.original_name,
                )
            offset += _CLEANUP_BATCH_SIZE


def cleanup_inactive_active_documents():
    """Hard-delete active documents that have not been accessed for the
    configured inactivity period.

    Only runs when ``DOC_CLEANUP_ENABLED`` is ``True``.
    Uses batched pagination and filters out soft-deleted records to avoid
    overlap with ``cleanup_old_deleted_documents``.
    """
    if not settings.DOC_CLEANUP_ENABLED:
        logger.info("Inactive document cleanup is disabled via DOC_CLEANUP_ENABLED")
        return

    inactive_days = settings.DOC_CLEANUP_INACTIVE_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=inactive_days)

    with get_db_session() as db:
        offset = 0
        while True:
            batch = (
                db.query(Document)
                .filter(
                    Document.is_deleted.is_(False),
                    Document.last_accessed_at < cutoff,
                )
                .limit(_CLEANUP_BATCH_SIZE)
                .offset(offset)
                .all()
            )
            if not batch:
                break
            for doc in batch:
                logger.info(
                    "Purging inactive active document %s ('%s', last accessed %s)",
                    doc.id,
                    doc.original_name,
                    doc.last_accessed_at,
                )
                _hard_delete_document(db, doc)
                logger.info(
                    "Purged inactive active document %s ('%s')",
                    doc.id,
                    doc.original_name,
                )
            offset += _CLEANUP_BATCH_SIZE

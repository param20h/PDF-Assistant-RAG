"""
Cleanup script for ChromaDB vectors and records of documents inactive for 30 days.

By default, a document is considered inactive if it has not been accessed (last_accessed_at)
or uploaded (if last_accessed_at is missing) for 30 days.

Run manually:
    python backend/scripts/document_cleanup.py

Environment:
    DOCUMENT_CLEANUP_INACTIVE_DAYS=30
    DOCUMENT_CLEANUP_DRY_RUN=true
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import or_, inspect, text

# Allow running this file directly from the repository root.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal  # noqa: E402
from app.models import Document  # noqa: E402
from app.rag.vectorstore import delete_document_chunks  # noqa: E402
from app.config import get_settings  # noqa: E402

logger = logging.getLogger("document_cleanup")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

settings = get_settings()

def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def ensure_last_accessed_at_column() -> None:
    """Ensure last_accessed_at column exists in database (handles SQLite local installs)."""
    db = SessionLocal()
    try:
        bind = db.get_bind()
        inspector = inspect(bind)
        columns = {column["name"] for column in inspector.get_columns("documents")}
        if "last_accessed_at" not in columns:
            logger.info("Adding missing documents.last_accessed_at column")
            db.execute(text("ALTER TABLE documents ADD COLUMN last_accessed_at TIMESTAMP"))
            db.commit()
    finally:
        db.close()


def cleanup_inactive_documents(
    inactive_days: int | None = None,
    dry_run: bool | None = None,
) -> dict[str, int]:
    """Delete database records, physical files, and Chroma collections for inactive documents."""
    ensure_last_accessed_at_column()

    days = inactive_days or int(os.getenv("DOCUMENT_CLEANUP_INACTIVE_DAYS", "30"))
    is_dry_run = _env_bool("DOCUMENT_CLEANUP_DRY_RUN", False) if dry_run is None else dry_run
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stats = {
        "scanned": 0,
        "eligible": 0,
        "deleted": 0,
        "failed": 0,
    }

    db = SessionLocal()
    try:
        # Select documents whose last_accessed_at or uploaded_at is before cutoff
        docs = db.query(Document).filter(
            or_(
                Document.last_accessed_at < cutoff,
                Document.last_accessed_at.is_(None) & (Document.uploaded_at < cutoff)
            )
        ).all()

        for doc in docs:
            stats["scanned"] += 1
            last_activity = doc.last_accessed_at or doc.uploaded_at
            
            stats["eligible"] += 1
            logger.info(
                "Document %s ('%s') inactive since %s; purging dry_run=%s",
                doc.id,
                doc.original_name,
                last_activity,
                is_dry_run,
            )

            if is_dry_run:
                continue

            try:
                # 1. Delete file from disk
                filepath = os.path.join(settings.UPLOAD_DIR, doc.user_id, doc.filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.info("Deleted physical file: %s", filepath)

                # 2. Delete vectors from ChromaDB
                delete_document_chunks(document_id=doc.id, user_id=doc.user_id)

                # 3. Delete from SQL database
                db.delete(doc)
                stats["deleted"] += 1
            except Exception as exc:
                stats["failed"] += 1
                logger.warning(
                    "Failed purging document %s: %s",
                    doc.id,
                    exc,
                    exc_info=True,
                )

        if not is_dry_run:
            db.commit()

        logger.info("Document cleanup complete: %s", stats)
        return stats
    finally:
        db.close()


if __name__ == "__main__":
    cleanup_inactive_documents()

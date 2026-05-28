"""
Cleanup script for ChromaDB vectors belonging to inactive users.

By default, a user is considered inactive if they have not logged in for
30 days. Users without last_login are skipped to avoid deleting vectors for
legacy accounts before activity tracking existed.

Run manually:
    python backend/scripts/vector_cleanup.py

Environment:
    VECTOR_CLEANUP_INACTIVE_DAYS=30
    VECTOR_CLEANUP_DRY_RUN=true
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import inspect, or_, text

# Allow running this file directly from the repository root.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.rag.vectorstore import delete_user_collection  # noqa: E402

logger = logging.getLogger("vector_cleanup")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}



def ensure_last_login_column() -> None:
    """Add users.last_login for SQLite installs that do not run migrations."""
    db = SessionLocal()
    try:
        bind = db.get_bind()
        inspector = inspect(bind)
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "last_login" not in columns:
            logger.info("Adding missing users.last_login column")
            db.execute(text("ALTER TABLE users ADD COLUMN last_login DATETIME"))
            db.commit()
    finally:
        db.close()


def cleanup_inactive_user_vectors(
    inactive_days: int | None = None,
    dry_run: bool | None = None,
) -> dict[str, int]:
    """Delete Chroma collections for users inactive past the threshold."""
    ensure_last_login_column()

    days = inactive_days or int(os.getenv("VECTOR_CLEANUP_INACTIVE_DAYS", "30"))
    is_dry_run = _env_bool("VECTOR_CLEANUP_DRY_RUN", False) if dry_run is None else dry_run
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stats = {
        "scanned": 0,
        "eligible": 0,
        "deleted": 0,
        "skipped_no_login": 0,
        "failed": 0,
    }

    db = SessionLocal()
    try:
        users = db.query(User).filter(
            or_(User.last_login.is_(None), User.last_login < cutoff)
        ).all()

        for user in users:
            stats["scanned"] += 1

            if user.last_login is None:
                stats["skipped_no_login"] += 1
                logger.info(
                    "Skipping user %s because last_login is missing",
                    user.id,
                )
                continue

            stats["eligible"] += 1
            logger.info(
                "User %s inactive since %s; deleting collection=%s dry_run=%s",
                user.id,
                user.last_login,
                f"user_{user.id.replace('-', '_')}"[:63],
                is_dry_run,
            )

            if is_dry_run:
                continue

            try:
                delete_user_collection(user.id)
                stats["deleted"] += 1
            except Exception as exc:  # defensive script boundary
                stats["failed"] += 1
                logger.warning(
                    "Failed deleting vector collection for user %s: %s",
                    user.id,
                    exc,
                    exc_info=True,
                )

        logger.info("Vector cleanup complete: %s", stats)
        return stats
    finally:
        db.close()


if __name__ == "__main__":
    cleanup_inactive_user_vectors()

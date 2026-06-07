"""
SQLAlchemy database setup with SQLite.
Uses synchronous SQLAlchemy for simplicity and compatibility.
"""
import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# ── Engine & Session ─────────────────────────────────
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if is_sqlite:
    # ── Ensure data directory exists ─────────────────────
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if db_path and os.path.dirname(db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},  # Required for SQLite
        echo=settings.DEBUG,
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()



def get_db():
    """FastAPI dependency — yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """Sync context manager for background tasks and streaming.

    Creates a new session, commits on success, rolls back on error,
    and always closes. Safe to use outside FastAPI's DI lifecycle.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _migrate_schema():
    """Apply schema migrations for existing databases (SQLite-compatible).

    SQLAlchemy's ``create_all`` only creates new tables and does **not**
    add missing columns to existing tables.  This helper fills that gap
    for non-destructive changes such as new nullable columns.
    """
    inspector = inspect(engine)
    # Migrate users
    existing_users_columns = {c["name"] for c in inspector.get_columns("users")}
    users_migrations = [
        ("users", "hf_token", "ALTER TABLE users ADD COLUMN hf_token VARCHAR(255)"),
        ("users", "google_refresh_token", "ALTER TABLE users ADD COLUMN google_refresh_token TEXT"),
        ("users", "role", "ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'"),
        ("users", "last_login", "ALTER TABLE users ADD COLUMN last_login TIMESTAMP"),
        ("users", "is_verified", "ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT TRUE NOT NULL"),
        ("users", "verification_token_hash", "ALTER TABLE users ADD COLUMN verification_token_hash VARCHAR(64)"),
        (
            "users",
            "verification_token_created_at",
            "ALTER TABLE users ADD COLUMN verification_token_created_at TIMESTAMP",
        ),
    ]
    for table, column, ddl in users_migrations:
        if column not in existing_users_columns:
            try:
                with engine.begin() as conn:
                    conn.execute(text(ddl))
                logger.info("Migration: added column %s.%s", table, column)
            except Exception:
                logger.warning(
                    "Migration skipped (may already exist): %s.%s", table, column
                )

    # Migrate api_keys
    try:
        existing_keys_columns = {c["name"] for c in inspector.get_columns("api_keys")}
    except Exception:
        existing_keys_columns = set()
    keys_migrations = [
        ("api_keys", "name", "ALTER TABLE api_keys ADD COLUMN name VARCHAR(100) DEFAULT 'default'"),
        ("api_keys", "is_active", "ALTER TABLE api_keys ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL"),
        ("api_keys", "last_used_at", "ALTER TABLE api_keys ADD COLUMN last_used_at TIMESTAMP"),
    ]
    for table, column, ddl in keys_migrations:
        if column not in existing_keys_columns:
            try:
                with engine.begin() as conn:
                    conn.execute(text(ddl))
                logger.info("Migration: added column %s.%s", table, column)
            except Exception:
                logger.warning(
                    "Migration skipped (may already exist): %s.%s", table, column
                )

    # Migrate documents
    existing_docs_columns = {c["name"] for c in inspector.get_columns("documents")}
    docs_migrations = [
        ("documents", "last_accessed_at", "ALTER TABLE documents ADD COLUMN last_accessed_at TIMESTAMP"),
        ("documents", "is_deleted", "ALTER TABLE documents ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL"),
        ("documents", "deleted_at", "ALTER TABLE documents ADD COLUMN deleted_at TIMESTAMP"),
        ("documents", "summary", "ALTER TABLE documents ADD COLUMN summary TEXT"),
        ("documents", "chunk_size", "ALTER TABLE documents ADD COLUMN chunk_size INTEGER"),
        ("documents", "chunk_overlap", "ALTER TABLE documents ADD COLUMN chunk_overlap INTEGER"),
        ("documents", "drive_file_id", "ALTER TABLE documents ADD COLUMN drive_file_id VARCHAR(255)"),
        ("documents", "drive_folder_id", "ALTER TABLE documents ADD COLUMN drive_folder_id VARCHAR(255)"),
        ("documents", "drive_synced_at", "ALTER TABLE documents ADD COLUMN drive_synced_at TIMESTAMP"),
    ]
    for table, column, ddl in docs_migrations:
        if column not in existing_docs_columns:
            try:
                with engine.begin() as conn:
                    conn.execute(text(ddl))
                logger.info("Migration: added column %s.%s", table, column)
            except Exception:
                logger.warning(
                    "Migration skipped (may already exist): %s.%s", table, column
                )

    # Migrate chat_messages
    try:
        existing_chat_columns = {c["name"] for c in inspector.get_columns("chat_messages")}
    except Exception:
        existing_chat_columns = set()
    chat_migrations = [
        ("chat_messages", "feedback", "ALTER TABLE chat_messages ADD COLUMN feedback VARCHAR(10)"),
    ]
    for table, column, ddl in chat_migrations:
        if column not in existing_chat_columns:
            try:
                with engine.begin() as conn:
                    conn.execute(text(ddl))
                logger.info("Migration: added column %s.%s", table, column)
            except Exception:
                logger.warning(
                    "Migration skipped (may already exist): %s.%s", table, column
                )



def init_db():
    """Create all tables on startup and apply schema migrations."""
    from app import models  # noqa: F401 — import to register models
    Base.metadata.create_all(bind=engine)
    _migrate_schema()

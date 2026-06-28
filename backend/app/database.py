"""
SQLAlchemy database setup with SQLite.
Uses synchronous SQLAlchemy for simplicity and compatibility.
"""
import os
import time
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event, inspect, text
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
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=settings.DATABASE_POOL_PRE_PING,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,  # Recycle stale connections
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
    """Context manager for background tasks, streaming, and other uses outside FastAPI DI.

    Creates a new session, commits on success, rolls back SQLAlchemy errors
    (converting them to typed AppException), re-raises non-DB exceptions,
    and always closes the session.
    """
    from sqlalchemy.exc import SQLAlchemyError
    from app.exceptions import AppException

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise AppException(
            "DATABASE_ERROR",
            "A database error occurred while processing your request.",
            500,
            {"error": str(e)[:200]},
        ) from e
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

_SLOW_QUERY_THRESHOLD = settings.DATABASE_SLOW_QUERY_THRESHOLD


@event.listens_for(engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(time.perf_counter())


@event.listens_for(engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    start_times = conn.info.get("query_start_time")
    if not start_times:
        return
    total_time = time.perf_counter() - start_times.pop(-1)
    if total_time > _SLOW_QUERY_THRESHOLD:
        logger.warning(
            "Slow query detected (%.2fs): %s",
            total_time,
            statement[:500],
        )


# ── Session Lifecycle Logging (DEBUG only) ───────────
if settings.DEBUG:
    @event.listens_for(SessionLocal, "after_begin")
    def _receive_after_begin(session, transaction, connection):
        logger.debug("Session %s began transaction", id(session))

    @event.listens_for(SessionLocal, "after_commit")
    def _receive_after_commit(session):
        logger.debug("Session %s committed", id(session))

    @event.listens_for(SessionLocal, "after_rollback")
    def _receive_after_rollback(session):
        logger.debug("Session %s rolled back", id(session))

    @event.listens_for(SessionLocal, "after_close")
    def _receive_after_close(session):
        logger.debug("Session %s closed", id(session))


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
        ("users", "display_name", "ALTER TABLE users ADD COLUMN display_name VARCHAR(120)"),
        ("users", "avatar_url", "ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500)"),
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
        ("documents", "processing_progress", "ALTER TABLE documents ADD COLUMN processing_progress INTEGER DEFAULT 0"),
        ("documents", "processing_stage", "ALTER TABLE documents ADD COLUMN processing_stage VARCHAR(20) DEFAULT 'queued'"),
        ("documents", "retry_count", "ALTER TABLE documents ADD COLUMN retry_count INTEGER DEFAULT 0"),
        ("documents", "last_error_traceback", "ALTER TABLE documents ADD COLUMN last_error_traceback TEXT"),
        ("documents", "processing_started_at", "ALTER TABLE documents ADD COLUMN processing_started_at TIMESTAMP"),
        ("documents", "completed_at", "ALTER TABLE documents ADD COLUMN completed_at TIMESTAMP"),
        ("documents", "extracted_urls", "ALTER TABLE documents ADD COLUMN extracted_urls TEXT"),
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


    # Migrate documents — embedding cache tracking
    try:
        existing_docs_columns = {c["name"] for c in inspector.get_columns("documents")}
    except Exception:
        existing_docs_columns = set()

    embedding_cache_migrations = [
        (
            "documents",
            "extracted_urls",
            "ALTER TABLE documents ADD COLUMN extracted_urls TEXT",
        ),
    ]
    for table, column, ddl in embedding_cache_migrations:
        if column not in existing_docs_columns:
            try:
                with engine.begin() as conn:
                    conn.execute(text(ddl))
                logger.info("Migration: added column %s.%s", table, column)
            except Exception:
                logger.warning(
                    "Migration skipped (may already exist): %s.%s", table, column
                )


    # ── Workspace tables ──────────────────────────────────────────────────
    existing_tables = set(inspector.get_table_names())

    if "workspaces" not in existing_tables:
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE workspaces (
                        id         CHAR(36)     PRIMARY KEY,
                        name       VARCHAR(255) NOT NULL,
                        created_by CHAR(36)     NOT NULL REFERENCES users(id),
                        created_at TIMESTAMP
                    )
                """))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_workspaces_created_by "
                    "ON workspaces (created_by)"
                ))
            logger.info("Migration: created table workspaces")
        except Exception:
            logger.warning("Migration skipped (may already exist): workspaces")

    if "workspace_members" not in existing_tables:
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE workspace_members (
                        id           CHAR(36)    PRIMARY KEY,
                        workspace_id CHAR(36)    NOT NULL REFERENCES workspaces(id),
                        user_id      CHAR(36)    NOT NULL REFERENCES users(id),
                        role         VARCHAR(20) NOT NULL DEFAULT 'viewer',
                        joined_at    TIMESTAMP,
                        CONSTRAINT uq_workspace_member UNIQUE (workspace_id, user_id)
                    )
                """))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_workspace_members_workspace_id "
                    "ON workspace_members (workspace_id)"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_workspace_members_user_id "
                    "ON workspace_members (user_id)"
                ))
            logger.info("Migration: created table workspace_members")
        except Exception:
            logger.warning("Migration skipped (may already exist): workspace_members")

    if "workspace_invitations" not in existing_tables:
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE workspace_invitations (
                        id             CHAR(36)     PRIMARY KEY,
                        email          VARCHAR(120) NOT NULL,
                        token_hash     VARCHAR(255) NOT NULL UNIQUE,
                        inviter_id     CHAR(36)     NOT NULL REFERENCES users(id),
                        workspace_name VARCHAR(255) NOT NULL,
                        created_at     TIMESTAMP,
                        expires_at     TIMESTAMP    NOT NULL,
                        accepted_at    TIMESTAMP
                    )
                """))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_workspace_invitations_email "
                    "ON workspace_invitations (email)"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_workspace_invitations_token_hash "
                    "ON workspace_invitations (token_hash)"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_workspace_invitations_inviter_id "
                    "ON workspace_invitations (inviter_id)"
                ))
            logger.info("Migration: created table workspace_invitations")
        except Exception:
            logger.warning("Migration skipped (may already exist): workspace_invitations")


def advisory_lock(lock_id: int):
    """Context manager that acquires a PostgreSQL advisory lock (xact scope).

    On SQLite the lock is a no-op because SQLite serializes all writes anyway.
    On PostgreSQL the lock is released automatically at transaction commit.

    Usage::

        with advisory_lock(hash("cleanup_inactive") & 0x7FFFFFFF):
            ...
    """
    if is_sqlite:
        # SQLite serializes writes; no explicit lock needed.
        return _noop_contextmanager()

    from contextlib import contextmanager

    @contextmanager
    def _pg_lock():
        with engine.begin() as conn:
            conn.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": lock_id})
            yield

    return _pg_lock()


def _noop_contextmanager():
    from contextlib import contextmanager as _cm

    @_cm
    def _noop():
        yield

    return _noop()


def init_db():
    """Create all tables on startup and apply schema migrations."""
    from app import models  # noqa: F401 — import to register models
    Base.metadata.create_all(bind=engine)
    _migrate_schema()

"""
Unit tests for database schema migrations (_migrate_schema).

Each test creates a minimal in-memory SQLite database that intentionally
omits one or more columns (simulating an older schema), runs
_migrate_schema(), and then verifies the missing columns were added
without corrupting existing data or dropping any existing columns.
"""
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_engine():
    """Fresh in-memory SQLite engine — fully isolated per test."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )


def _columns(engine, table: str) -> set:
    """Return the set of column names for a table."""
    return {c["name"] for c in inspect(engine).get_columns(table)}


def _run_migrate(engine):
    """Patch app.database.engine and call _migrate_schema()."""
    import app.database as db_module
    from sqlalchemy import inspect as sa_inspect

    original_engine = db_module.engine
    db_module.engine = engine

    # Also patch inspect so _migrate_schema uses our engine's inspector
    original_inspect = db_module.inspect
    db_module.inspect = lambda _: sa_inspect(engine)

    try:
        db_module._migrate_schema()
    finally:
        db_module.engine = original_engine
        db_module.inspect = original_inspect


def _create_minimal_users(engine):
    """Create users table with only the original columns (no migration columns)."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id CHAR(36) PRIMARY KEY,
                username VARCHAR(80) NOT NULL UNIQUE,
                email VARCHAR(120) NOT NULL UNIQUE,
                hashed_password VARCHAR(255) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP
            )
        """))


def _create_minimal_documents(engine):
    """Create documents table with only the original columns."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE documents (
                id CHAR(36) PRIMARY KEY,
                user_id CHAR(36) NOT NULL,
                filename VARCHAR(255) NOT NULL,
                original_name VARCHAR(255) NOT NULL,
                file_size INTEGER DEFAULT 0,
                page_count INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'pending',
                error_message TEXT,
                uploaded_at TIMESTAMP
            )
        """))


def _create_minimal_api_keys(engine):
    """Create api_keys table with only the original columns."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE api_keys (
                id CHAR(36) PRIMARY KEY,
                user_id CHAR(36) NOT NULL,
                key_prefix VARCHAR(20) NOT NULL,
                hashed_key VARCHAR(255) NOT NULL UNIQUE
            )
        """))


def _create_minimal_chat_messages(engine):
    """Create chat_messages table without the feedback column."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE chat_messages (
                id CHAR(36) PRIMARY KEY,
                user_id CHAR(36) NOT NULL,
                document_id CHAR(36),
                session_id CHAR(36),
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                sources_json TEXT,
                created_at TIMESTAMP
            )
        """))


# ── users migrations ──────────────────────────────────────────────────────────

def test_migrate_adds_hf_token_to_users():
    engine = _make_engine()
    _create_minimal_users(engine)
    assert "hf_token" not in _columns(engine, "users")
    _run_migrate(engine)
    assert "hf_token" in _columns(engine, "users")


def test_migrate_adds_role_to_users():
    engine = _make_engine()
    _create_minimal_users(engine)
    assert "role" not in _columns(engine, "users")
    _run_migrate(engine)
    assert "role" in _columns(engine, "users")


def test_migrate_adds_google_refresh_token_to_users():
    engine = _make_engine()
    _create_minimal_users(engine)
    assert "google_refresh_token" not in _columns(engine, "users")
    _run_migrate(engine)
    assert "google_refresh_token" in _columns(engine, "users")


def test_migrate_adds_last_login_to_users():
    engine = _make_engine()
    _create_minimal_users(engine)
    _run_migrate(engine)
    assert "last_login" in _columns(engine, "users")


def test_migrate_adds_is_verified_to_users():
    engine = _make_engine()
    _create_minimal_users(engine)
    assert "is_verified" not in _columns(engine, "users")
    _run_migrate(engine)
    assert "is_verified" in _columns(engine, "users")


def test_migrate_adds_verification_token_hash_to_users():
    engine = _make_engine()
    _create_minimal_users(engine)
    _run_migrate(engine)
    assert "verification_token_hash" in _columns(engine, "users")


def test_migrate_adds_verification_token_created_at_to_users():
    engine = _make_engine()
    _create_minimal_users(engine)
    _run_migrate(engine)
    assert "verification_token_created_at" in _columns(engine, "users")


def test_migrate_preserves_existing_users_columns():
    """Migration must never drop or rename any original users column."""
    engine = _make_engine()
    _create_minimal_users(engine)
    original = _columns(engine, "users")
    _run_migrate(engine)
    after = _columns(engine, "users")
    assert original.issubset(after), f"Columns removed: {original - after}"


def test_migrate_preserves_existing_user_data():
    """Rows inserted before migration must still be readable afterwards."""
    engine = _make_engine()
    _create_minimal_users(engine)
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO users (id, username, email, hashed_password) "
            "VALUES ('u1', 'alice', 'alice@example.com', 'hash')"
        ))
    _run_migrate(engine)
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT username, email FROM users WHERE id = 'u1'")
        ).fetchone()
    assert row is not None
    assert row[0] == "alice"
    assert row[1] == "alice@example.com"


# ── documents migrations ──────────────────────────────────────────────────────

def test_migrate_adds_is_deleted_to_documents():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_documents(engine)
    assert "is_deleted" not in _columns(engine, "documents")
    _run_migrate(engine)
    assert "is_deleted" in _columns(engine, "documents")


def test_migrate_adds_summary_to_documents():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_documents(engine)
    assert "summary" not in _columns(engine, "documents")
    _run_migrate(engine)
    assert "summary" in _columns(engine, "documents")


def test_migrate_adds_chunk_size_and_overlap_to_documents():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_documents(engine)
    _run_migrate(engine)
    cols = _columns(engine, "documents")
    assert "chunk_size" in cols
    assert "chunk_overlap" in cols


def test_migrate_adds_processing_progress_to_documents():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_documents(engine)
    _run_migrate(engine)
    assert "processing_progress" in _columns(engine, "documents")


def test_migrate_adds_processing_stage_to_documents():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_documents(engine)
    _run_migrate(engine)
    assert "processing_stage" in _columns(engine, "documents")


def test_migrate_adds_extracted_urls_to_documents():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_documents(engine)
    assert "extracted_urls" not in _columns(engine, "documents")
    _run_migrate(engine)
    assert "extracted_urls" in _columns(engine, "documents")


def test_migrate_adds_completed_at_to_documents():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_documents(engine)
    _run_migrate(engine)
    assert "completed_at" in _columns(engine, "documents")


def test_migrate_adds_drive_columns_to_documents():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_documents(engine)
    _run_migrate(engine)
    cols = _columns(engine, "documents")
    assert "drive_file_id" in cols
    assert "drive_folder_id" in cols
    assert "drive_synced_at" in cols


def test_migrate_preserves_existing_documents_columns():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_documents(engine)
    original = _columns(engine, "documents")
    _run_migrate(engine)
    after = _columns(engine, "documents")
    assert original.issubset(after), f"Columns removed: {original - after}"


def test_migrate_preserves_existing_document_data():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_documents(engine)
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO documents "
            "(id, user_id, filename, original_name, file_size, status) "
            "VALUES ('d1', 'u1', 'file.pdf', 'file.pdf', 1024, 'ready')"
        ))
    _run_migrate(engine)
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT original_name, status FROM documents WHERE id = 'd1'")
        ).fetchone()
    assert row is not None
    assert row[0] == "file.pdf"
    assert row[1] == "ready"


# ── api_keys migrations ───────────────────────────────────────────────────────

def test_migrate_adds_name_to_api_keys():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_api_keys(engine)
    assert "name" not in _columns(engine, "api_keys")
    _run_migrate(engine)
    assert "name" in _columns(engine, "api_keys")


def test_migrate_adds_is_active_to_api_keys():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_api_keys(engine)
    assert "is_active" not in _columns(engine, "api_keys")
    _run_migrate(engine)
    assert "is_active" in _columns(engine, "api_keys")


def test_migrate_adds_last_used_at_to_api_keys():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_api_keys(engine)
    _run_migrate(engine)
    assert "last_used_at" in _columns(engine, "api_keys")


def test_migrate_preserves_existing_api_keys_columns():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_api_keys(engine)
    original = _columns(engine, "api_keys")
    _run_migrate(engine)
    after = _columns(engine, "api_keys")
    assert original.issubset(after), f"Columns removed: {original - after}"


# ── chat_messages migrations ──────────────────────────────────────────────────

def test_migrate_adds_feedback_to_chat_messages():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_chat_messages(engine)
    assert "feedback" not in _columns(engine, "chat_messages")
    _run_migrate(engine)
    assert "feedback" in _columns(engine, "chat_messages")


def test_migrate_preserves_existing_chat_messages_columns():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_chat_messages(engine)
    original = _columns(engine, "chat_messages")
    _run_migrate(engine)
    after = _columns(engine, "chat_messages")
    assert original.issubset(after), f"Columns removed: {original - after}"


# ── Idempotency ───────────────────────────────────────────────────────────────

def test_migrate_is_idempotent_users():
    """Running _migrate_schema() twice must not raise or duplicate columns."""
    engine = _make_engine()
    _create_minimal_users(engine)
    _run_migrate(engine)
    cols_after_first = _columns(engine, "users")
    _run_migrate(engine)
    cols_after_second = _columns(engine, "users")
    assert cols_after_first == cols_after_second


def test_migrate_is_idempotent_documents():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_documents(engine)
    _run_migrate(engine)
    cols_after_first = _columns(engine, "documents")
    _run_migrate(engine)
    cols_after_second = _columns(engine, "documents")
    assert cols_after_first == cols_after_second


def test_migrate_is_idempotent_api_keys():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_api_keys(engine)
    _run_migrate(engine)
    cols_after_first = _columns(engine, "api_keys")
    _run_migrate(engine)
    cols_after_second = _columns(engine, "api_keys")
    assert cols_after_first == cols_after_second


def test_migrate_is_idempotent_chat_messages():
    engine = _make_engine()
    _create_minimal_users(engine)
    _create_minimal_chat_messages(engine)
    _run_migrate(engine)
    cols_after_first = _columns(engine, "chat_messages")
    _run_migrate(engine)
    cols_after_second = _columns(engine, "chat_messages")
    assert cols_after_first == cols_after_second


# ── Full schema (already migrated) ───────────────────────────────────────────

def test_migrate_on_fully_migrated_schema_is_safe():
    """If all columns already exist, _migrate_schema() must complete without error."""
    engine = _make_engine()
    # Create tables with ALL columns already present
    _create_minimal_users(engine)
    _create_minimal_documents(engine)
    _create_minimal_api_keys(engine)
    _create_minimal_chat_messages(engine)
    # First pass adds all columns
    _run_migrate(engine)
    # Second pass should be a complete no-op
    _run_migrate(engine)
    # Verify nothing was lost
    assert "hf_token" in _columns(engine, "users")
    assert "extracted_urls" in _columns(engine, "documents")
    assert "is_active" in _columns(engine, "api_keys")
    assert "feedback" in _columns(engine, "chat_messages")

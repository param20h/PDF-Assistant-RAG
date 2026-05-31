"""Migrate SQLite app data into a Supabase/Postgres database.

The script supports both the current FastAPI SQLite schema
(`users`, `documents`, `chat_messages`) and the older legacy
`instance/users.db` schema (`user` only).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    inspect,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

LOGGER = logging.getLogger("sqlite_to_postgres")


def generate_uuid() -> str:
    return str(uuid.uuid4())


metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", String, primary_key=True, default=generate_uuid),
    Column("username", String(80), unique=True, nullable=False, index=True),
    Column("email", String(120), unique=True, nullable=False, index=True),
    Column("hashed_password", String(255), nullable=False),
    Column("is_admin", Boolean, default=False),
    Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
    Column("last_login", DateTime, nullable=True, index=True),
    Column("hf_token", String(255), nullable=True),
)

api_keys = Table(
    "api_keys",
    metadata,
    Column("id", String, primary_key=True, default=generate_uuid),
    Column("user_id", String, ForeignKey("users.id"), nullable=False, index=True),
    Column("key_prefix", String(10), nullable=False),
    Column("hashed_key", String(255), nullable=False, unique=True, index=True),
    Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
    Column("last_used", DateTime, nullable=True),
)

documents = Table(
    "documents",
    metadata,
    Column("id", String, primary_key=True, default=generate_uuid),
    Column("user_id", String, ForeignKey("users.id"), nullable=False, index=True),
    Column("filename", String(255), nullable=False),
    Column("original_name", String(255), nullable=False),
    Column("file_size", Integer, default=0),
    Column("page_count", Integer, default=0),
    Column("chunk_count", Integer, default=0),
    Column("status", String(20), default="pending"),
    Column("error_message", Text, nullable=True),
    Column("uploaded_at", DateTime, default=lambda: datetime.now(timezone.utc)),
    Column("summary", Text, nullable=True),
)

chat_messages = Table(
    "chat_messages",
    metadata,
    Column("id", String, primary_key=True, default=generate_uuid),
    Column("user_id", String, ForeignKey("users.id"), nullable=False, index=True),
    Column("document_id", String, ForeignKey("documents.id"), nullable=True, index=True),
    Column("role", String(20), nullable=False),
    Column("content", Text, nullable=False),
    Column("sources_json", Text, nullable=True),
    Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
)

shared_messages = Table(
    "shared_messages",
    metadata,
    Column("id", String, primary_key=True, default=generate_uuid),
    Column("message_id", String, ForeignKey("chat_messages.id"), nullable=False, unique=True, index=True),
    Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
)


@dataclass
class MigrationStats:
    inserted: dict[str, int] = field(default_factory=dict)
    reused: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)

    def add(self, table_name: str, action: str) -> None:
        getattr(self, action)[table_name] = getattr(self, action).get(table_name, 0) + 1


def normalize_postgres_url(url: str) -> str:
    """Prefer psycopg v3 when callers pass Supabase's common URL forms."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def sqlite_url_from_path(path: str) -> str:
    return f"sqlite:///{Path(path).resolve().as_posix()}"


def make_engine(url: str) -> Engine:
    return create_engine(url, future=True)


def make_session(engine: Engine) -> Session:
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)()


def reflected_table(engine: Engine, table_name: str) -> Table | None:
    if not inspect(engine).has_table(table_name):
        return None
    reflected = MetaData()
    return Table(table_name, reflected, autoload_with=engine)


def fetch_rows(session: Session, table: Table) -> list[dict[str, Any]]:
    stmt = select(table)
    if "id" in table.c:
        stmt = stmt.order_by(table.c.id)
    return [dict(row) for row in session.execute(stmt).mappings().all()]


def existing_id(session: Session, table: Table, source_id: str | None) -> str | None:
    if not source_id:
        return None
    return session.execute(select(table.c.id).where(table.c.id == source_id)).scalar_one_or_none()


def available_id(session: Session, table: Table, source_id: Any) -> str:
    candidate = str(source_id) if source_id is not None else generate_uuid()
    if existing_id(session, table, candidate) is None:
        return candidate

    while True:
        candidate = generate_uuid()
        if existing_id(session, table, candidate) is None:
            return candidate


def first_existing_user(session: Session, row: dict[str, Any]) -> str | None:
    email = row.get("email")
    username = row.get("username")
    if email:
        match = session.execute(select(users.c.id).where(users.c.email == email)).scalar_one_or_none()
        if match:
            return match
    if username:
        return session.execute(select(users.c.id).where(users.c.username == username)).scalar_one_or_none()
    return None


def copy_users(
    source_session: Session,
    target_session: Session,
    source_table: Table,
    stats: MigrationStats,
) -> dict[str, str]:
    id_map: dict[str, str] = {}
    now = datetime.now(timezone.utc)

    for row in fetch_rows(source_session, source_table):
        old_id = str(row.get("id"))
        existing = existing_id(target_session, users, old_id) or first_existing_user(target_session, row)
        if existing:
            id_map[old_id] = existing
            stats.add("users", "reused")
            continue

        is_legacy = source_table.name == "user"
        new_id = available_id(target_session, users, None if is_legacy else old_id)
        user_values = {
            "id": new_id,
            "username": row["username"],
            "email": row["email"],
            "hashed_password": row.get("hashed_password") or row.get("password") or "",
            "is_admin": bool(row.get("is_admin") or False),
            "created_at": row.get("created_at") or now,
            "last_login": row.get("last_login"),
            "hf_token": row.get("hf_token"),
        }
        target_session.execute(users.insert().values(**user_values))
        id_map[old_id] = new_id
        stats.add("users", "inserted")

    return id_map


def copy_api_keys(
    source_session: Session,
    target_session: Session,
    source_table: Table | None,
    user_id_map: dict[str, str],
    stats: MigrationStats,
) -> dict[str, str]:
    id_map: dict[str, str] = {}
    if source_table is None:
        return id_map

    for row in fetch_rows(source_session, source_table):
        old_id = str(row.get("id"))
        new_user_id = user_id_map.get(str(row.get("user_id")))
        if not new_user_id:
            stats.add("api_keys", "skipped")
            continue

        existing = (
            existing_id(target_session, api_keys, old_id)
            or target_session.execute(
                select(api_keys.c.id).where(api_keys.c.hashed_key == row.get("hashed_key"))
            ).scalar_one_or_none()
        )
        if existing:
            id_map[old_id] = existing
            stats.add("api_keys", "reused")
            continue

        new_id = available_id(target_session, api_keys, old_id)
        target_session.execute(
            api_keys.insert().values(
                id=new_id,
                user_id=new_user_id,
                key_prefix=row["key_prefix"],
                hashed_key=row["hashed_key"],
                created_at=row.get("created_at") or datetime.now(timezone.utc),
                last_used=row.get("last_used"),
            )
        )
        id_map[old_id] = new_id
        stats.add("api_keys", "inserted")

    return id_map


def copy_documents(
    source_session: Session,
    target_session: Session,
    source_table: Table | None,
    user_id_map: dict[str, str],
    stats: MigrationStats,
) -> dict[str, str]:
    id_map: dict[str, str] = {}
    if source_table is None:
        return id_map

    for row in fetch_rows(source_session, source_table):
        old_id = str(row.get("id"))
        new_user_id = user_id_map.get(str(row.get("user_id")))
        if not new_user_id:
            stats.add("documents", "skipped")
            continue

        existing = existing_id(target_session, documents, old_id)
        if existing:
            id_map[old_id] = existing
            stats.add("documents", "reused")
            continue

        new_id = available_id(target_session, documents, old_id)
        target_session.execute(
            documents.insert().values(
                id=new_id,
                user_id=new_user_id,
                filename=row["filename"],
                original_name=row["original_name"],
                file_size=row.get("file_size") or 0,
                page_count=row.get("page_count") or 0,
                chunk_count=row.get("chunk_count") or 0,
                status=row.get("status") or "pending",
                error_message=row.get("error_message"),
                uploaded_at=row.get("uploaded_at") or datetime.now(timezone.utc),
                summary=row.get("summary"),
            )
        )
        id_map[old_id] = new_id
        stats.add("documents", "inserted")

    return id_map


def copy_chat_messages(
    source_session: Session,
    target_session: Session,
    source_table: Table | None,
    user_id_map: dict[str, str],
    document_id_map: dict[str, str],
    stats: MigrationStats,
) -> dict[str, str]:
    id_map: dict[str, str] = {}
    if source_table is None:
        return id_map

    for row in fetch_rows(source_session, source_table):
        old_id = str(row.get("id"))
        new_user_id = user_id_map.get(str(row.get("user_id")))
        old_document_id = row.get("document_id")
        new_document_id = document_id_map.get(str(old_document_id)) if old_document_id else None
        if not new_user_id or (old_document_id and not new_document_id):
            stats.add("chat_messages", "skipped")
            continue

        existing = existing_id(target_session, chat_messages, old_id)
        if existing:
            id_map[old_id] = existing
            stats.add("chat_messages", "reused")
            continue

        new_id = available_id(target_session, chat_messages, old_id)
        target_session.execute(
            chat_messages.insert().values(
                id=new_id,
                user_id=new_user_id,
                document_id=new_document_id,
                role=row["role"],
                content=row["content"],
                sources_json=row.get("sources_json"),
                created_at=row.get("created_at") or datetime.now(timezone.utc),
            )
        )
        id_map[old_id] = new_id
        stats.add("chat_messages", "inserted")

    return id_map


def copy_shared_messages(
    source_session: Session,
    target_session: Session,
    source_table: Table | None,
    message_id_map: dict[str, str],
    stats: MigrationStats,
) -> None:
    if source_table is None:
        return

    for row in fetch_rows(source_session, source_table):
        old_id = str(row.get("id"))
        new_message_id = message_id_map.get(str(row.get("message_id")))
        if not new_message_id:
            stats.add("shared_messages", "skipped")
            continue

        existing = (
            existing_id(target_session, shared_messages, old_id)
            or target_session.execute(
                select(shared_messages.c.id).where(shared_messages.c.message_id == new_message_id)
            ).scalar_one_or_none()
        )
        if existing:
            stats.add("shared_messages", "reused")
            continue

        target_session.execute(
            shared_messages.insert().values(
                id=available_id(target_session, shared_messages, old_id),
                message_id=new_message_id,
                created_at=row.get("created_at") or datetime.now(timezone.utc),
            )
        )
        stats.add("shared_messages", "inserted")


def migrate(
    sqlite_url: str,
    postgres_url: str,
    create_tables: bool,
    dry_run: bool,
) -> MigrationStats:
    source_engine = make_engine(sqlite_url)
    target_engine = make_engine(normalize_postgres_url(postgres_url))

    if create_tables:
        metadata.create_all(target_engine)

    source_session = make_session(source_engine)
    target_session = make_session(target_engine)
    stats = MigrationStats()

    try:
        current_users = reflected_table(source_engine, "users")
        legacy_users = reflected_table(source_engine, "user")
        source_users = current_users if current_users is not None else legacy_users
        if source_users is None:
            raise RuntimeError("No users table found. Expected 'users' or legacy 'user'.")

        user_id_map = copy_users(source_session, target_session, source_users, stats)
        copy_api_keys(source_session, target_session, reflected_table(source_engine, "api_keys"), user_id_map, stats)
        document_id_map = copy_documents(
            source_session,
            target_session,
            reflected_table(source_engine, "documents"),
            user_id_map,
            stats,
        )
        message_id_map = copy_chat_messages(
            source_session,
            target_session,
            reflected_table(source_engine, "chat_messages"),
            user_id_map,
            document_id_map,
            stats,
        )
        copy_shared_messages(
            source_session,
            target_session,
            reflected_table(source_engine, "shared_messages"),
            message_id_map,
            stats,
        )

        if dry_run:
            target_session.rollback()
            LOGGER.info("Dry run complete; rolled back target transaction.")
        else:
            target_session.commit()
            LOGGER.info("Migration committed.")

        return stats
    except IntegrityError:
        target_session.rollback()
        LOGGER.exception("Migration failed because the target database rejected a row.")
        raise
    except Exception:
        target_session.rollback()
        LOGGER.exception("Migration failed; rolled back target transaction.")
        raise
    finally:
        source_session.close()
        target_session.close()
        source_engine.dispose()
        target_engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate SQLite users/documents/chat history to Supabase Postgres.")
    parser.add_argument(
        "--sqlite-path",
        default="instance/users.db",
        help="Path to the SQLite database file. Defaults to instance/users.db.",
    )
    parser.add_argument(
        "--sqlite-url",
        help="Full SQLite SQLAlchemy URL. Overrides --sqlite-path.",
    )
    parser.add_argument(
        "--postgres-url",
        default=os.getenv("SUPABASE_DB_URL") or os.getenv("POSTGRES_DATABASE_URL") or os.getenv("DATABASE_URL"),
        help="Supabase/Postgres SQLAlchemy URL. Also read from SUPABASE_DB_URL, POSTGRES_DATABASE_URL, or DATABASE_URL.",
    )
    parser.add_argument(
        "--no-create-tables",
        action="store_true",
        help="Do not create missing target tables before migrating.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the migration and roll back the target transaction.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    postgres_url = args.postgres_url
    if not postgres_url or postgres_url.startswith("sqlite"):
        LOGGER.error("Provide a Supabase/Postgres URL with --postgres-url or SUPABASE_DB_URL.")
        return 2

    sqlite_url = args.sqlite_url or sqlite_url_from_path(args.sqlite_path)
    stats = migrate(
        sqlite_url=sqlite_url,
        postgres_url=postgres_url,
        create_tables=not args.no_create_tables,
        dry_run=args.dry_run,
    )

    for table_name in sorted(set(stats.inserted) | set(stats.reused) | set(stats.skipped)):
        LOGGER.info(
            "%s: inserted=%s reused=%s skipped=%s",
            table_name,
            stats.inserted.get(table_name, 0),
            stats.reused.get(table_name, 0),
            stats.skipped.get(table_name, 0),
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""migrate_sqlite_to_postgres.py
--------------------------------
Safely migrate all data from SQLite to PostgreSQL without data loss.

Supports both the current FastAPI schema (users, api_keys, documents,
chat_messages, shared_messages) and the extended schema that includes
workspaces, workspace_invitations, workspace_members, chat_sessions,
and drive_connections.

Also supports the older legacy ``instance/users.db`` schema where the
users table is named ``user`` (singular).

Dependencies
------------
    pip install sqlalchemy psycopg[binary]
    # or: pip install sqlalchemy psycopg2-binary

Tables migrated (FK-safe order)
---------------------------------
    users → api_keys → workspaces → workspace_invitations
    → workspace_members → chat_sessions → documents
    → chat_messages → drive_connections → shared_messages

Usage
-----
    # Dry-run (reads SQLite, prints counts — no Postgres connection needed):
    python migrate_sqlite_to_postgres.py \\
        --sqlite sqlite:///./data/app.db \\
        --dry-run

    # Live migration (Postgres URL via CLI):
    python migrate_sqlite_to_postgres.py \\
        --sqlite sqlite:///./data/app.db \\
        --postgres postgresql://user:pass@localhost:5432/mydb

    # Live migration (Postgres URL via environment variable):
    export SUPABASE_DB_URL="postgres://user:pass@db.supabase.co:5432/postgres"
    python migrate_sqlite_to_postgres.py --sqlite sqlite:///./data/app.db

    # Migrate from the legacy instance/users.db path:
    python migrate_sqlite_to_postgres.py \\
        --sqlite-path instance/users.db \\
        --postgres postgresql://user:pass@localhost:5432/mydb

    # Migrate specific tables only:
    python migrate_sqlite_to_postgres.py \\
        --sqlite sqlite:///./data/app.db \\
        --postgres postgresql://user:pass@localhost:5432/mydb \\
        --tables users documents chat_messages

    # Wipe Postgres tables before migrating (fresh start):
    python migrate_sqlite_to_postgres.py \\
        --sqlite sqlite:///./data/app.db \\
        --postgres postgresql://user:pass@localhost:5432/mydb \\
        --truncate

    # Verbose / debug logging:
    python migrate_sqlite_to_postgres.py \\
        --sqlite sqlite:///./data/app.db \\
        --postgres postgresql://user:pass@localhost:5432/mydb \\
        --verbose

Resolves: #279
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("migration")

# ---------------------------------------------------------------------------
# Migration order — respects FK dependencies
# ---------------------------------------------------------------------------
TABLE_ORDER = [
    "users",
    "api_keys",
    "workspaces",
    "workspace_invitations",
    "workspace_members",
    "chat_sessions",
    "documents",
    "chat_messages",
    "drive_connections",
    "shared_messages",
]

# Columns that hold UUID / GUID values and need string normalisation
_UUID_COLUMNS = {
    "id", "user_id", "document_id", "session_id", "message_id",
    "workspace_id", "inviter_id", "created_by",
}

# Boolean columns stored as 0/1 integers in SQLite
_BOOL_COLUMNS = {
    "is_admin", "is_verified", "is_active", "is_deleted", "enabled",
}


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def normalize_postgres_url(url: str) -> str:
    """
    Normalise common Postgres URL forms to use the psycopg (v3) driver.

    Supabase and many hosting providers hand out ``postgres://`` or plain
    ``postgresql://`` connection strings.  SQLAlchemy requires a driver
    specifier such as ``postgresql+psycopg://`` for psycopg v3, or
    ``postgresql+psycopg2://`` for psycopg2.  We prefer psycopg v3 when
    no driver is already specified.
    """
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    # Already has a driver specifier (e.g. postgresql+psycopg2://) — leave it.
    return url


def sqlite_url_from_path(path: str) -> str:
    return f"sqlite:///{Path(path).resolve().as_posix()}"


# ---------------------------------------------------------------------------
# Engine factory
# ---------------------------------------------------------------------------

def _make_engine(url: str, label: str):
    """Create a SQLAlchemy engine with sensible defaults."""
    is_sqlite = url.startswith("sqlite")
    kwargs: Dict[str, Any] = {"echo": False, "future": True}
    if is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs.update(pool_pre_ping=True, pool_size=5, max_overflow=10)
    logger.info("Connecting to %s: %s", label, url)
    return create_engine(url, **kwargs)


# ---------------------------------------------------------------------------
# Row coercion
# ---------------------------------------------------------------------------

def _normalise_uuid(value: Any) -> Optional[str]:
    """Return a UUID as a plain lowercase string, or None."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError):
        return str(value)


def _coerce_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Coerce a SQLite row dict so it is safe to insert into Postgres:

    * UUID columns      → normalised lowercase str
    * Boolean integers  → Python bool  (SQLite stores True/False as 1/0)
    * Naive datetimes   → UTC-aware datetimes
    """
    result: Dict[str, Any] = {}
    for col, val in row.items():
        if col in _UUID_COLUMNS:
            result[col] = _normalise_uuid(val)
        elif col in _BOOL_COLUMNS:
            result[col] = bool(val) if val is not None else None
        elif isinstance(val, datetime) and val.tzinfo is None:
            result[col] = val.replace(tzinfo=timezone.utc)
        else:
            result[col] = val
    return result


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------

def _table_exists(inspector, table: str) -> bool:
    return table in inspector.get_table_names()


def _resolve_users_table(src_inspector) -> Optional[str]:
    """
    Return the name of the users table in the source database.

    Supports both the current schema (``users``) and the legacy schema
    (``user``, singular) used by older ``instance/users.db`` databases.
    Returns None if neither is found.
    """
    if _table_exists(src_inspector, "users"):
        return "users"
    if _table_exists(src_inspector, "user"):
        logger.info("Legacy 'user' table detected — will migrate as 'users'.")
        return "user"
    return None


# ---------------------------------------------------------------------------
# Per-table migration
# ---------------------------------------------------------------------------

def _dry_run_table(table: str, src_conn) -> Dict[str, int]:
    """Read SQLite row counts and log them — no Postgres connection used."""
    src_inspector = inspect(src_conn)
    if not _table_exists(src_inspector, table):
        logger.warning("  [%s] not found in SQLite — skipping", table)
        return {"would_migrate": 0, "skipped": 0}

    count = src_conn.execute(text(f"SELECT COUNT(*) FROM \"{table}\"")).scalar() or 0
    logger.info("  [%s] %d rows found (dry-run — nothing written)", table, count)
    return {"would_migrate": count, "skipped": 0}


def _live_migrate_table(
    table: str,
    src_table_name: str,
    src_conn,
    dst_conn,
    truncate: bool,
    batch_size: int,
) -> Dict[str, int]:
    """
    Migrate one table from SQLite → Postgres.

    ``table`` is the canonical destination table name (always the current
    schema name, e.g. ``"users"``).  ``src_table_name`` may differ for
    legacy sources (e.g. ``"user"``).
    """
    stats = {"inserted": 0, "skipped": 0}

    src_inspector = inspect(src_conn)
    dst_inspector = inspect(dst_conn)

    if not _table_exists(src_inspector, src_table_name):
        logger.warning("  [%s] not found in SQLite — skipping", table)
        return stats

    if not _table_exists(dst_inspector, table):
        logger.warning(
            "  [%s] not found in Postgres — skipping. "
            "Run your init_postgres.sql first to create the schema.",
            table,
        )
        return stats

    # Fetch all rows from source
    rows_result = src_conn.execute(text(f"SELECT * FROM \"{src_table_name}\""))
    column_names: List[str] = list(rows_result.keys())
    raw_rows = rows_result.fetchall()

    if not raw_rows:
        logger.info("  [%s] 0 rows — nothing to migrate", table)
        return stats

    logger.info("  [%s] %d rows to migrate", table, len(raw_rows))

    if truncate:
        logger.info("  [%s] truncating Postgres table (CASCADE)", table)
        dst_conn.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))

    # Build idempotent INSERT — skips duplicates silently
    col_list = ", ".join(f'"{c}"' for c in column_names)
    placeholders = ", ".join(f":{c}" for c in column_names)
    insert_sql = text(
        f'INSERT INTO "{table}" ({col_list}) '
        f"VALUES ({placeholders}) "
        f"ON CONFLICT DO NOTHING"
    )

    batch: List[Dict[str, Any]] = []
    for raw in raw_rows:
        row_dict = dict(zip(column_names, raw))
        batch.append(_coerce_row(row_dict))

        if len(batch) >= batch_size:
            result = dst_conn.execute(insert_sql, batch)
            stats["inserted"] += result.rowcount if result.rowcount >= 0 else len(batch)
            batch = []

    if batch:
        result = dst_conn.execute(insert_sql, batch)
        stats["inserted"] += result.rowcount if result.rowcount >= 0 else len(batch)

    logger.info("  [%s] inserted %d rows", table, stats["inserted"])
    return stats


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_migration(
    sqlite_url: str,
    postgres_url: Optional[str],
    dry_run: bool,
    truncate: bool,
    tables: Optional[List[str]],
    batch_size: int,
) -> bool:
    """
    Orchestrate the full migration.  Returns True on success.

    In dry-run mode, no Postgres connection is opened; only SQLite row
    counts are reported.
    """
    # Build the ordered table list
    target = set(tables) if tables else set(TABLE_ORDER)
    ordered = [t for t in TABLE_ORDER if t in target]
    # Append any user-supplied extras that aren't in TABLE_ORDER
    for t in (tables or []):
        if t not in ordered:
            logger.warning(
                "Table '%s' is not in the known FK-safe order. "
                "It will be migrated last — ensure FK dependencies are satisfied.",
                t,
            )
            ordered.append(t)

    mode = "DRY RUN" if dry_run else "LIVE"
    logger.info("=" * 60)
    logger.info("Migration mode : %s", mode)
    logger.info("Source         : %s", sqlite_url)
    if not dry_run:
        logger.info("Destination    : %s", postgres_url)
    logger.info("Tables         : %s", ", ".join(ordered))
    logger.info("Truncate first : %s", truncate and not dry_run)
    logger.info("Batch size     : %d", batch_size)
    logger.info("=" * 60)

    src_engine = _make_engine(sqlite_url, "SQLite")

    if dry_run:
        overall_stats: Dict[str, Dict[str, int]] = {}
        with src_engine.connect() as src_conn:
            src_inspector = inspect(src_conn)
            users_src = _resolve_users_table(src_inspector)

            for table in ordered:
                logger.info("Checking table : %s", table)
                # For the legacy 'user' → 'users' mapping
                src_table_name = users_src if table == "users" and users_src else table
                if src_table_name is None:
                    logger.error("No users/user table found in SQLite.")
                    return False
                overall_stats[table] = _dry_run_table(src_table_name, src_conn)
    else:
        if not postgres_url:
            logger.error(
                "A Postgres URL is required for a live migration. "
                "Pass --postgres or set SUPABASE_DB_URL / DATABASE_URL."
            )
            return False

        pg_url = normalize_postgres_url(postgres_url)
        dst_engine = _make_engine(pg_url, "PostgreSQL")

        # Verify Postgres connectivity before touching data
        try:
            with dst_engine.connect() as probe:
                probe.execute(text("SELECT 1"))
        except OperationalError as exc:
            logger.error("Cannot connect to Postgres: %s", exc)
            return False

        overall_stats = {}
        # Single Postgres transaction — full rollback on any error
        with src_engine.connect() as src_conn, dst_engine.begin() as dst_conn:
            src_inspector = inspect(src_conn)
            users_src = _resolve_users_table(src_inspector)

            for table in ordered:
                logger.info("Migrating table: %s", table)
                src_table_name = users_src if table == "users" and users_src else table
                if table == "users" and src_table_name is None:
                    logger.error("No users/user table found in SQLite — aborting.")
                    raise RuntimeError("Missing users table in source database.")
                try:
                    overall_stats[table] = _live_migrate_table(
                        table=table,
                        src_table_name=src_table_name or table,
                        src_conn=src_conn,
                        dst_conn=dst_conn,
                        truncate=truncate,
                        batch_size=batch_size,
                    )
                except Exception as exc:
                    logger.error(
                        "  [%s] FAILED — rolling back all changes: %s",
                        table,
                        exc,
                        exc_info=True,
                    )
                    raise  # triggers dst_engine.begin() rollback

    # Print summary
    logger.info("=" * 60)
    logger.info("Summary")
    logger.info("-" * 60)
    total_migrated = 0
    for table, stats in overall_stats.items():
        if dry_run:
            logger.info(
                "  %-30s  would_migrate=%-6d  skipped=%d",
                table,
                stats.get("would_migrate", 0),
                stats.get("skipped", 0),
            )
            total_migrated += stats.get("would_migrate", 0)
        else:
            logger.info(
                "  %-30s  inserted=%-6d  skipped=%d",
                table,
                stats.get("inserted", 0),
                stats.get("skipped", 0),
            )
            total_migrated += stats.get("inserted", 0)

    logger.info("-" * 60)
    if dry_run:
        logger.info("  TOTAL  would_migrate=%d", total_migrated)
        logger.info("Dry run complete — no data was written to Postgres.")
    else:
        logger.info("  TOTAL  inserted=%d", total_migrated)
        logger.info("Migration complete.")
    logger.info("=" * 60)
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate data from SQLite to PostgreSQL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    src_group = parser.add_mutually_exclusive_group()
    src_group.add_argument(
        "--sqlite",
        metavar="URL",
        help="SQLAlchemy URL for the SQLite source, e.g. sqlite:///./data/app.db",
    )
    src_group.add_argument(
        "--sqlite-path",
        metavar="PATH",
        default="instance/users.db",
        help="Path to the SQLite file (alternative to --sqlite). "
             "Defaults to instance/users.db.",
    )

    parser.add_argument(
        "--postgres",
        metavar="URL",
        default=(
            os.getenv("SUPABASE_DB_URL")
            or os.getenv("POSTGRES_DATABASE_URL")
            or os.getenv("DATABASE_URL")
        ),
        help="Postgres destination URL (postgresql:// or postgres://). "
             "Also read from SUPABASE_DB_URL, POSTGRES_DATABASE_URL, or DATABASE_URL. "
             "Not required for --dry-run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Read from SQLite and report row counts — no Postgres connection made.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        default=False,
        help="TRUNCATE each Postgres table (CASCADE) before inserting. "
             "Useful for a clean re-migration. Ignored during --dry-run.",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        metavar="TABLE",
        help="Migrate only these tables (space-separated). "
             "Defaults to all tables in FK-safe order.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        metavar="N",
        help="Number of rows per INSERT batch (default: 500).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # Resolve SQLite URL
    if args.sqlite:
        sqlite_url = args.sqlite
        if not sqlite_url.startswith("sqlite"):
            logger.error("--sqlite must be a sqlite:/// URL, got: %s", sqlite_url)
            sys.exit(1)
    else:
        sqlite_url = sqlite_url_from_path(args.sqlite_path)

    # Postgres URL is optional for dry-run only
    postgres_url: Optional[str] = args.postgres
    if not args.dry_run:
        if not postgres_url:
            logger.error(
                "Provide a Postgres URL via --postgres, SUPABASE_DB_URL, "
                "POSTGRES_DATABASE_URL, or DATABASE_URL."
            )
            sys.exit(2)
        if postgres_url.startswith("sqlite"):
            logger.error(
                "--postgres must be a Postgres URL, not a SQLite URL: %s",
                postgres_url,
            )
            sys.exit(2)

    try:
        success = run_migration(
            sqlite_url=sqlite_url,
            postgres_url=postgres_url,
            dry_run=args.dry_run,
            truncate=args.truncate,
            tables=args.tables,
            batch_size=args.batch_size,
        )
    except Exception as exc:
        logger.error("Migration failed: %s", exc)
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

"""
Migration: add processing-progress tracking columns and extracted_urls to documents table.

Adds (idempotent — safe to re-run, skips existing columns):
  - processing_progress    INTEGER  DEFAULT 0
  - processing_stage       TEXT     DEFAULT 'queued'
  - retry_count            INTEGER  DEFAULT 0
  - last_error_traceback   TEXT
  - processing_started_at  DATETIME
  - completed_at           DATETIME
  - extracted_urls         TEXT

Run once from the backend directory:
    python migrate_add_processing_columns.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine
from sqlalchemy import text, inspect


COLUMNS = [
    ("processing_progress",   "INTEGER DEFAULT 0"),
    ("processing_stage",      "TEXT DEFAULT 'queued'"),
    ("retry_count",           "INTEGER DEFAULT 0"),
    ("last_error_traceback",  "TEXT DEFAULT NULL"),
    ("processing_started_at", "DATETIME DEFAULT NULL"),
    ("completed_at",          "DATETIME DEFAULT NULL"),
    ("extracted_urls",        "TEXT DEFAULT NULL"),
]


def migrate():
    inspector = inspect(engine)
    existing = {col["name"] for col in inspector.get_columns("documents")}

    added = []
    skipped = []

    with engine.begin() as conn:
        for col_name, col_def in COLUMNS:
            if col_name in existing:
                skipped.append(col_name)
                continue
            conn.execute(text(
                f"ALTER TABLE documents ADD COLUMN {col_name} {col_def}"
            ))
            added.append(col_name)

    if added:
        print(f"✅ Added columns: {added}")
    if skipped:
        print(f"ℹ️  Already existed (skipped): {skipped}")
    if not added:
        print("Nothing to do — all columns already present.")


if __name__ == "__main__":
    migrate()

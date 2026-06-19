"""
Migration: add extracted_urls column to documents table.

Run once:
    python migrate_add_extracted_urls.py

Safe to re-run — skips if the column already exists.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine
from sqlalchemy import text, inspect

def migrate():
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("documents")]

    if "extracted_urls" in columns:
        print("Column 'extracted_urls' already exists — skipping.")
        return

    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE documents ADD COLUMN extracted_urls TEXT DEFAULT NULL"
        ))
    print("Migration complete: added 'extracted_urls' to documents table.")

if __name__ == "__main__":
    migrate()

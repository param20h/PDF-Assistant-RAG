"""
One-time migration script to add indexes on documents.user_id and documents.filename.
Run this from the 'backend' directory.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text

def migrate():
    print("🚀 Starting migration: adding indexes on 'documents' table...")
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_documents_user_id ON documents (user_id)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_documents_filename ON documents (filename)"
            ))
            conn.commit()
        print("✅ Migration successful!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    migrate()
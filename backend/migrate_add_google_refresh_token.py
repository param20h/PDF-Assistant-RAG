"""
One-time migration script to add the 'google_refresh_token' column to users.
Run this from the 'backend' directory.
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

from app.database import engine


def migrate():
    print("Starting migration: adding 'google_refresh_token' column to 'users' table...")
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN google_refresh_token TEXT"))
            conn.commit()
        print("Migration successful!")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("Column 'google_refresh_token' already exists. Skipping migration.")
        else:
            print(f"Migration failed: {e}")


if __name__ == "__main__":
    migrate()

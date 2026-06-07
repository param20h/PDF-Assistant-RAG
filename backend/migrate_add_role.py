"""
One-time migration script to add the 'role' column to the 'users' table.
Run this from the 'backend' directory.
"""
import sys
import os

# Add the current directory to sys.path to allow importing 'app'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text

def migrate():
    print("🚀 Starting migration: adding 'role' column to 'users' table...")
    try:
        with engine.connect() as conn:
            # SQLite doesn't support adding a column with NOT NULL without a default value 
            # if there are already rows, but we provide a default 'user'.
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user'"
            ))
            # Update existing rows to have the 'user' role
            conn.execute(text(
                "UPDATE users SET role = 'user' WHERE role IS NULL"
            ))
            conn.execute(text(
                "UPDATE users SET role = 'admin' WHERE is_admin = 1"
            ))
            conn.commit()
        print("✅ Migration successful!")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("ℹ️ Column 'role' already exists. Skipping migration.")
        else:
            print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    migrate()

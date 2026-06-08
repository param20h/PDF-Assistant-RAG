# migrations/add_keywords_column.py
"""
One-off migration: adds the `keywords` TEXT column to the `documents` table.
Run once: python migrations/add_keywords_column.py
"""
import sqlite3
import os

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./data/app.db").replace("sqlite:///", "")

def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE documents ADD COLUMN keywords TEXT;")
        conn.commit()
        print(f"✅ Column 'keywords' added to 'documents' in {DB_PATH}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("ℹ️  Column 'keywords' already exists — nothing to do.")
        else:
            raise
    finally:
        conn.close()

if __name__ == "__main__":
    run()

"""
Safe migration script to move data from SQLite to PostgreSQL.
Handles Users, Documents, and Chat Messages while preserving UUIDs.
"""
import sys
import argparse
import logging
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

# Add parent directory to path to import app modules
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import Base, User, Document, ChatMessage, ApiKey, ChatSession, DriveConnection, SharedMessage

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def migrate(sqlite_url: str, postgres_url: str, dry_run: bool = False):
    """Perform the migration from SQLite to Postgres."""
    logger.info("Starting migration from %s to %s", sqlite_url, postgres_url)
    if dry_run:
        logger.info("DRY RUN MODE: No changes will be committed to Postgres.")

    # Create engines
    sqlite_engine = create_engine(sqlite_url)
    postgres_engine = create_engine(postgres_url)

    # Initialize Postgres schema
    if not dry_run:
        logger.info("Initializing Postgres schema...")
        Base.metadata.create_all(postgres_engine)

    # Create sessions
    SqliteSession = sessionmaker(bind=sqlite_engine)
    PostgresSession = sessionmaker(bind=postgres_engine)

    sqlite_db = SqliteSession()
    postgres_db = PostgresSession()

    try:
        # 1. Migrate Users
        logger.info("Migrating Users...")
        users = sqlite_db.query(User).all()
        for user in users:
            # Check if user already exists in postgres
            existing = postgres_db.query(User).filter(User.id == user.id).first()
            if not existing:
                # Merge into postgres session
                # We use make_transient to avoid session conflicts
                sqlite_db.expunge(user)
                if not dry_run:
                    postgres_db.merge(user)
        
        if not dry_run:
            postgres_db.commit()
        logger.info("Migrated %d users.", len(users))

        # 2. Migrate Documents
        logger.info("Migrating Documents...")
        docs = sqlite_db.query(Document).all()
        for doc in docs:
            existing = postgres_db.query(Document).filter(Document.id == doc.id).first()
            if not existing:
                sqlite_db.expunge(doc)
                if not dry_run:
                    postgres_db.merge(doc)
        
        if not dry_run:
            postgres_db.commit()
        logger.info("Migrated %d documents.", len(docs))

        # 3. Migrate Chat Sessions
        logger.info("Migrating Chat Sessions...")
        sessions = sqlite_db.query(ChatSession).all()
        for session in sessions:
            existing = postgres_db.query(ChatSession).filter(ChatSession.id == session.id).first()
            if not existing:
                sqlite_db.expunge(session)
                if not dry_run:
                    postgres_db.merge(session)
        
        if not dry_run:
            postgres_db.commit()
        logger.info("Migrated %d chat sessions.", len(sessions))

        # 4. Migrate Chat Messages
        logger.info("Migrating Chat Messages...")
        messages = sqlite_db.query(ChatMessage).all()
        for msg in messages:
            existing = postgres_db.query(ChatMessage).filter(ChatMessage.id == msg.id).first()
            if not existing:
                sqlite_db.expunge(msg)
                if not dry_run:
                    postgres_db.merge(msg)
        
        if not dry_run:
            postgres_db.commit()
        logger.info("Migrated %d chat messages.", len(messages))

        # 5. Migrate API Keys
        logger.info("Migrating API Keys...")
        keys = sqlite_db.query(ApiKey).all()
        for key in keys:
            existing = postgres_db.query(ApiKey).filter(ApiKey.id == key.id).first()
            if not existing:
                sqlite_db.expunge(key)
                if not dry_run:
                    postgres_db.merge(key)
        
        if not dry_run:
            postgres_db.commit()
        logger.info("Migrated %d API keys.", len(keys))

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error("Migration failed: %s", e)
        postgres_db.rollback()
        raise
    finally:
        sqlite_db.close()
        postgres_db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate data from SQLite to PostgreSQL")
    parser.add_argument("--sqlite", required=True, help="SQLite connection URL (e.g., sqlite:///instance/app.db)")
    parser.add_argument("--postgres", required=True, help="Postgres connection URL (e.g., postgresql://user:pass@localhost/db)")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without committing changes")
    
    args = parser.parse_args()
    
    migrate(args.sqlite, args.postgres, args.dry_run)

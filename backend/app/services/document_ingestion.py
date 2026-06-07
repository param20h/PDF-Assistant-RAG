"""Reusable document ingestion pipeline."""
import traceback
import logging
from datetime import datetime, timezone

from app.models import Document
from app.rag.chunker import chunk_document, get_page_count
from app.rag.vectorstore import store_chunks
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _update_progress(document_id: str, progress: int, stage: str, error: str = None):
    """Update document progress fields in the database."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.processing_progress = progress
            doc.processing_stage = stage
            if error:
                doc.error_message = error
            db.commit()
    except Exception as e:
        logger.warning("Failed to update progress for %s: %s", document_id, e)
    finally:
        db.close()


def ingest_document(document_id: str, filepath: str, original_name: str, user_id: str):
    """
    Process a document: chunk it, generate embeddings, store vectors, summarize,
    and update the database record.
    """
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(
            Document.id == document_id,
            Document.is_deleted.is_(False),
        ).first()
        if not doc:
            logger.error("Document %s not found for ingestion", document_id)
            return

        doc.status = "processing"
        doc.processing_stage = "extracting"
        doc.processing_progress = 10
        doc.error_message = None
        doc.last_error_traceback = None
        db.commit()

        page_count = get_page_count(filepath)
        doc.page_count = page_count
        doc.processing_progress = 20
        db.commit()

        try:
            chunk_kwargs = {}
            if doc.chunk_size is not None:
                chunk_kwargs["chunk_size"] = doc.chunk_size
            if doc.chunk_overlap is not None:
                chunk_kwargs["chunk_overlap"] = doc.chunk_overlap
            doc.processing_stage = "chunking"
            doc.processing_progress = 30
            db.commit()
            chunks = chunk_document(filepath, **chunk_kwargs)
        except TypeError:
            chunks = chunk_document(filepath)

        if not chunks:
            doc.status = "failed"
            doc.processing_progress = 0
            doc.error_message = "No text could be extracted from the document"
            db.commit()
            return

        doc.processing_progress = 50
        doc.processing_stage = "indexing"
        db.commit()

        try:
            from app.rag.graph_builder import build_graph, save_graph

            graph = build_graph(chunks)
            save_graph(graph, user_id=user_id, document_id=document_id)
        except Exception as e:
            logger.warning("Could not build knowledge graph for document %s: %s", document_id, e)

        doc.processing_progress = 70
        doc.processing_stage = "embedding"
        db.commit()

        chunk_count = store_chunks(
            chunks=chunks,
            document_id=document_id,
            filename=original_name,
            user_id=user_id,
        )

        doc.processing_progress = 85
        db.commit()

        try:
            from app.rag.summarizer import generate_document_summary

            summary = generate_document_summary(filepath, max_sentences=2)
            if summary:
                doc.summary = summary
                db.commit()
        except Exception as e:
            logger.warning("Could not generate summary for document %s: %s", document_id, e)
            doc.summary = None

        doc.chunk_count = chunk_count
        doc.status = "ready"
        doc.processing_progress = 100
        doc.processing_stage = "completed"
        doc.completed_at = datetime.now(timezone.utc)
        doc.error_message = None
        db.commit()

        logger.info(
            "Document %s ingested: %s pages, %s chunks",
            document_id,
            page_count,
            chunk_count,
        )

    except Exception as e:
        logger.error("Ingestion error for %s: %s", document_id, e)
        db.rollback()
        try:
            doc = db.query(Document).filter(
                Document.id == document_id,
                Document.is_deleted.is_(False),
            ).first()
            if doc:
                doc.status = "failed"
                doc.processing_progress = 0
                doc.error_message = str(e)[:500]
                doc.last_error_traceback = traceback.format_exc()[:2000]
                db.commit()
        except Exception:
            logger.exception("Failed to mark document %s as failed", document_id)
    finally:
        db.close()

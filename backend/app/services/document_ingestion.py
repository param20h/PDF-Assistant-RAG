"""Reusable document ingestion pipeline."""
import logging

from app.models import Document
from app.rag.chunker import chunk_document, get_page_count
from app.rag.vectorstore import store_chunks

logger = logging.getLogger(__name__)


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
        doc.error_message = None
        db.commit()

        page_count = get_page_count(filepath)
        doc.page_count = page_count

        try:
            chunk_kwargs = {}
            if doc.chunk_size is not None:
                chunk_kwargs["chunk_size"] = doc.chunk_size
            if doc.chunk_overlap is not None:
                chunk_kwargs["chunk_overlap"] = doc.chunk_overlap
            chunks = chunk_document(filepath, **chunk_kwargs)
        except TypeError:
            # Preserve compatibility with patched/test implementations.
            chunks = chunk_document(filepath)

        if not chunks:
            doc.status = "failed"
            doc.error_message = "No text could be extracted from the document"
            db.commit()
            return

        try:
            from app.rag.graph_builder import build_graph, save_graph

            graph = build_graph(chunks)
            save_graph(graph, user_id=user_id, document_id=document_id)
        except Exception as e:
            logger.warning("Could not build knowledge graph for document %s: %s", document_id, e)

        chunk_count = store_chunks(
            chunks=chunks,
            document_id=document_id,
            filename=original_name,
            user_id=user_id,
        )

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
                doc.error_message = str(e)[:500]
                db.commit()
        except Exception:
            logger.exception("Failed to mark document %s as failed", document_id)
    finally:
        db.close()

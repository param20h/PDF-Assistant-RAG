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

        # ── Proximity caption pass (PDF only) ────────────────────────────────
        # Write bounding-box-derived captions into image chunks BEFORE store_chunks()
        # so generate_captions_for_chunks() in vectorstore.py only needs to handle
        # the OCR / placeholder fallback for any images without adjacent text.
        ext = filepath.rsplit(".", 1)[-1].lower()
        if ext == "pdf":
            try:
                from app.rag.vision import extract_captions_from_pdf

                pdf_captions = extract_captions_from_pdf(filepath)
                # Build lookup: page -> [captions in figure_index order]
                caption_map: dict = {}
                for cap in pdf_captions:
                    caption_map.setdefault(cap["page"], []).append(cap)

                fig_counters: dict = {}
                for chunk in chunks:
                    if not chunk.get("image_bytes"):
                        continue
                    page = chunk.get("page", 1)
                    idx = fig_counters.get(page, 0)
                    page_caps = caption_map.get(page, [])
                    if idx < len(page_caps) and page_caps[idx]["caption"]:
                        chunk["image_caption"] = page_caps[idx]["caption"]
                        chunk["bbox"] = str(page_caps[idx]["bbox"])
                    fig_counters[page] = idx + 1
            except Exception as exc:
                logger.warning(
                    "Proximity caption extraction failed for %s: %s", document_id, exc
                )
        # ── End proximity caption pass ────────────────────────────────────────

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

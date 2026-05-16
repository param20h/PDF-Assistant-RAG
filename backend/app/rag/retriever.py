"""
Two-stage retrieval: ChromaDB similarity search + cross-encoder reranking.
"""
import logging
from typing import List, Dict, Any, Optional
from app.config import get_settings
from app.rag.embeddings import embed_query
from app.rag.vectorstore import query_chunks

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Singleton reranker ───────────────────────────────
_reranker = None


def get_reranker():
    """Load cross-encoder reranker model (singleton)."""
    global _reranker

    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading reranker: {settings.RERANKER_MODEL}")
            _reranker = CrossEncoder(settings.RERANKER_MODEL, max_length=512)
            logger.info("Reranker loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load reranker: {e}. Falling back to embedding-only retrieval.")
            _reranker = "disabled"

    return _reranker if _reranker != "disabled" else None


def retrieve(
    query: str,
    user_id: str,
    document_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Two-stage retrieval pipeline:
    1. ChromaDB similarity search (top-K broad)
    2. Cross-encoder reranking (top-K refined)

    Returns chunks with confidence scores.
    """
    # ── Stage 1: Embedding search ────────────────────
    query_vector = embed_query(query)
    candidates = query_chunks(
        query_embedding=query_vector,
        user_id=user_id,
        document_id=document_id,
        top_k=settings.TOP_K_RETRIEVAL,
    )

    if not candidates:
        return []

    # ── Stage 2: Cross-encoder reranking ─────────────
    reranker = get_reranker()

    if reranker is not None and len(candidates) > 1:
        try:
            # Build query-document pairs for reranking
            pairs = [(query, chunk["text"]) for chunk in candidates]
            rerank_scores = reranker.predict(pairs)

            # Assign rerank scores
            for i, chunk in enumerate(candidates):
                chunk["rerank_score"] = float(rerank_scores[i])

            # Sort by rerank score (descending)
            candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

        except Exception as e:
            logger.warning(f"Reranking failed, using embedding scores: {e}")

    # ── Take top-K after reranking ───────────────────
    top_chunks = candidates[:settings.TOP_K_RERANK]

    # ── Calculate confidence percentages ─────────────
    if top_chunks:
        max_score = max(
            chunk.get("rerank_score", chunk.get("score", 0))
            for chunk in top_chunks
        )
        max_score = max(max_score, 0.001)  # Avoid division by zero

        for chunk in top_chunks:
            raw = chunk.get("rerank_score", chunk.get("score", 0))
            chunk["confidence"] = round((raw / max_score) * 100, 1)
            # Clean up internal score
            if "rerank_score" in chunk:
                chunk["score"] = round(chunk["rerank_score"], 4)
                del chunk["rerank_score"]

    return top_chunks

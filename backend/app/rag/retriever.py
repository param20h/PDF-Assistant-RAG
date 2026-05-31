"""
Two-stage retrieval: Hybrid Ensemble (ChromaDB + BM25) + cross-encoder reranking.
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional

# In LangChain 1.3.2+, EnsembleRetriever moved to langchain_classic (imported by langchain_community)
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document as LangchainDocument
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from pydantic import Field

from app.config import get_settings
from app.rag.embeddings import embed_query
from app.rag.tracing import trace_function
from app.rag.vectorstore import query_chunks

logger = logging.getLogger(__name__)
settings = get_settings()
MAX_QUERY_VARIANTS = 4

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


class CustomVectorRetriever(BaseRetriever):
    user_id: str = Field(description="User ID")
    document_id: Optional[str] = Field(default=None, description="Document ID")
    top_k: int = Field(default=10, description="Top K results")

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[LangchainDocument]:
        query_vector = embed_query(query)
        candidates = query_chunks(
            query_embedding=query_vector,
            user_id=self.user_id,
            document_id=self.document_id,
            top_k=self.top_k,
        )
        return [LangchainDocument(page_content=c["text"], metadata=c) for c in candidates]


class CustomBM25Retriever(BaseRetriever):
    user_id: str = Field(description="User ID")
    document_id: Optional[str] = Field(default=None, description="Document ID")
    top_k: int = Field(default=10, description="Top K results")

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[LangchainDocument]:
        from app.rag.bm25 import query_bm25
        candidates = query_bm25(
            query=query,
            user_id=self.user_id,
            document_id=self.document_id,
            top_k=self.top_k,
        )
        return [LangchainDocument(page_content=c["text"], metadata=c) for c in candidates]


def transform_query(query: str) -> List[str]:
    """Rewrite a user question into multiple retrieval-friendly search queries."""
    original_query = query.strip()
    if not original_query:
        return []

    try:
        generated_queries = _generate_query_variants(original_query)
    except Exception as e:
        logger.warning(f"Query transformation failed, using original query only: {e}")
        generated_queries = []

    return _dedupe_queries([original_query, *generated_queries])[:MAX_QUERY_VARIANTS]


def _generate_query_variants(query: str) -> List[str]:
    """Use the configured LLM to split/rewrite a user query for semantic search."""
    if not settings.HF_TOKEN:
        return []

    from huggingface_hub import InferenceClient

    client = InferenceClient(token=settings.HF_TOKEN)
    prompt = (
        "Rewrite the user question into concise semantic search queries for document retrieval. "
        "Split independent topics into separate queries. Return a JSON array of strings only. "
        f"User question: {query}"
    )
    response = client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You create optimized search queries for a RAG retriever.",
            },
            {"role": "user", "content": prompt},
        ],
        model=settings.LLM_MODEL,
        max_tokens=256,
        temperature=0.2,
    )

    if not response.choices:
        return []

    content = response.choices[0].message.content or ""
    return _parse_query_variants(content)


def _parse_query_variants(content: str) -> List[str]:
    """Parse LLM output into a list even when it adds light prose around JSON."""
    content = content.strip()
    if not content:
        return []

    parsed = _try_parse_query_json(content)
    if parsed is not None:
        return parsed

    match = re.search(r"\[[\s\S]*\]", content)
    if match:
        parsed = _try_parse_query_json(match.group(0))
        if parsed is not None:
            return parsed

    queries = []
    for line in content.splitlines():
        cleaned = re.sub(r"^\s*[-*\d.)]+\s*", "", line).strip().strip('"')
        if cleaned:
            queries.append(cleaned)
    return queries


def _try_parse_query_json(content: str) -> Optional[List[str]]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, dict):
        parsed = parsed.get("queries", [])

    if not isinstance(parsed, list):
        return []

    return [item.strip() for item in parsed if isinstance(item, str) and item.strip()]


def _dedupe_queries(queries: List[str]) -> List[str]:
    deduped = []
    seen = set()
    for query in queries:
        normalized = " ".join(query.split())
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            deduped.append(normalized)
    return deduped


def _candidate_key(chunk: Dict[str, Any]) -> str:
    for key in ("id", "chunk_id"):
        if chunk.get(key):
            return str(chunk[key])

    text = str(chunk.get("text", ""))
    return "|".join(
        str(part)
        for part in (
            chunk.get("document_id", ""),
            chunk.get("filename", ""),
            chunk.get("page", ""),
            text[:200],
        )
    )


def _merge_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}

    for candidate in candidates:
        candidate_copy = dict(candidate)
        key = _candidate_key(candidate_copy)
        existing = merged.get(key)

        if existing is None or candidate_copy.get("score", 0) > existing.get("score", 0):
            merged[key] = candidate_copy

    return list(merged.values())


@trace_function(
    "retrieve",
    metadata_factory=lambda query, user_id, document_id=None: {
        "user_id": user_id,
        "document_id": document_id,
        "embedding_model": settings.EMBEDDING_MODEL,
        "reranker_model": settings.RERANKER_MODEL,
        "top_k_retrieval": settings.TOP_K_RETRIEVAL,
        "top_k_rerank": settings.TOP_K_RERANK,
    },
)
def retrieve(
    query: str,
    user_id: str,
    document_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Two-stage retrieval pipeline:
    1. Hybrid Search (Vector + BM25 via EnsembleRetriever with RRF) with Query Transformation
    2. Cross-encoder reranking (top-K refined)

    Returns chunks with confidence scores.
    """
    # ── Stage 1: Hybrid Search with Query Transformation ─────────────
    vector_retriever = CustomVectorRetriever(
        user_id=user_id,
        document_id=document_id,
        top_k=settings.TOP_K_RETRIEVAL,
    )

    bm25_retriever = CustomBM25Retriever(
        user_id=user_id,
        document_id=document_id,
        top_k=settings.TOP_K_RETRIEVAL,
    )

    ensemble_retriever = EnsembleRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        weights=[0.6, 0.4]
    )

    all_candidates = []
    for search_query in transform_query(query):
        docs = ensemble_retriever.invoke(search_query)
        for i, doc in enumerate(docs):
            chunk = doc.metadata.copy()
            # Preserve a mock score based on rank for fallback if reranker fails
            # We use 1.0/(i+1) as a base RRF-like score
            chunk["score"] = 1.0 / (i + 1)
            all_candidates.append(chunk)

    if not all_candidates:
        return []

    candidates = _merge_candidates(all_candidates)

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
            logger.warning(f"Reranking failed, using hybrid scores: {e}")

    # Ensure candidates are sorted by best available score
    candidates.sort(key=lambda x: x.get("rerank_score", x.get("score", 0)), reverse=True)

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

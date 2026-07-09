"""
Two-stage retrieval: Hybrid Search (Vector + BM25 via RRF) + cross-encoder reranking.
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional

from app.config import get_settings
from app.rag.embeddings import embed_query
from app.rag.tracing import trace_function
from app.rag.vectorstore import query_chunks
from app.rag.reranker import get_reranker

logger = logging.getLogger(__name__)
settings = get_settings()
MAX_QUERY_VARIANTS = 4


# ── RRF core ─────────────────────────────────────────────────────────────────

def rrf_merge(
    vector_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    k: int = 60,
) -> List[Dict[str, Any]]:
    """Merge vector and BM25 ranked lists using Reciprocal Rank Fusion.

    RRF formula:  score(d) = Σ  1 / (k + rank(d, list))
    where rank is 1-based and k=60 is the standard smoothing constant.

    Args:
        vector_results: Chunks from ChromaDB, ordered by descending similarity.
        bm25_results:   Chunks from BM25, ordered by descending BM25 score.
        k:              RRF smoothing constant (default 60).

    Returns:
        Deduplicated list of chunks sorted by descending RRF score, each chunk
        carrying an ``rrf_score`` field.
    """
    rrf_scores: Dict[str, float] = {}
    chunk_store: Dict[str, Dict[str, Any]] = {}

    def _key(chunk: Dict[str, Any]) -> str:
        """Stable deduplication key — prefer explicit IDs, fall back to content hash."""
        for field in ("id", "chunk_id"):
            if chunk.get(field):
                return str(chunk[field])
        text = str(chunk.get("text", ""))
        return "|".join([
            str(chunk.get("document_id", "")),
            str(chunk.get("page", "")),
            text[:200],
        ])

    def _accumulate(results: List[Dict[str, Any]]) -> None:
        for rank, chunk in enumerate(results, start=1):
            key = _key(chunk)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)
            if key not in chunk_store or chunk.get("score", 0) > chunk_store[key].get("score", 0):
                chunk_store[key] = chunk

    _accumulate(vector_results)
    _accumulate(bm25_results)

    merged = []
    for key, rrf_score in sorted(rrf_scores.items(), key=lambda t: t[1], reverse=True):
        chunk = chunk_store[key].copy()
        chunk["rrf_score"] = round(rrf_score, 6)
        merged.append(chunk)

    return merged


# ── Query helpers ─────────────────────────────────────────────────────────────

def transform_query(query: str) -> List[str]:
    """Rewrite a user question into multiple retrieval-friendly search queries."""
    original_query = query.strip()
    if not original_query:
        return []

    try:
        generated_queries = _generate_query_variants(original_query)
    except Exception as e:
        logger.warning("Query transformation failed, using original query only: %s", e)
        generated_queries = []

    return _dedupe_queries([original_query, *generated_queries])[:MAX_QUERY_VARIANTS]


def _generate_query_variants(query: str) -> List[str]:
    """Use the configured LLM to rewrite a user query into 3 semantic variations.

    Each variation rephrases the original from a different angle so that
    BM25 and ChromaDB retrieve a broader, complementary set of chunks.
    The original query is always prepended by the caller (transform_query),
    so we ask for exactly 3 *additional* variants here.
    """
    if not settings.HF_TOKEN:
        return []

    from huggingface_hub import InferenceClient

    client = InferenceClient(token=settings.HF_TOKEN)

    prompt = (
        "Generate exactly 3 semantic variations of the user question below. "
        "Each variation must preserve the original meaning but use different "
        "vocabulary, phrasing, or sentence structure to improve document retrieval coverage. "
        "Do NOT add new topics or change the intent. "
        "Return ONLY a JSON array of 3 strings, with no extra text, markdown, or explanation.\n\n"
        f"User question: {query}\n\n"
        'Example output: ["variation one", "variation two", "variation three"]'
    )

    response = client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a query rewriter for a RAG retrieval system. "
                    "You output only valid JSON arrays of strings, nothing else."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        model=settings.LLM_MODEL,
        max_tokens=256,
        temperature=0.3,
    )

    if not response.choices:
        return []

    content = response.choices[0].message.content or ""
    variants = _parse_query_variants(content)

    # Cap at 3 variants as requested — the original is added by transform_query
    return variants[:3]


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


def _merge_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate a flat candidate list, keeping the highest-scored entry per key."""
    merged: Dict[str, Dict[str, Any]] = {}
    for candidate in candidates:
        candidate_copy = dict(candidate)
        key = "|".join([
            str(candidate_copy.get("document_id", "")),
            str(candidate_copy.get("page", "")),
            str(candidate_copy.get("text", ""))[:200],
        ])
        existing = merged.get(key)
        if existing is None or candidate_copy.get("score", 0) > existing.get("score", 0):
            merged[key] = candidate_copy
    return list(merged.values())


# ── Main retrieval pipeline ───────────────────────────────────────────────────

@trace_function(
    "retrieve",
    metadata_factory=lambda query, user_id, document_id=None, document_ids=None, top_k=None: {
        "user_id": user_id,
        "document_id": document_id,
        "embedding_model": settings.EMBEDDING_MODEL,
        "reranker_model": settings.RERANKER_MODEL,
        "top_k_retrieval": settings.TOP_K_RETRIEVAL,
        "top_k_rerank": settings.TOP_K_RERANK,
        "hybrid_search": settings.USE_HYBRID_SEARCH,
        "rrf_k": settings.RRF_K,
    },
)
def retrieve(
    query: str,
    user_id: str,
    document_id: Optional[str] = None,
    document_ids: Optional[List[str]] = None,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Two-stage retrieval pipeline:
    1. Hybrid Search — Vector (ChromaDB) + BM25 merged via Reciprocal Rank Fusion (RRF),
       applied across all transformed query variants.
    2. Cross-encoder reranking — top-K refined by a cross-encoder model.

    Falls back to vector-only when USE_HYBRID_SEARCH=False or rank_bm25 is absent.
    Returns chunks with confidence scores.
    """
    effective_top_k = top_k if top_k is not None else settings.TOP_K_RETRIEVAL

    # ── Stage 1: Hybrid retrieval with query transformation ───────────────────
    all_candidates: List[Dict[str, Any]] = []

    for search_query in transform_query(query):
        query_vector = embed_query(search_query)

        # Vector results (always)
        vector_results = query_chunks(
            query_embedding=query_vector,
            user_id=user_id,
            document_id=document_id,
            document_ids=document_ids,
            top_k=effective_top_k,
        )

        if settings.USE_HYBRID_SEARCH:
            try:
                from app.rag.bm25 import query_bm25
                bm25_results = query_bm25(
                    query=search_query,
                    user_id=user_id,
                    document_id=document_id,
                    document_ids=document_ids,
                    top_k=effective_top_k,
                )
            except Exception as exc:
                logger.warning("BM25 retrieval failed, using vector-only: %s", exc)
                bm25_results = []

            merged = rrf_merge(
                vector_results=vector_results,
                bm25_results=bm25_results,
                k=settings.RRF_K,
            )

            for chunk in merged:
                chunk["score"] = chunk.pop("rrf_score")

            all_candidates.extend(merged)
        else:
            all_candidates.extend(vector_results)

    if not all_candidates:
        return []

    candidates = _merge_candidates(all_candidates)

    # ── Stage 2: Cross-encoder reranking ─────────────────────────────────────
    reranker = get_reranker()

    if reranker is not None:
        top_chunks = reranker.rerank(
            query=query,
            documents=candidates,
            top_k=settings.TOP_K_RERANK,
        )
    else:
        candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_chunks = candidates[:settings.TOP_K_RERANK]

    # ── Confidence normalisation ──────────────────────────────────────────────
    if top_chunks:
        max_score = max(
            chunk.get("rerank_score", chunk.get("score", 0))
            for chunk in top_chunks
        )
        max_score = max(max_score, 0.001)

        for chunk in top_chunks:
            raw = chunk.get("rerank_score", chunk.get("score", 0))
            chunk["confidence"] = round((raw / max_score) * 100, 1)
            if "rerank_score" in chunk:
                chunk["score"] = round(chunk["rerank_score"], 4)
                del chunk["rerank_score"]

    from app.observability import chunks_retrieved_var
    chunks_retrieved_var.set(len(top_chunks))
    logger.info(
        "Retrieved %d relevant chunks for query: '%s'",
        len(top_chunks),
        query,
    )

    return top_chunks

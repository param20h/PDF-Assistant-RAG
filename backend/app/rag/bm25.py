"""
BM25 Keyword Search implementation using rank_bm25.
Stores a BM25 index per document to allow easy updates and deletions.
"""
import json
import os
import glob
import logging
import re
from typing import List, Dict, Any, Optional

from app.config import get_settings

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

logger = logging.getLogger(__name__)
settings = get_settings()


def _bm25_to_dict(bm25: BM25Okapi) -> dict:
    """Serialize BM25Okapi internals to a JSON-safe dict."""
    return {
        "corpus_size": bm25.corpus_size,
        "avgdl": bm25.avgdl,
        "doc_freqs": [{str(k): v for k, v in doc.items()} for doc in bm25.doc_freqs],
        "idf": {str(k): v for k, v in bm25.idf.items()},
        "doc_len": bm25.doc_len,
        "k1": bm25.k1,
        "b": bm25.b,
        "epsilon": bm25.epsilon,
    }


def _dict_to_bm25(data: dict) -> BM25Okapi:
    """Reconstruct a BM25Okapi instance from a dict saved by _bm25_to_dict."""
    bm25 = object.__new__(BM25Okapi)
    bm25.corpus_size = data["corpus_size"]
    bm25.avgdl = data["avgdl"]
    bm25.doc_freqs = [{int(k): v for k, v in doc.items()} for doc in data["doc_freqs"]]
    bm25.idf = {int(k): v for k, v in data["idf"].items()}
    bm25.doc_len = data["doc_len"]
    bm25.k1 = data["k1"]
    bm25.b = data["b"]
    bm25.epsilon = data["epsilon"]
    return bm25


def get_bm25_dir(user_id: str) -> str:
    """Get the directory path for a user's BM25 indexes."""
    clean_id = user_id.replace("-", "_")
    path = os.path.join(settings.CHROMA_PERSIST_DIR, "bm25", clean_id)
    os.makedirs(path, exist_ok=True)
    return path


def get_bm25_path(user_id: str, document_id: str) -> str:
    """Get the file path for a specific document's BM25 index."""
    return os.path.join(get_bm25_dir(user_id), f"{document_id}.json")


def tokenize(text: str) -> List[str]:
    """Tokenize by converting to lowercase and extracting all alphanumeric words."""
    return re.findall(r'\w+', text.lower())


def store_bm25_index(chunks: List[Dict[str, Any]], document_id: str, filename: str, user_id: str):
    """
    Build and store a BM25 index for the given document chunks.
    """
    if BM25Okapi is None:
        logger.warning("rank_bm25 is not installed; skipping BM25 index storage")
        return

    if not chunks:
        return

    texts = [chunk["text"] for chunk in chunks]
    tokenized_texts = [tokenize(text) for text in texts]
    bm25 = BM25Okapi(tokenized_texts)

    formatted_chunks = []
    for chunk in chunks:
        chunk_idx = chunk.get("chunk_index")
        chunk_id = f"{document_id}_{chunk_idx}" if chunk_idx is not None else None
        formatted_chunks.append({
            "id": chunk_id,
            "text": chunk["text"],
            "filename": filename,
            "document_id": document_id,
            "page": chunk.get("page", 1),
        })

    data = {
        "bm25": _bm25_to_dict(bm25),
        "chunks": formatted_chunks,
    }

    path = get_bm25_path(user_id, document_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        logger.info(f"Stored BM25 index for document {document_id}")
    except Exception as e:
        logger.error(f"Failed to store BM25 index for {document_id}: {e}")


def _query_single_index(path: str, tokenized_query: List[str], top_k: int) -> List[Dict[str, Any]]:
    """Query a single BM25 index file."""
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load BM25 index from {path}: {e}")
        return []

    bm25 = _dict_to_bm25(data["bm25"])
    chunks = data["chunks"]

    scores = bm25.get_scores(tokenized_query)

    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    results = []
    for i in top_indices:
        if scores[i] > 0:
            chunk = chunks[i].copy()
            chunk["score"] = float(scores[i])
            results.append(chunk)

    return results


def query_bm25(
    query: str,
    user_id: str,
    document_id: Optional[str] = None,
    document_ids: Optional[List[str]] = None,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Query BM25 index(es) for relevant chunks.
    """
    if BM25Okapi is None:
        return []

    tokenized_query = tokenize(query)

    if document_id:
        path = get_bm25_path(user_id, document_id)
        return _query_single_index(path, tokenized_query, top_k)

    if document_ids:
        all_results = []
        for doc_id in document_ids:
            path = get_bm25_path(user_id, doc_id)
            if os.path.exists(path):
                results = _query_single_index(path, tokenized_query, top_k)
                all_results.extend(results)
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:top_k]

    user_dir = get_bm25_dir(user_id)
    all_results = []

    for path in glob.glob(os.path.join(user_dir, "*.json")):
        results = _query_single_index(path, tokenized_query, top_k)
        all_results.extend(results)

    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:top_k]


def delete_bm25_index(document_id: str, user_id: str):
    """Delete a specific document's BM25 index."""
    path = get_bm25_path(user_id, document_id)
    if os.path.exists(path):
        try:
            os.remove(path)
            logger.info(f"Deleted BM25 index for document {document_id}")
        except Exception as e:
            logger.warning(f"Error deleting BM25 index: {e}")


def delete_user_bm25_indexes(user_id: str):
    """Delete all BM25 indexes for a user."""
    user_dir = get_bm25_dir(user_id)
    if os.path.exists(user_dir):
        try:
            for path in glob.glob(os.path.join(user_dir, "*.json")):
                os.remove(path)
            os.rmdir(user_dir)
            logger.info(f"Deleted BM25 directory for user {user_id}")
        except Exception as e:
            logger.warning(f"Error deleting BM25 directory for user {user_id}: {e}")

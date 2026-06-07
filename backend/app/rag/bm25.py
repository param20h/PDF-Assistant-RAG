"""
BM25 Keyword Search implementation using rank_bm25.
Stores a BM25 index per document to allow easy updates and deletions.
"""
import os
import glob
import pickle
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

def get_bm25_dir(user_id: str) -> str:
    """Get the directory path for a user's BM25 indexes."""
    clean_id = user_id.replace("-", "_")
    path = os.path.join(settings.CHROMA_PERSIST_DIR, "bm25", clean_id)
    os.makedirs(path, exist_ok=True)
    return path

def get_bm25_path(user_id: str, document_id: str) -> str:
    """Get the file path for a specific document's BM25 index."""
    return os.path.join(get_bm25_dir(user_id), f"{document_id}.pkl")

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

    # Format chunks to match vectorstore output
    formatted_chunks = []
    for chunk in chunks:
        formatted_chunks.append({
            "text": chunk["text"],
            "filename": filename,
            "document_id": document_id,
            "page": chunk.get("page", 1),
        })

    data = {
        "bm25": bm25,
        "chunks": formatted_chunks
    }

    path = get_bm25_path(user_id, document_id)
    try:
        with open(path, "wb") as f:
            pickle.dump(data, f)
        logger.info(f"Stored BM25 index for document {document_id}")
    except Exception as e:
        logger.error(f"Failed to store BM25 index for {document_id}: {e}")

def _query_single_index(path: str, tokenized_query: List[str], top_k: int) -> List[Dict[str, Any]]:
    """Query a single BM25 index file."""
    if not os.path.exists(path):
        return []

    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
    except Exception as e:
        logger.error(f"Failed to load BM25 index from {path}: {e}")
        return []

    bm25 = data["bm25"]
    chunks = data["chunks"]

    scores = bm25.get_scores(tokenized_query)
    
    # Get top_k indices sorted by score
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    results = []
    for i in top_indices:
        if scores[i] > 0:
            chunk = chunks[i].copy()
            # Normalize BM25 score to 0-1 range roughly, or just keep raw.
            # BM25 scores are usually > 0, often 1-10.
            # We keep the raw score for now, RRF will handle the ranking.
            chunk["score"] = float(scores[i])
            results.append(chunk)

    return results

def query_bm25(
    query: str,
    user_id: str,
    document_id: Optional[str] = None,
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
    
    # If no document_id, query all documents for this user
    user_dir = get_bm25_dir(user_id)
    all_results = []
    
    for path in glob.glob(os.path.join(user_dir, "*.pkl")):
        results = _query_single_index(path, tokenized_query, top_k)
        all_results.extend(results)
        
    # Sort all results by score and take top_k
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
            for path in glob.glob(os.path.join(user_dir, "*.pkl")):
                os.remove(path)
            os.rmdir(user_dir)
            logger.info(f"Deleted BM25 directory for user {user_id}")
        except Exception as e:
            logger.warning(f"Error deleting BM25 directory for user {user_id}: {e}")

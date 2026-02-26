import faiss
import numpy as np
import pickle
import os
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL, TOP_K

embedding_model = SentenceTransformer(EMBEDDING_MODEL)

def embed_query(query):
    return embedding_model.encode(query)

def retrieve_chunks(query, filename=None, meta_path=None):
    if meta_path is None or not os.path.exists(meta_path):
        return []

    index_path = os.path.join(os.path.dirname(meta_path), "index.faiss")

    if not os.path.exists(index_path):
        return []

    query_embedding = np.array([embed_query(query)]).astype("float32")

    index = faiss.read_index(index_path)

    with open(meta_path, "rb") as f:
        metadata = pickle.load(f)

    # ── Fix: search a larger pool to allow filtering by filename ──
    n_search = min(100, len(metadata))

    if n_search == 0:
        return []

    distances, indices = index.search(query_embedding, n_search)

    # ── Fix: check distances is not empty ──
    if len(distances) == 0 or len(distances[0]) == 0:
        return []

    max_distance = float(distances[0].max()) if distances[0].max() > 0 else 1

    chunks = []
    for i, idx in enumerate(indices[0]):
        # ── Fix: skip invalid indices ──
        if idx == -1 or idx >= len(metadata):
            continue

        if filename and metadata[idx]["filename"] != filename:
            continue

        raw_score = float(distances[0][i])
        confidence = round((1 - (raw_score / max_distance)) * 100, 2)

        chunks.append({
            "text": metadata[idx]["text"],
            "filename": metadata[idx]["filename"],
            "page": metadata[idx]["page"],
            "score": raw_score,
            "confidence": confidence
        })

        if len(chunks) == TOP_K:
            break

    # fallback: if no specific good match, and the user asks a very generic question 
    # and we have chunks for this file, just return the first chunk of the file
    if not chunks and filename:
        for idx in range(len(metadata)):
            if metadata[idx]["filename"] == filename:
                chunks.append({
                    "text": metadata[idx]["text"],
                    "filename": metadata[idx]["filename"],
                    "page": metadata[idx]["page"],
                    "score": 0.0,
                    "confidence": 0.0
                })
                break

    return chunks 
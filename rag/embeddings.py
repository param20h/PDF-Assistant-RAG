import faiss
import numpy as np
import pickle
import os
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL, CHROMA_DB_PATH

# ── Load Model ───────────────────────────────────────
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

INDEX_PATH = CHROMA_DB_PATH + "/index.faiss"

def embed_text(text):
    return embedding_model.encode(text)

# ── Updated to accept meta_path ──────────────────────
def store_embeddings(chunks, filename, meta_path):
    embeddings = []
    metadata = []

    for i, chunk in enumerate(chunks):
        emb = embed_text(chunk["text"])
        embeddings.append(emb)
        metadata.append({
            "text": chunk["text"],
            "filename": filename,
            "page": chunk["page"],
            "chunk_index": i
        })

    embeddings_np = np.array(embeddings).astype("float32")
    dimension = embeddings_np.shape[1]

    index_path = os.path.join(os.path.dirname(meta_path), "index.faiss")

    if os.path.exists(index_path):
        index = faiss.read_index(index_path)
        with open(meta_path, "rb") as f:
            existing_metadata = pickle.load(f)
    else:
        index = faiss.IndexFlatL2(dimension)
        existing_metadata = []

    index.add(embeddings_np)
    existing_metadata.extend(metadata)

    faiss.write_index(index, index_path)
    with open(meta_path, "wb") as f:
        pickle.dump(existing_metadata, f)
"""
HuggingFace local embeddings using sentence-transformers.
Loads the model once via singleton pattern for efficiency.
"""
import logging
from typing import List
from langchain_huggingface import HuggingFaceEmbeddings
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Singleton embedding model ────────────────────────
_embedding_model = None


def get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Get or create the embedding model (singleton).
    Uses sentence-transformers/all-MiniLM-L6-v2 — lightweight 384-dim model.
    """
    global _embedding_model

    if _embedding_model is None:
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        _embedding_model = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True, "batch_size": 32},
        )
        logger.info("Embedding model loaded successfully")

    return _embedding_model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a batch of texts into vectors."""
    model = get_embedding_model()
    return model.embed_documents(texts)


def embed_query(query: str) -> List[float]:
    """Embed a single query string."""
    model = get_embedding_model()
    return model.embed_query(query)

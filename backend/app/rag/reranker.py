"""
Cross-encoder reranker using BAAI/bge-reranker-v2-m3.
Loads the model once and provides a rerank method.
"""

import logging
from typing import List, Dict, Any, Optional

from sentence_transformers import CrossEncoder

from app.config import get_settings

logger = logging.getLogger(__name__)

# ── Reranker Class ─────────────────────────────────────
class Reranker:
    """Reranks documents using a cross-encoder model (BGE reranker)."""

    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        """
        Initialize the reranker model.

        Args:
            model_name: HuggingFace model ID (defaults to settings.RERANKER_MODEL).
            device: 'cpu', 'cuda', or None (auto-detect).
        """
        settings = get_settings()
        self.model_name = model_name or settings.RERANKER_MODEL
        self.device = device
        self._model: Optional[CrossEncoder] = None

    # Lazy-load the model when needed to avoid long startup times
    def _load_model(self) -> CrossEncoder:
        """Lazy-load the cross-encoder model."""
        if self._model is None:
            logger.info(f"Loading reranker: {self.model_name}")
            self._model = CrossEncoder(
                self.model_name,
                max_length=512,
                device=self.device
            )
            logger.info("Reranker loaded successfully")
        return self._model

    # Reranking method that takes a query and a list of documents, and returns them sorted by relevance
    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
        text_key: str = "text",
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents based on relevance to the query.

        Args:
            query: The user query.
            documents: List of document dicts (must contain text_key field).
            top_k: Number of top documents to return after reranking.
            text_key: Key in document dict that holds the text content.

        Returns:
            List of reranked documents (same dicts, but sorted by relevance).
        """
        if not documents:
            return []

        model = self._load_model()

        # Prepare query-document pairs
        pairs = [(query, doc[text_key]) for doc in documents]

        # Get relevance scores
        scores = model.predict(pairs)

        # Pair scores with documents and sort in descending order
        scored = list(zip(scores, documents))
        scored.sort(key=lambda x: x[0], reverse=True)

        # Return top_k documents
        reranked = [doc for _, doc in scored[:top_k]]

        # Attach rerank_score to each returned document
        for (score, doc) in scored:
            if doc in reranked:
                doc["rerank_score"] = float(score)

        return reranked


# Singleton instance for global reuse
_reranker_instance: Optional[Reranker] = None

# Function to get the global reranker instance
def get_reranker(model_name: Optional[str] = None) -> Reranker:
    """Get or create the global reranker instance."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = Reranker(model_name=model_name)
    return _reranker_instance
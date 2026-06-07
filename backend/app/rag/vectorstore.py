"""
ChromaDB vector store operations.
Per-user collections for data isolation.
"""
import logging
from typing import List, Dict, Any, Optional
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Singleton ChromaDB client ────────────────────────
_chroma_client = None


def get_chroma_client():
    """Get or create persistent ChromaDB client."""
    global _chroma_client

    if _chroma_client is None:
        import os
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"ChromaDB initialized at {settings.CHROMA_PERSIST_DIR}")

    return _chroma_client


def get_collection_name(user_id: str) -> str:
    """Generate a valid collection name for a user."""
    # ChromaDB collection names must be 3-63 chars, alphanumeric + underscores
    clean_id = user_id.replace("-", "_")
    name = f"user_{clean_id}"
    # Truncate if too long
    return name[:63]


def store_chunks(
    chunks: List[Dict[str, Any]],
    document_id: str,
    filename: str,
    user_id: str,
) -> int:
    """
    Embed and store document chunks in ChromaDB, and build a local BM25 index.
    Returns the number of chunks stored.
    """
    if not chunks:
        return 0

    # Delete existing chunks for this document and user before inserting new ones
    # to avoid stale/orphaned chunks in ChromaDB and BM25.
    delete_document_chunks(document_id, user_id)

    # Build and store BM25 index
    from app.rag.bm25 import store_bm25_index
    try:
        store_bm25_index(chunks, document_id, filename, user_id)
    except Exception as e:
        logger.error(f"Could not build BM25 index: {e}")

    # Generate captions for any extracted images before embedding
    try:
        from app.rag.vision import generate_captions_for_chunks

        generate_captions_for_chunks(chunks)
    except Exception as e:
        logger.warning(f"Could not generate image captions: {e}")

    client = get_chroma_client()
    from app.rag.embeddings import get_embedding_model

    embedding_model = get_embedding_model()

    collection_name = get_collection_name(user_id)
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    # ── Prepare batch data ───────────────────────────
    texts = [chunk["text"] for chunk in chunks]
    ids = [f"{document_id}_{chunk['chunk_index']}" for chunk in chunks]
    metadatas = [
        {
            "text": chunk["text"],
            "filename": filename,
            "document_id": document_id,
            "page": chunk["page"],
            "chunk_index": chunk["chunk_index"],
            "chunk_type": chunk.get("chunk_type", "text"),
            **({"bbox": chunk.get("bbox", "")} if chunk.get("bbox") else {}),
            **({"table_index": chunk.get("table_index", 0)} if chunk.get("chunk_type") == "table" else {}),
            # Indicate whether this chunk was originally an image and include a short caption
            **({"is_image": True, "image_caption": chunk.get("image_caption", "")}
               if chunk.get("is_image") else {}),
        }
        for chunk in chunks
    ]

    # ── Embed and upsert in batches ──────────────────
    batch_size = 50
    total_stored = 0

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch_ids = ids[i:i + batch_size]
        batch_metadatas = metadatas[i:i + batch_size]

        # Generate embeddings
        embeddings = embedding_model.embed_documents(batch_texts)

        collection.add(
            ids=batch_ids,
            embeddings=embeddings,
            metadatas=batch_metadatas,
            documents=batch_texts,
        )
        total_stored += len(batch_texts)

    logger.info(f"Stored {total_stored} chunks for document {document_id}")
    return total_stored


def query_chunks(
    query_embedding: List[float],
    user_id: str,
    document_id: Optional[str] = None,
    document_ids: Optional[List[str]] = None,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Query ChromaDB for relevant chunks.
    Returns list of dicts with text, metadata, and distance.
    """
    client = get_chroma_client()
    collection_name = get_collection_name(user_id)

    try:
        collection = client.get_collection(name=collection_name)
    except Exception:
        logger.warning(f"Collection {collection_name} not found")
        return []

    # ── Build filter ─────────────────────────────────
    where_filter = None
    if document_id:
        where_filter = {"document_id": {"$eq": document_id}}
    elif document_ids:
        where_filter = {"document_id": {"$in": document_ids}}

    # ── Query ────────────────────────────────────────
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    # ── Format results ───────────────────────────────
    chunks = []
    if results and results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 0

            # Convert cosine distance to similarity score (0-1)
            similarity = 1 - distance

            chunks.append({
                "text": doc,
                "filename": metadata.get("filename", ""),
                "document_id": metadata.get("document_id", ""),
                "page": metadata.get("page", 1),
                "chunk_type": metadata.get("chunk_type", "text"),
                "bbox": metadata.get("bbox", ""),
                "score": round(similarity, 4),
            })

    return chunks


def delete_document_chunks(document_id: str, user_id: str):
    """Delete all chunks for a specific document."""
    client = get_chroma_client()
    collection_name = get_collection_name(user_id)

    try:
        from app.rag.bm25 import delete_bm25_index
        delete_bm25_index(document_id, user_id)
    except Exception as e:
        logger.warning(f"Error deleting BM25 index: {e}")

    try:
        collection = client.get_collection(name=collection_name)
        # Get all IDs for this document
        results = collection.get(
            where={"document_id": {"$eq": document_id}},
            include=[],
        )
        if results["ids"]:
            collection.delete(ids=results["ids"])
            logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
    except Exception as e:
        logger.warning(f"Error deleting chunks: {e}")


def delete_user_collection(user_id: str):
    """Delete entire collection for a user."""
    client = get_chroma_client()
    collection_name = get_collection_name(user_id)

    try:
        from app.rag.bm25 import delete_user_bm25_indexes
        delete_user_bm25_indexes(user_id)
    except Exception as e:
        logger.warning(f"Error deleting user BM25 indexes: {e}")

    try:
        client.delete_collection(name=collection_name)
        logger.info(f"Deleted collection {collection_name}")
    except Exception as e:
        logger.warning(f"Error deleting collection: {e}")

import sys
from unittest.mock import MagicMock


def test_store_chunks_deletes_old_chunks(monkeypatch):
    """
    Test that store_chunks cleans up old chunks for the specific document and user
    before embedding and saving the new chunks.
    """
    # Keep track of fake module from sys.modules
    fake_module = sys.modules.get("app.rag.vectorstore")

    # Temporarily remove fake_module to import the real module
    if fake_module:
        del sys.modules["app.rag.vectorstore"]

    try:
        # Import the real module
        import app.rag.vectorstore as real_vectorstore

        # Mock the ChromaDB client and collection
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client.get_collection.return_value = mock_collection

        # Simulate existing chunks in ChromaDB
        mock_collection.get.return_value = {"ids": ["doc_123_0", "doc_123_1"]}

        monkeypatch.setattr(real_vectorstore, "get_chroma_client", lambda: mock_client)

        # Mock embedding model on the app.rag.embeddings module directly
        import app.rag.embeddings as embeddings_module
        mock_embeddings = MagicMock()
        mock_embeddings.embed_documents.return_value = [[0.1] * 384]
        monkeypatch.setattr(
            embeddings_module,
            "get_embedding_model",
            lambda: mock_embeddings,
        )

        # Mock BM25 actions to avoid I/O or extra imports
        monkeypatch.setattr("app.rag.bm25.store_bm25_index", lambda *args, **kwargs: None)
        monkeypatch.setattr("app.rag.bm25.delete_bm25_index", lambda *args, **kwargs: None)

        # Execute store_chunks
        chunks = [{"text": "Hello world", "page": 1, "chunk_index": 0}]
        real_vectorstore.store_chunks(
            chunks=chunks,
            document_id="doc_123",
            filename="test.pdf",
            user_id="user_123",
        )

        # Assertions
        # 1. It should check for existing chunks using correct metadata filters
        mock_collection.get.assert_called_once_with(
            where={"document_id": {"$eq": "doc_123"}},
            include=[],
        )
        # 2. It should delete those chunks by ID
        mock_collection.delete.assert_called_once_with(ids=["doc_123_0", "doc_123_1"])
        # 3. It should add the new chunks to the collection
        mock_collection.add.assert_called_once()

    finally:
        # Restore the fake module
        if fake_module:
            sys.modules["app.rag.vectorstore"] = fake_module

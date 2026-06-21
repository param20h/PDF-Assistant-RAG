import pytest
import os
from app.rag import bm25

def test_tokenize():
    # Test that punctuation is stripped and tokens are lowercased
    text = "This is a document."
    assert bm25.tokenize(text) == ["this", "is", "a", "document"]

    text_qwen = "The model used is Qwen."
    assert bm25.tokenize(text_qwen) == ["the", "model", "used", "is", "qwen"]

    text_mixed = "BM25 keyword-search module, testing!"
    assert bm25.tokenize(text_mixed) == ["bm25", "keyword", "search", "module", "testing"]

def test_store_and_query_bm25(tmp_path, monkeypatch):
    # Mock settings.CHROMA_PERSIST_DIR to use the temp path
    monkeypatch.setattr(bm25.settings, "CHROMA_PERSIST_DIR", str(tmp_path))

    user_id = "test-user-123"
    doc_id = "test-doc-abc"
    chunks = [
        {"text": "The model used is Qwen.", "page": 1},
        {"text": "BM25 retrieval performs keyword search.", "page": 2},
        {"text": "This is a completely unrelated third document chunk.", "page": 3},
    ]

    # Store index
    bm25.store_bm25_index(chunks, doc_id, "test.pdf", user_id)

    # Check that the index file was created
    expected_path = bm25.get_bm25_path(user_id, doc_id)
    assert os.path.exists(expected_path)

    # Query with exact word (originally failed because of punctuation)
    # The first chunk has "Qwen." (with period), query is "qwen"
    results = bm25.query_bm25("qwen", user_id, doc_id, top_k=1)
    assert len(results) == 1
    assert "Qwen" in results[0]["text"]
    assert results[0]["page"] == 1

    # Query all indexes for user
    results_all = bm25.query_bm25("keyword", user_id, top_k=2)
    assert len(results_all) == 1
    assert "BM25 retrieval" in results_all[0]["text"]
    assert results_all[0]["page"] == 2

    # Delete index
    bm25.delete_bm25_index(doc_id, user_id)
    assert not os.path.exists(expected_path)

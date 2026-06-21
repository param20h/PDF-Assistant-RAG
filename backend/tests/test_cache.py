"""
Unit tests for the response caching utility (Issue #45, #640).
Run with: pytest backend/tests/test_cache.py -v
"""

import pytest
import app.cache as cache_module


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear all cache state before each test so tests are independent."""
    cache_module._lru_store.clear()
    cache_module._lru_order.clear()
    cache_module._redis_available = False
    cache_module._redis_client = None
    yield


def test_cache_miss_returns_none():
    result = cache_module.get_cached_response("user1", "doc123", "What is this about?")
    assert result is None


def test_set_and_get_roundtrip():
    cache_module.set_cached_response("user1", "doc123", "What is this?", "It is a test.")
    result = cache_module.get_cached_response("user1", "doc123", "What is this?")
    assert result == "It is a test."


def test_different_documents_do_not_collide():
    cache_module.set_cached_response("user1", "doc_A", "Same question?", "Answer A")
    cache_module.set_cached_response("user1", "doc_B", "Same question?", "Answer B")
    assert cache_module.get_cached_response("user1", "doc_A", "Same question?") == "Answer A"
    assert cache_module.get_cached_response("user1", "doc_B", "Same question?") == "Answer B"


def test_question_normalised_to_lowercase():
    """Cache should match regardless of question casing."""
    cache_module.set_cached_response("user1", "doc1", "What is AI?", "AI is artificial intelligence.")
    result = cache_module.get_cached_response("user1", "doc1", "WHAT IS AI?")
    assert result == "AI is artificial intelligence."


def test_invalidate_removes_entry():
    cache_module.set_cached_response("user1", "doc1", "Hello?", "Hi!")
    cache_module.invalidate_cache("user1", "doc1", "Hello?")
    assert cache_module.get_cached_response("user1", "doc1", "Hello?") is None


def test_lru_eviction_removes_oldest():
    """When LRU reaches max size, the oldest entry is evicted."""
    cache_module.LRU_MAX_SIZE = 3
    cache_module.set_cached_response("user1", "doc", "Q1", "A1")
    cache_module.set_cached_response("user1", "doc", "Q2", "A2")
    cache_module.set_cached_response("user1", "doc", "Q3", "A3")
    cache_module.set_cached_response("user1", "doc", "Q4", "A4")  # should evict Q1
    assert cache_module.get_cached_response("user1", "doc", "Q1") is None
    assert cache_module.get_cached_response("user1", "doc", "Q4") == "A4"


def test_make_cache_key_is_deterministic():
    k1 = cache_module.make_cache_key("user1", "doc1", "What is this?")
    k2 = cache_module.make_cache_key("user1", "doc1", "What is this?")
    assert k1 == k2


def test_make_cache_key_differs_by_document():
    k1 = cache_module.make_cache_key("user1", "doc1", "Same question")
    k2 = cache_module.make_cache_key("user1", "doc2", "Same question")
    assert k1 != k2


def test_make_cache_key_is_64_chars():
    """SHA-256 hex digest is always exactly 64 characters."""
    key = cache_module.make_cache_key("user1", "any_doc", "any question")
    assert len(key) == 64


# ── Cross-user isolation ────────────────────────────────────────────
# make_cache_key omitted user_id entirely, so two different users asking the
# identical question with no document_id (cross-document RAG over their own
# private knowledge base) collapsed onto the same cache entry — meaning the
# second user's request returned the first user's privately-generated answer.

def test_make_cache_key_differs_by_user():
    """Same document + question, different users, must produce different keys."""
    k1 = cache_module.make_cache_key("user-a", "doc1", "Summarize the key points")
    k2 = cache_module.make_cache_key("user-b", "doc1", "Summarize the key points")
    assert k1 != k2


def test_make_cache_key_differs_by_user_with_no_document():
    """The empty-document_id case from ask_question's `str(payload.document_id or "")`
    is exactly where the original bug collapsed two different users onto one key."""
    k1 = cache_module.make_cache_key("user-a", "", "What does this say about pricing?")
    k2 = cache_module.make_cache_key("user-b", "", "What does this say about pricing?")
    assert k1 != k2


def test_documentless_query_cache_is_isolated_per_user():
    """Regression test for #640: one user's cached document-less RAG answer
    must never be served back to a different user asking the same question."""
    cache_module.set_cached_response("user-a", "", "summarize the key points", "User A's private summary")

    # A different user asking the identical normalized question text must miss.
    assert cache_module.get_cached_response("user-b", "", "summarize the key points") is None

    # The original user still gets their own cached answer back.
    assert cache_module.get_cached_response("user-a", "", "summarize the key points") == "User A's private summary"
"""
Unit tests for the response caching utility (Issue #45).
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
    result = cache_module.get_cached_response("doc123", "What is this about?")
    assert result is None


def test_set_and_get_roundtrip():
    cache_module.set_cached_response("doc123", "What is this?", "It is a test.")
    result = cache_module.get_cached_response("doc123", "What is this?")
    assert result == "It is a test."


def test_different_documents_do_not_collide():
    cache_module.set_cached_response("doc_A", "Same question?", "Answer A")
    cache_module.set_cached_response("doc_B", "Same question?", "Answer B")
    assert cache_module.get_cached_response("doc_A", "Same question?") == "Answer A"
    assert cache_module.get_cached_response("doc_B", "Same question?") == "Answer B"


def test_question_normalised_to_lowercase():
    """Cache should match regardless of question casing."""
    cache_module.set_cached_response("doc1", "What is AI?", "AI is artificial intelligence.")
    result = cache_module.get_cached_response("doc1", "WHAT IS AI?")
    assert result == "AI is artificial intelligence."


def test_invalidate_removes_entry():
    cache_module.set_cached_response("doc1", "Hello?", "Hi!")
    cache_module.invalidate_cache("doc1", "Hello?")
    assert cache_module.get_cached_response("doc1", "Hello?") is None


def test_lru_eviction_removes_oldest():
    """When LRU reaches max size, the oldest entry is evicted."""
    cache_module.LRU_MAX_SIZE = 3
    cache_module.set_cached_response("doc", "Q1", "A1")
    cache_module.set_cached_response("doc", "Q2", "A2")
    cache_module.set_cached_response("doc", "Q3", "A3")
    cache_module.set_cached_response("doc", "Q4", "A4")  # should evict Q1
    assert cache_module.get_cached_response("doc", "Q1") is None
    assert cache_module.get_cached_response("doc", "Q4") == "A4"


def test_make_cache_key_is_deterministic():
    k1 = cache_module.make_cache_key("doc1", "What is this?")
    k2 = cache_module.make_cache_key("doc1", "What is this?")
    assert k1 == k2


def test_make_cache_key_differs_by_document():
    k1 = cache_module.make_cache_key("doc1", "Same question")
    k2 = cache_module.make_cache_key("doc2", "Same question")
    assert k1 != k2


def test_make_cache_key_is_64_chars():
    """SHA-256 hex digest is always exactly 64 characters."""
    key = cache_module.make_cache_key("any_doc", "any question")
    assert len(key) == 64

"""Regression tests for the process_document Celery task.

These guard against the task body becoming a no-op stub again (see issue
#635): process_document must actually drive the real ingestion pipeline in
app.services.document_ingestion, not just flip the document's status to
"ready" without storing any chunks/vectors.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.models import Document
from app.tasks import process_document


def _make_pending_document(db_session, doc_id="test-doc-123", user_id="user-456"):
    test_doc = Document(
        id=doc_id,
        filename="sample.pdf",
        original_name="sample.pdf",
        status="pending",
        user_id=user_id,
    )
    db_session.add(test_doc)
    db_session.commit()
    return test_doc


@pytest.fixture()
def patched_session_factory(db_session, monkeypatch):
    """Route both app.tasks (get_db_session) and document_ingestion
    (SessionLocal) onto the same test db_session, so the task and the
    pipeline it dispatches into observe a single consistent view of the row.
    """
    from contextlib import contextmanager

    @contextmanager
    def _fake_get_db_session():
        yield db_session

    monkeypatch.setattr("app.tasks.get_db_session", _fake_get_db_session)
    monkeypatch.setattr("app.database.SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    return db_session


def test_process_document_runs_real_ingestion_pipeline(patched_session_factory):
    """process_document must delegate into ingest_document and persist real
    chunk/vector results - not silently no-op and mark the doc 'ready' with
    zero chunks (the bug in #635).
    """
    db_session = patched_session_factory
    _make_pending_document(db_session)

    fake_chunks = [
        {"text": "first chunk", "page": 1, "type": "text"},
        {"text": "second chunk", "page": 1, "type": "text"},
        {"text": "third chunk", "page": 2, "type": "text"},
    ]

    with patch("app.services.document_ingestion.get_page_count", return_value=2), \
         patch("app.services.document_ingestion.chunk_document", return_value=fake_chunks), \
         patch("app.services.document_ingestion.store_chunks", return_value=len(fake_chunks)) as mock_store, \
         patch("app.services.document_ingestion.persist_document_keywords"):

        task_result = process_document.apply(
            kwargs={
                "document_id": "test-doc-123",
                "filepath": "/tmp/sample.pdf",
                "original_name": "sample.pdf",
                "user_id": "user-456",
            }
        )

    assert task_result.status == "SUCCESS"
    assert task_result.result == {"document_id": "test-doc-123", "status": "ready"}

    mock_store.assert_called_once()
    call_kwargs = mock_store.call_args.kwargs
    assert call_kwargs["chunks"] == fake_chunks
    assert call_kwargs["document_id"] == "test-doc-123"

    updated_doc = db_session.query(Document).filter_by(id="test-doc-123").first()
    assert updated_doc is not None
    assert updated_doc.status == "ready"
    assert updated_doc.chunk_count == 3
    assert updated_doc.page_count == 2
    assert updated_doc.retry_count == 1


def test_process_document_marks_failed_when_no_text_extracted(patched_session_factory):
    """If ingestion legitimately fails (e.g. no extractable text),
    process_document must surface that as a failed task/status rather than
    reporting 'ready' regardless of pipeline outcome.
    """
    db_session = patched_session_factory
    _make_pending_document(db_session, doc_id="test-doc-empty")

    with patch("app.services.document_ingestion.get_page_count", return_value=1), \
         patch("app.services.document_ingestion.chunk_document", return_value=[]):

        task_result = process_document.apply(
            kwargs={
                "document_id": "test-doc-empty",
                "filepath": "/tmp/empty.pdf",
                "original_name": "empty.pdf",
                "user_id": "user-456",
            }
        )

    assert task_result.status == "FAILURE"

    updated_doc = db_session.query(Document).filter_by(id="test-doc-empty").first()
    assert updated_doc is not None
    assert updated_doc.status == "failed"
    assert updated_doc.chunk_count == 0
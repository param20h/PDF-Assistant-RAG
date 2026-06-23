"""Regression tests for re-chunking a document while it is
still processing must not queue a second concurrent ingestion run.

update_chunk_settings previously reset doc.status to "pending" and
re-queued process_document.delay(...) unconditionally, with no check on
the document's current status. If a prior ingestion run for the same
document_id was still "processing", this let two ingestion runs execute
concurrently against the same document - and since store_chunks() in
vectorstore.py performs a non-atomic delete-then-batch-insert sequence,
the two runs could interleave and corrupt the vector store relative to
whatever chunk_count ends up persisted in Postgres.
"""
from app.models import Document


def test_update_chunk_settings_rejects_while_document_processing(
    client, auth_headers, db_session, user, monkeypatch
):
    """A document mid-ingestion must reject a re-chunk request with 409,
    not silently reset its status and re-queue a second concurrent run.
    """
    document = Document(
        user_id=user.id,
        filename="processing.pdf",
        original_name="processing.pdf",
        file_size=256,
        status="processing",
        chunk_count=0,
        page_count=0,
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    def _delay_should_not_be_called(*args, **kwargs):
        raise AssertionError(
            "process_document.delay was called for a document still "
            "processing - the concurrency guard did not reject the request"
        )

    monkeypatch.setattr(
        "app.routes.documents.process_document.delay",
        _delay_should_not_be_called,
    )

    response = client.post(
        f"/api/v1/documents/{document.id}/chunk_settings",
        json={"chunk_size": 500, "chunk_overlap": 50},
        headers=auth_headers,
    )

    assert response.status_code == 409

    refreshed = db_session.get(Document, document.id)
    assert refreshed.status == "processing"
    assert refreshed.chunk_count == 0
    assert refreshed.page_count == 0


def test_update_chunk_settings_allows_when_not_processing(
    client, auth_headers, ready_document, db_session, monkeypatch
):
    """A document that is "ready" (i.e. not mid-ingestion) must still be
    allowed to re-chunk - the guard should only block "processing".
    """
    queued = {}

    class _FakeTask:
        id = "fake-task-id"

    def _fake_delay(**kwargs):
        queued.update(kwargs)
        return _FakeTask()

    monkeypatch.setattr("app.routes.documents.process_document.delay", _fake_delay)

    response = client.post(
        f"/api/v1/documents/{ready_document.id}/chunk_settings",
        json={"chunk_size": 500, "chunk_overlap": 50},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert queued["document_id"] == ready_document.id

    refreshed = db_session.get(Document, ready_document.id)
    assert refreshed.status == "pending"
    assert refreshed.chunk_size == 500
    assert refreshed.chunk_overlap == 50
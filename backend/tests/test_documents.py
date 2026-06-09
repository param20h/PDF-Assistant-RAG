import pytest
import types

from app.models import Document
from app.services.document_ingestion import ingest_document


def test_api_health(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["version"] == "2.0.0"


def test_protected_documents_list_requires_auth(client):
    response = client.get("/api/v1/documents/")

    assert response.status_code in (401, 403)


def test_documents_list_authenticated(client, auth_headers, ready_document):
    response = client.get("/api/v1/documents/", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == ready_document.id
    assert payload["items"][0]["original_name"] == "ready.txt"


def test_upload_rejects_unsupported_extension_before_deep_validation(client, auth_headers):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("payload.exe", b"binary-data", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "not supported" in response.json()["error"]["message"]


def test_rename_document_updates_original_name(client, auth_headers, ready_document, db_session):
    response = client.patch(
        f"/api/v1/documents/{ready_document.id}",
        headers=auth_headers,
        json={"name": " renamed-report.pdf "},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == ready_document.id
    assert payload["original_name"] == "renamed-report.pdf"

    db_session.refresh(ready_document)
    assert ready_document.original_name == "renamed-report.pdf"
    assert ready_document.filename == "ready.txt"


def test_rename_document_rejects_empty_name(client, auth_headers, ready_document):
    response = client.patch(
        f"/api/v1/documents/{ready_document.id}",
        headers=auth_headers,
        json={"name": "   "},
    )

    assert response.status_code == 422


def test_rename_document_returns_404_for_missing_document(client, auth_headers):
    response = client.patch(
        "/api/v1/documents/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
        json={"name": "missing.pdf"},
    )

    assert response.status_code == 404


def test_rename_document_returns_403_for_other_users_document(client, auth_headers, db_session, other_user):
    other_document = Document(
        user_id=other_user.id,
        filename="other.txt",
        original_name="other.txt",
        file_size=64,
        status="ready",
    )
    db_session.add(other_document)
    db_session.commit()
    db_session.refresh(other_document)

    response = client.patch(
        f"/api/v1/documents/{other_document.id}",
        headers=auth_headers,
        json={"name": "renamed.txt"},
    )

    assert response.status_code == 403
    db_session.refresh(other_document)
    assert other_document.original_name == "other.txt"


def test_ingest_document_builds_and_saves_graph(db_session, monkeypatch, tmp_path, user):
    document = Document(
        user_id=user.id,
        filename="graph.txt",
        original_name="graph.txt",
        file_size=128,
        status="pending",
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    user_id = user.id
    document_id = document.id
    chunks = [{"text": "OpenAI works with Microsoft.", "page": 1, "chunk_index": 0}]
    saved = {}

    monkeypatch.setattr("app.services.document_ingestion.get_page_count", lambda filepath: 1)
    monkeypatch.setattr("app.services.document_ingestion.chunk_document", lambda filepath: chunks)
    monkeypatch.setattr("app.services.document_ingestion.store_chunks", lambda **kwargs: len(chunks))
    monkeypatch.setattr("app.database.SessionLocal", lambda: db_session)

    fake_summary = types.ModuleType("app.rag.summarizer")
    fake_summary.generate_document_summary = lambda filepath, max_sentences=2: "Summary"
    monkeypatch.setitem(__import__("sys").modules, "app.rag.summarizer", fake_summary)

    monkeypatch.setattr(
        "app.rag.graph_builder.build_graph",
        lambda received_chunks: {"chunks": received_chunks},
    )
    monkeypatch.setattr(
        "app.rag.graph_builder.save_graph",
        lambda graph, user_id, document_id: saved.update(
            {"graph": graph, "user_id": user_id, "document_id": document_id}
        ),
    )

    ingest_document(
        document_id=document_id,
        filepath=str(tmp_path / "graph.txt"),
        original_name=document.original_name,
        user_id=user_id,
    )

    assert saved == {
        "graph": {"chunks": chunks},
        "user_id": user_id,
        "document_id": document_id,
    }
    refreshed = db_session.get(Document, document_id)
    assert refreshed.status == "ready"
    assert refreshed.chunk_count == 1


def test_delete_document_soft_deletes_and_hides_document(client, auth_headers, ready_document, db_session, monkeypatch):
    deletion_calls = []
    doc_id = ready_document.id

    monkeypatch.setattr(
        "app.rag.graph_builder.delete_graph",
        lambda user_id, document_id: deletion_calls.append(
            {"user_id": user_id, "document_id": document_id}
        ),
    )

    response = client.delete(
        f"/api/v1/documents/{doc_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert deletion_calls == []

    db_session.refresh(ready_document)
    assert ready_document.is_deleted is True
    assert ready_document.deleted_at is not None

    list_response = client.get("/api/v1/documents/", headers=auth_headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 0

    get_response = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert get_response.status_code == 404


def test_list_trash_documents(client, auth_headers, ready_document, db_session):
    # Set document as soft-deleted
    from datetime import datetime, timezone
    ready_document.is_deleted = True
    ready_document.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    # Get trash
    response = client.get("/api/v1/documents/trash", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == ready_document.id
    assert payload[0]["original_name"] == "ready.txt"


def test_restore_document(client, auth_headers, ready_document, db_session):
    from datetime import datetime, timezone
    ready_document.is_deleted = True
    ready_document.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    # Verify not in active list
    list_response = client.get("/api/v1/documents/", headers=auth_headers)
    assert list_response.json()["total"] == 0

    # Restore
    response = client.post(f"/api/v1/documents/{ready_document.id}/restore", headers=auth_headers)
    assert response.status_code == 200

    db_session.refresh(ready_document)
    assert ready_document.is_deleted is False
    assert ready_document.deleted_at is None

    # Verify back in active list
    list_response = client.get("/api/v1/documents/", headers=auth_headers)
    assert list_response.json()["total"] == 1


def test_purge_document(client, auth_headers, ready_document, db_session, monkeypatch):
    from app.rag import vectorstore
    import app.routes.documents
    import os

    chunk_deleted = []
    graph_deleted = []
    file_deleted = []

    monkeypatch.setattr(
        vectorstore,
        "delete_document_chunks",
        lambda document_id, user_id: chunk_deleted.append(document_id)
    )
    monkeypatch.setattr(
        app.routes.documents,
        "delete_graph",
        lambda user_id, document_id: graph_deleted.append(document_id)
    )
    monkeypatch.setattr(
        os.path,
        "exists",
        lambda path: True
    )
    monkeypatch.setattr(
        os,
        "remove",
        lambda path: file_deleted.append(path)
    )

    doc_id = ready_document.id

    # Purge document
    response = client.delete(f"/api/v1/documents/{doc_id}/purge", headers=auth_headers)
    assert response.status_code == 200

    # Verify mocks were called
    assert doc_id in chunk_deleted
    assert doc_id in graph_deleted
    assert len(file_deleted) == 1

    # Verify DB record is gone
    refreshed = db_session.get(Document, doc_id)
    assert refreshed is None


def test_cleanup_old_deleted_documents_purges_graph(db_session, user, monkeypatch):
    from app.models import Document
    from app.services.cleanup import cleanup_old_deleted_documents
    from datetime import datetime, timedelta, timezone
    from app.rag import vectorstore, graph_builder
    import os

    # Create document soft-deleted more than 30 days ago
    from app.config import get_settings
    settings = get_settings()
    max_age_days = settings.DOC_CLEANUP_MAX_AGE_DAYS
    deleted_time = datetime.now(timezone.utc) - timedelta(days=max_age_days + 1)

    doc = Document(
        id="cleanup-test-doc-id",
        user_id=user.id,
        filename="cleanup_test.pdf",
        original_name="cleanup_test.pdf",
        is_deleted=True,
        deleted_at=deleted_time,
    )
    db_session.add(doc)
    db_session.commit()

    chunk_deleted = []
    graph_deleted = []
    file_deleted = []

    monkeypatch.setattr("app.database.SessionLocal", lambda: db_session)
    # Mock database session factory in cleanup
    class MockDbSessionContext:
        def __init__(self, session):
            self.session = session
        def __enter__(self):
            return self.session
        def __exit__(self, exc_type, exc_val, exc_tb):
            if not exc_type:
                self.session.commit()
    monkeypatch.setattr("app.services.cleanup.get_db_session", lambda: MockDbSessionContext(db_session))

    monkeypatch.setattr(
        vectorstore,
        "delete_document_chunks",
        lambda document_id, user_id: chunk_deleted.append(document_id)
    )
    monkeypatch.setattr(
        graph_builder,
        "delete_graph",
        lambda user_id, document_id: graph_deleted.append(document_id)
    )
    monkeypatch.setattr(
        os.path,
        "exists",
        lambda path: True
    )
    monkeypatch.setattr(
        os,
        "remove",
        lambda path: file_deleted.append(path)
    )

    cleanup_old_deleted_documents()

    assert "cleanup-test-doc-id" in chunk_deleted
    assert "cleanup-test-doc-id" in graph_deleted
    assert len(file_deleted) == 1

    # Verify db record is gone
    refreshed = db_session.get(Document, "cleanup-test-doc-id")
    assert refreshed is None


@pytest.mark.anyio
async def test_document_cleanup_job_purges_graph(db_session, user, monkeypatch):
    from app.models import Document
    from app.main import document_cleanup_job
    from datetime import datetime, timedelta, timezone
    from app.rag import vectorstore, graph_builder
    import os

    # Create document inactive for more than 30 days
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=31)

    doc = Document(
        id="inactive-test-doc-id",
        user_id=user.id,
        filename="inactive_test.pdf",
        original_name="inactive_test.pdf",
        is_deleted=False,
        last_accessed_at=cutoff_time,
        uploaded_at=cutoff_time,
    )
    db_session.add(doc)
    db_session.commit()

    chunk_deleted = []
    graph_deleted = []
    file_deleted = []

    monkeypatch.setattr("app.database.SessionLocal", lambda: db_session)
    
    # Mock asyncio.sleep to raise exception to break infinite loop
    import asyncio
    async def fake_sleep(seconds):
        raise asyncio.CancelledError()
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    monkeypatch.setattr(
        vectorstore,
        "delete_document_chunks",
        lambda document_id, user_id: chunk_deleted.append(document_id)
    )
    monkeypatch.setattr(
        graph_builder,
        "delete_graph",
        lambda user_id, document_id: graph_deleted.append(document_id)
    )
    monkeypatch.setattr(
        os.path,
        "exists",
        lambda path: True
    )
    monkeypatch.setattr(
        os,
        "remove",
        lambda path: file_deleted.append(path)
    )

    try:
        await document_cleanup_job()
    except asyncio.CancelledError:
        pass

    assert "inactive-test-doc-id" in chunk_deleted
    assert "inactive-test-doc-id" in graph_deleted
    assert len(file_deleted) == 1

    # Verify db record is gone
    refreshed = db_session.get(Document, "inactive-test-doc-id")
    assert refreshed is None





import types

from app.models import Document
from app.routes.documents import _ingest_document


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
    assert "not supported" in response.json()["detail"]


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

    monkeypatch.setattr("app.routes.documents.get_page_count", lambda filepath: 1)
    monkeypatch.setattr("app.routes.documents.chunk_document", lambda filepath: chunks)
    monkeypatch.setattr("app.routes.documents.store_chunks", lambda **kwargs: len(chunks))
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

    _ingest_document(
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

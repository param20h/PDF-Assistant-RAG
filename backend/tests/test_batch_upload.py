"""
Tests for POST /api/v1/documents/upload/batch — issue #435.
"""
import io
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models import Document


# ── helpers ──────────────────────────────────────────────────────────────────

def _fake_txt_file(name: str = "test.txt", content: bytes = b"hello world") -> tuple:
    """Return a multipart files tuple accepted by httpx TestClient."""
    return ("files", (name, io.BytesIO(content), "text/plain"))


def _patch_validate(monkeypatch, tmp_path, content: bytes = b"hello world") -> None:
    """Make validate_upload write content to a real temp file and return its path."""
    import tempfile, shutil

    async def fake_validate(file):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", dir=tmp_path)
        tmp.write(content)
        tmp.close()
        return tmp.name

    monkeypatch.setattr("app.routes.documents.validate_upload", fake_validate)


def _patch_celery(monkeypatch) -> MagicMock:
    """Stub out Celery so tests never touch Redis."""
    mock_task = MagicMock()
    mock_task.id = f"celery-{uuid.uuid4().hex}"
    monkeypatch.setattr(
        "app.routes.documents.process_document",
        MagicMock(delay=MagicMock(return_value=mock_task)),
    )
    return mock_task


# ── tests ─────────────────────────────────────────────────────────────────────

def test_batch_upload_single_file(client, auth_headers, monkeypatch, tmp_path):
    _patch_validate(monkeypatch, tmp_path)
    _patch_celery(monkeypatch)

    response = client.post(
        "/api/v1/documents/upload/batch",
        headers=auth_headers,
        files=[_fake_txt_file("report.txt")],
        data={"chunk_size": "1000", "chunk_overlap": "200"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["documents"]) == 1
    assert payload["documents"][0]["original_name"] == "report.txt"
    assert payload["documents"][0]["status"] == "pending"
    assert len(payload["task_ids"]) == 1
    assert payload["failed"] == []


def test_batch_upload_multiple_files(client, auth_headers, monkeypatch, tmp_path):
    _patch_validate(monkeypatch, tmp_path)
    _patch_celery(monkeypatch)

    response = client.post(
        "/api/v1/documents/upload/batch",
        headers=auth_headers,
        files=[
            _fake_txt_file("a.txt"),
            _fake_txt_file("b.txt"),
            _fake_txt_file("c.txt"),
        ],
        data={"chunk_size": "1000", "chunk_overlap": "200"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["total"] == 3
    assert len(payload["documents"]) == 3
    assert len(payload["task_ids"]) == 3
    assert payload["failed"] == []


def test_batch_upload_rejects_bad_extension(client, auth_headers, monkeypatch, tmp_path):
    """A .exe file should land in failed[], not crash the whole batch."""
    _patch_validate(monkeypatch, tmp_path)
    _patch_celery(monkeypatch)

    response = client.post(
        "/api/v1/documents/upload/batch",
        headers=auth_headers,
        files=[
            _fake_txt_file("good.txt"),
            ("files", ("bad.exe", io.BytesIO(b"binary"), "application/octet-stream")),
        ],
        data={"chunk_size": "1000", "chunk_overlap": "200"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["total"] == 1
    assert payload["documents"][0]["original_name"] == "good.txt"
    assert "bad.exe" in payload["failed"]


def test_batch_upload_all_files_fail_returns_400(client, auth_headers, monkeypatch, tmp_path):
    """When every file fails, the endpoint should return 400."""
    _patch_validate(monkeypatch, tmp_path)
    _patch_celery(monkeypatch)

    response = client.post(
        "/api/v1/documents/upload/batch",
        headers=auth_headers,
        files=[
            ("files", ("bad1.exe", io.BytesIO(b"x"), "application/octet-stream")),
            ("files", ("bad2.exe", io.BytesIO(b"y"), "application/octet-stream")),
        ],
        data={"chunk_size": "1000", "chunk_overlap": "200"},
    )

    assert response.status_code == 400


def test_batch_upload_requires_auth(client):
    response = client.post(
        "/api/v1/documents/upload/batch",
        files=[_fake_txt_file("test.txt")],
        data={"chunk_size": "1000", "chunk_overlap": "200"},
    )

    assert response.status_code in (401, 403)


def test_batch_upload_invalid_chunk_size(client, auth_headers, monkeypatch, tmp_path):
    _patch_validate(monkeypatch, tmp_path)
    _patch_celery(monkeypatch)

    response = client.post(
        "/api/v1/documents/upload/batch",
        headers=auth_headers,
        files=[_fake_txt_file("test.txt")],
        data={"chunk_size": "50", "chunk_overlap": "10"},
    )

    assert response.status_code == 400


def test_batch_upload_invalid_chunk_overlap(client, auth_headers, monkeypatch, tmp_path):
    _patch_validate(monkeypatch, tmp_path)
    _patch_celery(monkeypatch)

    response = client.post(
        "/api/v1/documents/upload/batch",
        headers=auth_headers,
        files=[_fake_txt_file("test.txt")],
        data={"chunk_size": "500", "chunk_overlap": "600"},
    )

    assert response.status_code == 400


def test_batch_upload_celery_fallback_uses_background_task(client, auth_headers, monkeypatch, tmp_path):
    """When Celery is unavailable, tasks should fall back gracefully."""
    _patch_validate(monkeypatch, tmp_path)

    # Make Celery raise so the fallback branch is taken
    monkeypatch.setattr(
        "app.routes.documents.process_document",
        MagicMock(delay=MagicMock(side_effect=Exception("Redis down"))),
    )

    response = client.post(
        "/api/v1/documents/upload/batch",
        headers=auth_headers,
        files=[_fake_txt_file("fallback.txt")],
        data={"chunk_size": "1000", "chunk_overlap": "200"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["total"] == 1
    assert payload["task_ids"][0].startswith("local_")


def test_batch_upload_document_persisted_in_db(client, auth_headers, monkeypatch, tmp_path, db_session):
    _patch_validate(monkeypatch, tmp_path)
    _patch_celery(monkeypatch)

    response = client.post(
        "/api/v1/documents/upload/batch",
        headers=auth_headers,
        files=[_fake_txt_file("persisted.txt")],
        data={"chunk_size": "1000", "chunk_overlap": "200"},
    )

    assert response.status_code == 202
    doc_id = response.json()["documents"][0]["id"]
    doc = db_session.get(Document, doc_id)
    assert doc is not None
    assert doc.original_name == "persisted.txt"
    assert doc.status == "pending"
    assert doc.chunk_size == 1000
    assert doc.chunk_overlap == 200


def test_batch_upload_chunk_settings_stored(client, auth_headers, monkeypatch, tmp_path, db_session):
    _patch_validate(monkeypatch, tmp_path)
    _patch_celery(monkeypatch)

    response = client.post(
        "/api/v1/documents/upload/batch",
        headers=auth_headers,
        files=[_fake_txt_file("chunked.txt")],
        data={"chunk_size": "800", "chunk_overlap": "100"},
    )

    assert response.status_code == 202
    doc_id = response.json()["documents"][0]["id"]
    doc = db_session.get(Document, doc_id)
    assert doc.chunk_size == 800
    assert doc.chunk_overlap == 100

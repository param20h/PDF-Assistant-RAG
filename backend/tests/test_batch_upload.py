"""
Tests for POST /documents/upload/batch — issue #435.
"""
import io
import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf_bytes() -> bytes:
    """Return the minimal bytes of a valid single-page PDF."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
    )


def _pdf_file(name: str = "test.pdf") -> tuple[str, tuple]:
    """Return a (field_name, (filename, bytes_io, mimetype)) tuple for requests."""
    return ("files", (name, io.BytesIO(_make_pdf_bytes()), "application/pdf"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBatchUpload:
    URL = "/documents/upload/batch"

    def test_no_auth_rejected(self, client):
        response = client.post(self.URL, files=[_pdf_file()])
        assert response.status_code == 401

    def test_empty_file_list_rejected(self, client, auth_headers, monkeypatch, tmp_path):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
        # FastAPI will return 422 when the required `files` field is missing
        response = client.post(self.URL, headers=auth_headers)
        assert response.status_code == 422

    def test_too_many_files_rejected(self, client, auth_headers, monkeypatch, tmp_path):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
        with (
            patch("app.routes.documents.validate_upload", side_effect=Exception("mocked")),
        ):
            files = [_pdf_file(f"file{i}.pdf") for i in range(21)]
            response = client.post(self.URL, headers=auth_headers, files=files)
        # Our ValidationException maps to 400
        assert response.status_code == 400

    def test_single_file_success(self, client, auth_headers, monkeypatch, tmp_path):
        upload_dir = str(tmp_path)
        monkeypatch.setenv("UPLOAD_DIR", upload_dir)

        fake_temp = tmp_path / "fake_tmp.pdf"
        fake_temp.write_bytes(_make_pdf_bytes())

        with (
            patch("app.routes.documents.settings") as mock_settings,
            patch("app.routes.documents.validate_upload", return_value=str(fake_temp)),
            patch("app.routes.documents.process_document") as mock_task,
            patch("app.routes.documents.shutil.move"),
        ):
            mock_settings.UPLOAD_DIR = upload_dir
            mock_settings.ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}

            fake_celery_result = MagicMock()
            fake_celery_result.id = "celery-task-id-1"
            mock_task.delay.return_value = fake_celery_result

            response = client.post(
                self.URL,
                headers=auth_headers,
                files=[_pdf_file("doc1.pdf")],
            )

        assert response.status_code == 202
        body = response.json()
        assert body["total"] == 1
        assert body["succeeded"] == 1
        assert body["failed"] == 0
        assert body["results"][0]["success"] is True
        assert body["results"][0]["filename"] == "doc1.pdf"

    def test_multi_file_partial_failure(self, client, auth_headers, monkeypatch, tmp_path):
        """One valid file + one file that fails validation → partial success."""
        upload_dir = str(tmp_path)
        monkeypatch.setenv("UPLOAD_DIR", upload_dir)

        fake_temp = tmp_path / "fake_tmp.pdf"
        fake_temp.write_bytes(_make_pdf_bytes())

        call_count = {"n": 0}

        async def fake_validate(file):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return str(fake_temp)
            raise Exception("Corrupted or invalid file")

        with (
            patch("app.routes.documents.settings") as mock_settings,
            patch("app.routes.documents.validate_upload", side_effect=fake_validate),
            patch("app.routes.documents.process_document") as mock_task,
            patch("app.routes.documents.shutil.move"),
        ):
            mock_settings.UPLOAD_DIR = upload_dir
            mock_settings.ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}

            fake_celery_result = MagicMock()
            fake_celery_result.id = "celery-task-id-2"
            mock_task.delay.return_value = fake_celery_result

            response = client.post(
                self.URL,
                headers=auth_headers,
                files=[_pdf_file("good.pdf"), _pdf_file("bad.pdf")],
            )

        assert response.status_code == 202
        body = response.json()
        assert body["total"] == 2
        assert body["succeeded"] == 1
        assert body["failed"] == 1

        successes = [r for r in body["results"] if r["success"]]
        failures = [r for r in body["results"] if not r["success"]]
        assert len(successes) == 1
        assert len(failures) == 1
        assert failures[0]["error"] is not None

    def test_celery_fallback_to_background_task(self, client, auth_headers, monkeypatch, tmp_path):
        """When Celery is unavailable the endpoint falls back gracefully."""
        upload_dir = str(tmp_path)
        monkeypatch.setenv("UPLOAD_DIR", upload_dir)

        fake_temp = tmp_path / "fake_tmp.pdf"
        fake_temp.write_bytes(_make_pdf_bytes())

        with (
            patch("app.routes.documents.settings") as mock_settings,
            patch("app.routes.documents.validate_upload", return_value=str(fake_temp)),
            patch("app.routes.documents.process_document") as mock_task,
            patch("app.routes.documents.shutil.move"),
        ):
            mock_settings.UPLOAD_DIR = upload_dir
            mock_settings.ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}
            mock_task.delay.side_effect = Exception("Redis unavailable")

            response = client.post(
                self.URL,
                headers=auth_headers,
                files=[_pdf_file("celery_fail.pdf")],
            )

        assert response.status_code == 202
        body = response.json()
        assert body["succeeded"] == 1
        # task_id should start with "local_" when falling back
        assert body["results"][0]["document"]["task_id"].startswith("local_")

    def test_unsupported_extension_counted_as_failure(self, client, auth_headers, monkeypatch, tmp_path):
        upload_dir = str(tmp_path)
        monkeypatch.setenv("UPLOAD_DIR", upload_dir)

        with (
            patch("app.routes.documents.settings") as mock_settings,
        ):
            mock_settings.UPLOAD_DIR = upload_dir
            mock_settings.ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}

            response = client.post(
                self.URL,
                headers=auth_headers,
                files=[("files", ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream"))],
            )

        assert response.status_code == 202
        body = response.json()
        assert body["total"] == 1
        assert body["failed"] == 1
        assert body["succeeded"] == 0

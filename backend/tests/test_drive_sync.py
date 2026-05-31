from pathlib import Path

from app.models import Document, DriveConnection
from app.services import drive_sync


def test_drive_sync_ingests_new_pdf_and_skips_existing(db_session, user, tmp_path, monkeypatch):
    monkeypatch.setattr(drive_sync.settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(drive_sync, "_build_drive_service", lambda connection: object())
    monkeypatch.setattr(
        drive_sync,
        "_list_pdf_files",
        lambda service, folder_id: [
            {"id": "drive-file-1", "name": "Guide.pdf", "size": "0"},
        ],
    )

    def fake_download(service, file_id, destination):
        Path(destination).write_bytes(b"%PDF-1.4\n")

    def fake_ingest(document_id, filepath, original_name, user_id):
        document = db_session.query(Document).filter(Document.id == document_id).one()
        document.status = "ready"
        document.page_count = 1
        document.chunk_count = 1
        db_session.commit()

    monkeypatch.setattr(drive_sync, "_download_drive_file", fake_download)
    monkeypatch.setattr(drive_sync, "ingest_document", fake_ingest)

    connection = DriveConnection(user_id=user.id, folder_id="folder-1")
    db_session.add(connection)
    db_session.commit()

    first_stats = drive_sync.sync_drive_pdfs(db_session)
    second_stats = drive_sync.sync_drive_pdfs(db_session)

    document = db_session.query(Document).filter(Document.drive_file_id == "drive-file-1").one()
    assert first_stats["ingested"] == 1
    assert second_stats["skipped"] == 1
    assert document.status == "ready"
    assert document.original_name == "Guide.pdf"
    assert document.drive_folder_id == "folder-1"

"""Google Drive PDF discovery and ingestion service."""
import io
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Document, DriveConnection
from app.services.document_ingestion import ingest_document

logger = logging.getLogger(__name__)
settings = get_settings()
_sync_lock = threading.Lock()

PDF_MIME_TYPE = "application/pdf"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _build_drive_service(connection: DriveConnection):
    """Build a Google Drive API client for a saved connection."""
    try:
        from google.oauth2.credentials import Credentials
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "Google Drive sync requires google-api-python-client and google-auth"
        ) from exc

    if connection.credentials_json:
        credentials = Credentials.from_authorized_user_info(
            json.loads(connection.credentials_json),
            scopes=DRIVE_SCOPES,
        )
    else:
        service_account_file = (
            connection.service_account_file or settings.GOOGLE_SERVICE_ACCOUNT_FILE
        )
        if not service_account_file:
            raise RuntimeError("Drive connection has no OAuth credentials or service account file")
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=DRIVE_SCOPES,
        )

    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _list_pdf_files(service, folder_id: str) -> list[dict]:
    """Return PDF files directly inside a Drive folder."""
    files: list[dict] = []
    page_token = None
    query = (
        f"'{folder_id}' in parents and "
        f"mimeType = '{PDF_MIME_TYPE}' and trashed = false"
    )

    while True:
        response = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                pageToken=page_token,
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return files


def _download_drive_file(service, file_id: str, destination: str):
    """Download a Drive file to disk."""
    from googleapiclient.http import MediaIoBaseDownload

    request = service.files().get_media(fileId=file_id)
    with io.FileIO(destination, "wb") as file_handle:
        downloader = MediaIoBaseDownload(file_handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def sync_drive_pdfs(db: Session) -> dict:
    """
    Discover new PDFs from enabled Drive connections, download them, and ingest them.
    """
    if not _sync_lock.acquire(blocking=False):
        logger.info("Drive sync skipped because a previous run is still active")
        return {"connections": 0, "discovered": 0, "ingested": 0, "skipped": 0, "failed": 0}

    stats = {"connections": 0, "discovered": 0, "ingested": 0, "skipped": 0, "failed": 0}
    try:
        connections = (
            db.query(DriveConnection)
            .filter(DriveConnection.enabled.is_(True))
            .all()
        )
        stats["connections"] = len(connections)

        for connection in connections:
            try:
                service = _build_drive_service(connection)
                files = _list_pdf_files(service, connection.folder_id)
                stats["discovered"] += len(files)

                for drive_file in files:
                    existing = (
                        db.query(Document)
                        .filter(Document.drive_file_id == drive_file["id"])
                        .first()
                    )
                    if existing:
                        stats["skipped"] += 1
                        continue

                    user_dir = os.path.join(settings.UPLOAD_DIR, connection.user_id)
                    os.makedirs(user_dir, exist_ok=True)
                    stored_filename = f"{uuid.uuid4().hex}.pdf"
                    filepath = os.path.join(user_dir, stored_filename)

                    document = Document(
                        user_id=connection.user_id,
                        filename=stored_filename,
                        original_name=drive_file.get("name") or stored_filename,
                        file_size=int(drive_file.get("size") or 0),
                        status="pending",
                        drive_file_id=drive_file["id"],
                        drive_folder_id=connection.folder_id,
                        drive_synced_at=datetime.now(timezone.utc),
                    )
                    db.add(document)
                    db.commit()
                    db.refresh(document)

                    try:
                        _download_drive_file(service, drive_file["id"], filepath)
                        document.file_size = Path(filepath).stat().st_size
                        db.commit()
                        ingest_document(
                            document_id=document.id,
                            filepath=filepath,
                            original_name=document.original_name,
                            user_id=connection.user_id,
                        )
                        stats["ingested"] += 1
                    except Exception as exc:
                        logger.exception(
                            "Drive ingestion failed for file %s",
                            drive_file.get("id"),
                        )
                        db.refresh(document)
                        document.status = "failed"
                        document.error_message = str(exc)[:500]
                        db.commit()
                        stats["failed"] += 1

                connection.last_synced_at = datetime.now(timezone.utc)
                connection.updated_at = datetime.now(timezone.utc)
                db.commit()
            except Exception:
                logger.exception("Drive sync failed for connection %s", connection.id)
                stats["failed"] += 1

        logger.info("Drive sync complete: %s", stats)
        return stats
    finally:
        _sync_lock.release()


def sync_drive_pdfs_with_session() -> dict:
    """Run Drive sync with an owned database session."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        return sync_drive_pdfs(db)
    finally:
        db.close()

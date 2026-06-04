import asyncio
import io
import sys
import types
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile
from pypdf import PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Document, User
from app.routes import documents


def _pdf_bytes() -> bytes:
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(buffer)
    return buffer.getvalue()


def _upload_file(name: str, content: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(content))


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def fake_magic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        sys.modules,
        "magic",
        types.SimpleNamespace(from_file=lambda *_args, **_kwargs: "application/pdf"),
    )


def test_validate_upload_accepts_valid_pdf() -> None:
    temp_path = None

    try:
        temp_path = _run(documents.validate_upload(_upload_file("report.pdf", _pdf_bytes())))
        assert Path(temp_path).exists()
        assert Path(temp_path).suffix == ".pdf"
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


def test_validate_upload_rejects_invalid_file_type() -> None:
    with pytest.raises(HTTPException) as exc:
        _run(documents.validate_upload(_upload_file("notes.exe", b"not a document")))

    assert exc.value.status_code == 400
    assert "Only PDF" in exc.value.detail


def test_validate_upload_rejects_oversized_file_and_removes_temp_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    created_paths: list[Path] = []
    original_named_temporary_file = documents.tempfile.NamedTemporaryFile

    def tracking_tempfile(*args, **kwargs):
        kwargs.setdefault("dir", tmp_path)
        handle = original_named_temporary_file(*args, **kwargs)
        created_paths.append(Path(handle.name))
        return handle

    monkeypatch.setattr(documents.settings, "MAX_UPLOAD_SIZE_MB", 0)
    monkeypatch.setattr(documents.tempfile, "NamedTemporaryFile", tracking_tempfile)

    with pytest.raises(HTTPException) as exc:
        _run(documents.validate_upload(_upload_file("too-large.pdf", _pdf_bytes())))

    assert exc.value.status_code == 400
    assert exc.value.detail == "File too large"
    assert created_paths
    assert all(not path.exists() for path in created_paths)


def test_validate_upload_rejects_corrupted_pdf() -> None:
    with pytest.raises(HTTPException) as exc:
        _run(documents.validate_upload(_upload_file("broken.pdf", b"%PDF-1.4\nnot really a pdf")))

    assert exc.value.status_code == 400
    assert exc.value.detail == "Corrupted or invalid file"


def test_upload_document_returns_409_for_duplicate_original_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    user = User(
        id=str(uuid.uuid4()),
        username="upload-tester",
        email="upload@example.com",
        hashed_password="hashed",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    temp_files: list[Path] = []

    async def fake_validate_upload(_file: UploadFile) -> str:
        handle = documents.tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        with handle:
            handle.write(_pdf_bytes())
        temp_files.append(Path(handle.name))
        return handle.name

    monkeypatch.setattr(documents, "validate_upload", fake_validate_upload)
    monkeypatch.setattr(documents.settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(
        documents.process_document,
        "delay",
        lambda **_kwargs: types.SimpleNamespace(id="queued-task"),
    )

    first = _run(
        documents.upload_document(
            file=_upload_file("same-name.pdf", b"first"),
            user=user,
            db=session,
        )
    )

    with pytest.raises(HTTPException) as exc:
        _run(
            documents.upload_document(
                file=_upload_file("same-name.pdf", b"second"),
                user=user,
                db=session,
            )
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == {
        "conflict": True,
        "existing_id": first.id,
        "original_name": "same-name.pdf",
    }

    stored_docs = session.query(Document).all()
    assert len(stored_docs) == 1
    assert stored_docs[0].original_name == "same-name.pdf"
    assert first.original_name == "same-name.pdf"
    assert first.task_id == "queued-task"
    user_upload_dir = tmp_path / "uploads" / user.id
    assert (user_upload_dir / stored_docs[0].filename).exists()
    assert len(list(user_upload_dir.glob("*.pdf"))) == 1
    assert all(not path.exists() for path in temp_files)


def test_replace_document_resets_row_and_requeues_ingest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    user = User(
        id=str(uuid.uuid4()),
        username="replace-tester",
        email="replace@example.com",
        hashed_password="hashed",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(documents.settings, "UPLOAD_DIR", str(upload_dir))
    user_dir = upload_dir / user.id
    user_dir.mkdir(parents=True)

    old_filename = "old-doc.pdf"
    old_path = user_dir / old_filename
    old_path.write_bytes(b"old-content")

    document = Document(
        user_id=user.id,
        filename=old_filename,
        original_name="report.pdf",
        file_size=len(b"old-content"),
        status="ready",
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    deleted_vectors: list[tuple[str, str]] = []

    def track_delete(document_id: str, user_id: str) -> None:
        deleted_vectors.append((document_id, user_id))

    monkeypatch.setattr(documents, "delete_document_chunks", track_delete)

    queued: list[dict] = []

    monkeypatch.setattr(
        documents.process_document,
        "delay",
        lambda **kwargs: queued.append(kwargs) or types.SimpleNamespace(id="replace-task"),
    )

    result = _run(
        documents.replace_document(
            doc_id=document.id,
            file=_upload_file("report.pdf", b"new-content"),
            user=user,
            db=session,
        )
    )

    session.refresh(document)

    assert not old_path.exists()
    assert deleted_vectors == [(str(document.id), str(user.id))]
    assert document.original_name == "report.pdf"
    assert document.file_size == len(b"new-content")
    assert document.status == "pending"
    assert document.filename != old_filename
    assert (user_dir / document.filename).exists()
    assert (user_dir / document.filename).read_bytes() == b"new-content"
    assert len(queued) == 1
    assert queued[0]["document_id"] == document.id
    assert queued[0]["user_id"] == user.id
    assert result.task_id == "replace-task"


def test_replace_document_returns_423_while_processing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    user = User(
        id=str(uuid.uuid4()),
        username="locked-tester",
        email="locked@example.com",
        hashed_password="hashed",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    monkeypatch.setattr(documents.settings, "UPLOAD_DIR", str(tmp_path / "uploads"))

    document = Document(
        user_id=user.id,
        filename="busy.pdf",
        original_name="busy.pdf",
        file_size=10,
        status="processing",
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    with pytest.raises(HTTPException) as exc:
        _run(
            documents.replace_document(
                doc_id=document.id,
                file=_upload_file("busy.pdf", b"new"),
                user=user,
                db=session,
            )
        )

    assert exc.value.status_code == 423

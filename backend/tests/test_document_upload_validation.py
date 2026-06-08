import asyncio
import io
import sys
import types
import uuid
from pathlib import Path

import pytest
from fastapi import UploadFile
from app.exceptions import ValidationException
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
    with pytest.raises(ValidationException) as exc:
        _run(documents.validate_upload(_upload_file("notes.exe", b"not a document")))

    assert exc.value.status_code == 400
    assert "Only PDF" in exc.value.message


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

    with pytest.raises(ValidationException) as exc:
        _run(documents.validate_upload(_upload_file("too-large.pdf", _pdf_bytes())))

    assert exc.value.status_code == 400
    assert exc.value.message == "File too large"
    assert created_paths
    assert all(not path.exists() for path in created_paths)


def test_validate_upload_rejects_corrupted_pdf() -> None:
    with pytest.raises(ValidationException) as exc:
        _run(documents.validate_upload(_upload_file("broken.pdf", b"%PDF-1.4\nnot really a pdf")))

    assert exc.value.status_code == 400
    assert exc.value.message == "Corrupted or invalid file"


@pytest.mark.parametrize(
    "first_hex,second_hex",
    [
        (
            "11111111111111111111111111111111",
            "22222222222222222222222222222222",
        )
    ],
)
def test_upload_document_handles_duplicate_original_names(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    first_hex: str,
    second_hex: str,
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

    class FakeUUID:
        def __init__(self, value: str) -> None:
            self.hex = value

    uuid_values = iter([FakeUUID(first_hex), FakeUUID(second_hex)])

    monkeypatch.setattr(documents, "validate_upload", fake_validate_upload)
    monkeypatch.setattr(documents.settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(documents.uuid, "uuid4", lambda: next(uuid_values))
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
    second = _run(
        documents.upload_document(
            file=_upload_file("same-name.pdf", b"second"),
            user=user,
            db=session,
        )
    )

    stored_docs = session.query(Document).order_by(Document.filename).all()

    assert [doc.original_name for doc in stored_docs] == ["same-name.pdf", "same-name.pdf"]
    assert len({doc.filename for doc in stored_docs}) == 2
    assert first.original_name == second.original_name == "same-name.pdf"
    assert first.task_id == second.task_id == "queued-task"
    assert (tmp_path / "uploads" / user.id / f"{first_hex}.pdf").exists()
    assert (tmp_path / "uploads" / user.id / f"{second_hex}.pdf").exists()
    assert all(not path.exists() for path in temp_files)

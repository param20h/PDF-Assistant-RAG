from pathlib import Path
import sys
import types

import pytest

from app.rag import chunker
from app.rag.chunker import chunk_document, get_page_count


def test_txt_extraction_and_chunking(tmp_path):
    file_path = tmp_path / "notes.txt"
    file_path.write_text("This is a sample text file for chunking.", encoding="utf-8")

    chunks = chunk_document(str(file_path))

    assert len(chunks) >= 1
    assert chunks[0]["page"] == 1
    assert "sample text file" in chunks[0]["text"]


def test_empty_txt_returns_no_chunks(tmp_path):
    file_path = tmp_path / "empty.txt"
    file_path.write_text("   \n", encoding="utf-8")

    assert chunk_document(str(file_path)) == []


def test_unsupported_extension_raises_value_error(tmp_path):
    file_path = tmp_path / "data.csv"
    file_path.write_text("a,b,c", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file type"):
        chunk_document(str(file_path))


def test_get_page_count_for_txt_returns_one(tmp_path):
    file_path = tmp_path / "single.txt"
    file_path.write_text("hello", encoding="utf-8")

    assert get_page_count(str(file_path)) == 1


def test_pdf_table_detection_separates_table_from_paragraph(monkeypatch):
    class FakeTable:
        bbox = (40, 90, 300, 160)

        def extract(self):
            return [["Name", "Amount"], ["Alpha", "$10"]]

    class FakePage:
        width = 400
        height = 200

        def find_tables(self):
            return [FakeTable()]

        def extract_words(self):
            return [
                {"text": "Intro", "x0": 40,  "x1": 70, "top": 20, "bottom": 30},
                {"text": "paragraph", "x0":  75, "x1": 140, "top": 20, "bottom": 30},
                {"text": "Name", "x0": 45,  "x1": 80, "top": 100, "bottom": 110},
                {"text": "Amount", "x0": 160, "x1": 220, "top": 100, "bottom": 110},
                {"text": "Alpha", "x0": 45,  "x1": 85, "top": 125, "bottom": 135},
                {"text": "$10", "x0": 160,  "x1": 185, "top": 125, "bottom": 135},
            ]

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    fake_pdfplumber = types.SimpleNamespace(open=lambda _filepath: FakePdf())
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)
    monkeypatch.setattr(chunker, "extract_pdf_images", lambda _filepath: [])

    chunks = chunk_document("report.pdf")

    assert len(chunks) == 2
    assert chunks[0]["chunk_type"] == "text"
    assert chunks[0]["text"] == "Intro paragraph"
    assert "Name" not in chunks[0]["text"]
    assert chunks[1]["chunk_type"] == "table"
    assert chunks[1]["bbox"] == "[0.1, 0.45, 0.75, 0.8]"
    assert "| Name | Amount |" in chunks[1]["text"]
    assert "| Alpha | $10 |" in chunks[1]["text"]

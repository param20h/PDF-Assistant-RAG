from pathlib import Path
import sys
import types

import pytest

from app.rag import chunker
from app.rag.chunker import _table_to_markdown, chunk_document, get_page_count


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


def test_table_to_markdown_cleans_cells_and_escapes_pipes():
    rows = [
        ["Name", "Age", "Role"],
        [" Asha\nRao ", 24, "Admin | Owner"],
        [None, "  ", None],
        ["Ravi", 28],
    ]

    assert _table_to_markdown(rows) == "\n".join(
        [
            "| Name | Age | Role |",
            "| --- | --- | --- |",
            "| Asha Rao | 24 | Admin \\| Owner |",
            "| Ravi | 28 |  |",
        ]
    )


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
                {"text": "Intro", "x0": 40, "x1": 70, "top": 20, "bottom": 30},
                {"text": "paragraph", "x0": 75, "x1": 140, "top": 20, "bottom": 30},
                {"text": "Name", "x0": 45, "x1": 80, "top": 100, "bottom": 110},
                {"text": "Amount", "x0": 160, "x1": 220, "top": 100, "bottom": 110},
                {"text": "Alpha", "x0": 45, "x1": 85, "top": 125, "bottom": 135},
                {"text": "$10", "x0": 160, "x1": 185, "top": 125, "bottom": 135},
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


def test_unstructured_table_detection(monkeypatch):
    # Create fake Unstructured Table and Text element classes
    class FakeTableClass:
        pass

    class FakeTable(FakeTableClass):
        def __init__(self):
            self.rows = [["Name", "Amount"], ["Delta", "$40"]]
            self.page_number = 3

    class FakeText:
        def __init__(self):
            self.text = "Intro paragraph"
            self.page_number = 3

    def fake_partition_pdf(filename):
        return [FakeText(), FakeTable()]

    # Insert fake unstructured modules
    monkeypatch.setitem(sys.modules, "unstructured", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "unstructured.partition", types.SimpleNamespace())
    monkeypatch.setitem(
        sys.modules,
        "unstructured.partition.pdf",
        types.SimpleNamespace(partition_pdf=fake_partition_pdf),
    )
    monkeypatch.setitem(sys.modules, "unstructured.documents", types.SimpleNamespace())
    monkeypatch.setitem(
        sys.modules,
        "unstructured.documents.elements",
        types.SimpleNamespace(Table=FakeTableClass),
    )

    monkeypatch.setattr(chunker, "extract_pdf_images", lambda _filepath: [])

    chunks = chunk_document("sample.pdf")

    # Expect two chunks: text then table
    assert len(chunks) >= 2
    assert chunks[0]["chunk_type"] == "text"
    assert "Intro paragraph" in chunks[0]["text"]
    # find a table chunk
    table_chunks = [c for c in chunks if c.get("chunk_type") == "table"]
    assert table_chunks, "No table chunks produced by Unstructured path"
    assert table_chunks[0]["page"] == 3
    assert "| Name | Amount |" in table_chunks[0]["text"]
    assert "| Delta | $40 |" in table_chunks[0]["text"]


# ── _table_to_markdown edge cases ────────────────────────────────────────────


def test_table_to_markdown_empty_rows_returns_empty():
    assert _table_to_markdown([]) == ""


def test_table_to_markdown_all_blank_cells_returns_empty():
    rows = [[None, None], ["  ", ""], [None, "   "]]
    assert _table_to_markdown(rows) == ""


def test_table_to_markdown_single_row_acts_as_header():
    rows = [["Product", "Price"]]
    result = _table_to_markdown(rows)
    assert result == "\n".join(
        [
            "| Product | Price |",
            "| --- | --- |",
        ]
    )


def test_table_to_markdown_ragged_rows_padded_to_max_width():
    """Rows shorter than the widest row must be right-padded with empty strings."""
    rows = [
        ["A", "B", "C"],
        ["X"],
        ["Y", "Z"],
    ]
    result = _table_to_markdown(rows)
    lines = result.splitlines()
    # Every line should have the same number of pipe characters
    pipe_counts = [line.count("|") for line in lines]
    assert len(set(pipe_counts)) == 1, "All rows must have equal column count"


def test_table_to_markdown_whitespace_normalised_in_cells():
    rows = [["Col\t1", "Col\n2"], ["val  a", "val\tb"]]
    result = _table_to_markdown(rows)
    assert "Col 1" in result
    assert "Col 2" in result
    assert "val a" in result
    assert "val b" in result


def test_table_to_markdown_pipe_in_cell_is_escaped():
    rows = [["A|B", "C"], ["x|y|z", "w"]]
    result = _table_to_markdown(rows)
    assert "A\\|B" in result
    assert "x\\|y\\|z" in result


def test_table_to_markdown_separator_row_uses_triple_dash():
    rows = [["H1", "H2"], ["v1", "v2"]]
    lines = _table_to_markdown(rows).splitlines()
    assert lines[1] == "| --- | --- |"


# ── pdfplumber path — multi-page ─────────────────────────────────────────────


def test_pdf_table_multi_page_produces_chunk_per_page(monkeypatch):
    """Tables on different pages must produce separate table chunks with correct page numbers."""

    class FakeTable:
        def __init__(self, page_num):
            self._page_num = page_num
            self.bbox = (0, 50, 200, 150)

        def extract(self):
            return [["Item", "Qty"], [f"Row-p{self._page_num}", "1"]]

    class FakePage:
        def __init__(self, page_num):
            self._page_num = page_num
            self.width = 200
            self.height = 200

        def find_tables(self):
            return [FakeTable(self._page_num)]

        def extract_words(self):
            # No paragraph words — all words are inside the table bbox
            return []

    class FakePdf:
        pages = [FakePage(1), FakePage(2)]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    fake_pdfplumber = types.SimpleNamespace(open=lambda _: FakePdf())
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)
    monkeypatch.setattr(chunker, "extract_pdf_images", lambda _: [])

    chunks = chunk_document("multipage.pdf")

    table_chunks = [c for c in chunks if c.get("chunk_type") == "table"]
    assert len(table_chunks) == 2
    assert table_chunks[0]["page"] == 1
    assert table_chunks[1]["page"] == 2
    assert "Row-p1" in table_chunks[0]["text"]
    assert "Row-p2" in table_chunks[1]["text"]


def test_pdf_empty_table_is_not_emitted(monkeypatch):
    """A table whose cells are all blank must produce no chunk."""

    class FakeEmptyTable:
        bbox = (0, 50, 200, 150)

        def extract(self):
            return [[None, ""], ["  ", None]]

    class FakePage:
        width = 200
        height = 200

        def find_tables(self):
            return [FakeEmptyTable()]

        def extract_words(self):
            return []

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    fake_pdfplumber = types.SimpleNamespace(open=lambda _: FakePdf())
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)
    monkeypatch.setattr(chunker, "extract_pdf_images", lambda _: [])

    chunks = chunk_document("empty_table.pdf")
    table_chunks = [c for c in chunks if c.get("chunk_type") == "table"]
    assert table_chunks == [], "Empty tables must not produce chunks"


def test_pdf_table_index_increments_per_page(monkeypatch):
    """table_index must restart at 0 for each page (pdfplumber path)."""

    class FakeTable:
        bbox = (0, 50, 200, 150)

        def extract(self):
            return [["H"], ["V"]]

    class FakePage:
        width = 200
        height = 200

        def find_tables(self):
            return [FakeTable(), FakeTable()]

        def extract_words(self):
            return []

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    fake_pdfplumber = types.SimpleNamespace(open=lambda _: FakePdf())
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)
    monkeypatch.setattr(chunker, "extract_pdf_images", lambda _: [])

    chunks = chunk_document("two_tables.pdf")
    table_chunks = [c for c in chunks if c.get("chunk_type") == "table"]
    assert len(table_chunks) == 2
    assert table_chunks[0]["table_index"] == 0
    assert table_chunks[1]["table_index"] == 1


def test_pdf_table_bbox_normalised_to_unit_range(monkeypatch):
    """Stored bbox values must each be within [0.0, 1.0]."""

    class FakeTable:
        bbox = (20, 40, 180, 160)

        def extract(self):
            return [["X", "Y"], ["1", "2"]]

    class FakePage:
        width = 200
        height = 200

        def find_tables(self):
            return [FakeTable()]

        def extract_words(self):
            return []

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    import json as _json

    fake_pdfplumber = types.SimpleNamespace(open=lambda _: FakePdf())
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)
    monkeypatch.setattr(chunker, "extract_pdf_images", lambda _: [])

    chunks = chunk_document("bbox_check.pdf")
    table_chunks = [c for c in chunks if c.get("chunk_type") == "table"]
    assert table_chunks, "Expected at least one table chunk"

    bbox = _json.loads(table_chunks[0]["bbox"])
    assert len(bbox) == 4
    for val in bbox:
        assert 0.0 <= val <= 1.0, f"bbox value {val} out of [0, 1] range"


# ── PyMuPDF fallback path ─────────────────────────────────────────────────────


def test_pymupdf_fallback_produces_text_chunks(monkeypatch):
    """When both unstructured and pdfplumber are absent, PyMuPDF must still produce text chunks."""

    class FakePage:
        def get_text(self):
            return "Fallback text from PyMuPDF page."

    class FakeDoc:
        _pages = [FakePage()]

        def __iter__(self):
            return iter(self._pages)

        def __len__(self):
            return len(self._pages)

        def __getitem__(self, idx):
            return self._pages[idx]

        def close(self):
            pass

    # Block unstructured and pdfplumber so the fitz fallback is exercised
    monkeypatch.setitem(sys.modules, "unstructured", None)
    monkeypatch.setitem(sys.modules, "pdfplumber", None)
    monkeypatch.setattr(chunker.fitz, "open", lambda _: FakeDoc())
    monkeypatch.setattr(chunker, "extract_pdf_images", lambda _: [])

    chunks = chunk_document("fallback.pdf")
    assert len(chunks) >= 1
    assert chunks[0]["chunk_type"] == "text"
    assert "Fallback text" in chunks[0]["text"]


# ── Image chunks alongside tables ─────────────────────────────────────────────


def test_image_chunks_appended_after_text_chunks_on_same_page(monkeypatch):
    """Image chunks extracted from a page must appear after that page's text/table chunks."""

    class FakeTable:
        bbox = (0, 50, 100, 100)

        def extract(self):
            return [["Col"], ["Val"]]

    class FakePage:
        width = 100
        height = 100

        def find_tables(self):
            return [FakeTable()]

        def extract_words(self):
            # One paragraph word OUTSIDE the table bbox so the text path runs
            return [
                {"text": "Intro", "x0": 0, "x1": 40, "top": 10, "bottom": 20},
            ]

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    fake_pdfplumber = types.SimpleNamespace(open=lambda _: FakePdf())
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)
    monkeypatch.setattr(
        chunker,
        "extract_pdf_images",
        lambda _: [{"image_bytes": b"\x89PNG\r\n", "page": 1}],
    )

    chunks = chunk_document("img_and_table.pdf")

    table_chunks = [c for c in chunks if c.get("chunk_type") == "table"]
    image_chunks = [c for c in chunks if c.get("image_bytes")]

    assert table_chunks, "Expected a table chunk"
    assert image_chunks, "Expected an image chunk"

    table_idx = chunks.index(table_chunks[0])
    image_idx = chunks.index(image_chunks[0])
    assert image_idx > table_idx


# ── chunk_index continuity ────────────────────────────────────────────────────


def test_chunk_index_is_monotonically_increasing(monkeypatch):
    """chunk_index must be a 0-based counter that never resets or skips mid-document."""

    class FakeTable:
        bbox = (0, 50, 200, 150)

        def extract(self):
            return [["H1", "H2"], ["r1", "r2"]]

    class FakePage:
        width = 200
        height = 200

        def find_tables(self):
            return [FakeTable()]

        def extract_words(self):
            return [
                {"text": "Intro", "x0": 0, "x1": 40, "top": 10, "bottom": 20},
            ]

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    fake_pdfplumber = types.SimpleNamespace(open=lambda _: FakePdf())
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)
    monkeypatch.setattr(chunker, "extract_pdf_images", lambda _: [])

    chunks = chunk_document("index_check.pdf")
    indices = [c["chunk_index"] for c in chunks]

    assert indices == list(
        range(len(indices))
    ), f"chunk_index must be 0-based and contiguous, got {indices}"

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
def test_pdf_image_captioning_on_the_fly(monkeypatch):
    # Mock extract_pdf_images to yield one image on page 1
    def fake_extract_images(doc_or_path, **kwargs):
        yield {
            "image_bytes": b"fake_png_bytes",
            "page": 1,
            "width": 100,
            "height": 100,
        }

    monkeypatch.setattr(chunker, "extract_pdf_images", fake_extract_images)

    # Mock caption_image to return a custom caption
    from app.rag import vision
    monkeypatch.setattr(vision, "caption_image", lambda img_bytes, page=None: f"Captured image on page {page}")

    # Mock extract_pdf to return a text page
    def fake_extract_pdf(filepath):
        return [{"text": "Hello world on page 1", "page": 1, "chunk_type": "text"}]

    monkeypatch.setattr(chunker, "extract_pdf", fake_extract_pdf)

    # Mock fitz.open
    class FakePage:
        rect = type('Rect', (), {'width': 100, 'height': 100})()
        def search_for(self, text):
            return []

    class FakePdf:
        def __init__(self, *args, **kwargs):
            pass
        def __len__(self):
            return 1
        def __getitem__(self, idx):
            return FakePage()
        def close(self):
            pass

    import fitz
    monkeypatch.setattr(fitz, "open", lambda *args, **kwargs: FakePdf())

    # Run chunk_document
    chunks = chunk_document("dummy.pdf")

    # The result should contain the text chunk and the image chunk
    assert len(chunks) == 2
    assert chunks[0]["text"] == "Hello world on page 1"
    assert chunks[0]["page"] == 1
    
    assert chunks[1]["text"] == "Captured image on page 1"
    assert chunks[1]["page"] == 1
    assert chunks[1]["is_image"] is True
    assert chunks[1]["image_caption"] == "Captured image on page 1"
    # Ensure image_bytes is not in the chunk dictionary (preventing memory leak)
    assert "image_bytes" not in chunks[1]

def test_pdf_multi_column_layout_parsing_order(monkeypatch):
    """Ensure multi-column layout extracts text column-by-column rather than row-by-row."""
    class FakePage:
        width = 600
        height = 800

        def find_tables(self):
            return []

        def extract_words(self):
            # Simulated 2-column layout with 2 sequential reading rows
            return [
                # Left Column - Line 1
                {"text": "Left1", "x0": 50, "x1": 100, "top": 100, "bottom": 115},
                # Right Column - Line 1
                {"text": "Right1", "x0": 350, "x1": 400, "top": 100, "bottom": 115},
                # Left Column - Line 2
                {"text": "Left2", "x0": 50, "x1": 100, "top": 130, "bottom": 145},
                # Right Column - Line 2
                {"text": "Right2", "x0": 350, "x1": 400, "top": 130, "bottom": 145},
            ]

    class FakePdf:
        pages = [FakePage()]
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, traceback): return False

    fake_pdfplumber = types.SimpleNamespace(open=lambda _filepath: FakePdf())
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)
    monkeypatch.setattr(chunker, "extract_pdf_images", lambda _filepath: [])

    chunks = chunk_document("multi_column.pdf")
    
    assert len(chunks) == 1
    text_lines = chunks[0]["text"].splitlines()
    
    # Correct reading order reads entire Column 1 downward, then moves to Column 2
    assert text_lines == ["Left1", "Left2", "Right1", "Right2"]

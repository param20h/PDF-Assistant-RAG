"""
Tests for OCR fallback — issue #282.

All external I/O (fitz, pytesseract, easyocr, Pillow) is mocked so the
suite runs without Tesseract or any GPU dependency installed.
"""
import types
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_fitz_page(text: str = "") -> MagicMock:
    """Return a mock fitz.Page whose get_text() returns *text*."""
    page = MagicMock()
    page.get_text.return_value = text
    pix = MagicMock()
    pix.tobytes.return_value = b"PNG_BYTES"
    page.get_pixmap.return_value = pix
    return page


def _make_fitz_doc(pages_text: list[str]):
    """Return a mock fitz document iterating over mock pages."""
    pages = [_make_fitz_page(t) for t in pages_text]
    doc = MagicMock()
    doc.__iter__ = MagicMock(return_value=iter(pages))
    doc.__len__ = MagicMock(return_value=len(pages))
    doc.__enter__ = MagicMock(return_value=doc)
    doc.__exit__ = MagicMock(return_value=False)
    return doc, pages


# ── _page_is_image_only ───────────────────────────────────────────────────────

class TestPageIsImageOnly:
    def test_empty_page_is_image_only(self):
        from app.rag.ocr import _page_is_image_only
        page = _make_fitz_page("")
        assert _page_is_image_only(page) is True

    def test_sparse_page_is_image_only(self):
        from app.rag.ocr import _page_is_image_only
        page = _make_fitz_page("hi")
        assert _page_is_image_only(page) is True

    def test_page_with_enough_text_is_not_image_only(self):
        from app.rag.ocr import _page_is_image_only
        page = _make_fitz_page("A" * 50)
        assert _page_is_image_only(page) is False

    def test_boundary_exactly_at_min_chars(self):
        from app.rag.ocr import _page_is_image_only, MIN_TEXT_CHARS
        page = _make_fitz_page("A" * MIN_TEXT_CHARS)
        assert _page_is_image_only(page) is False

    def test_one_below_boundary_is_image_only(self):
        from app.rag.ocr import _page_is_image_only, MIN_TEXT_CHARS
        page = _make_fitz_page("A" * (MIN_TEXT_CHARS - 1))
        assert _page_is_image_only(page) is True


# ── _render_page_to_image ─────────────────────────────────────────────────────

class TestRenderPageToImage:
    def test_returns_png_bytes(self):
        from app.rag.ocr import _render_page_to_image
        page = _make_fitz_page()
        result = _render_page_to_image(page, dpi=72)
        assert result == b"PNG_BYTES"
        page.get_pixmap.assert_called_once()


# ── _ocr_with_tesseract ───────────────────────────────────────────────────────

class TestOcrWithTesseract:
    def test_returns_extracted_text(self):
        from app.rag.ocr import _ocr_with_tesseract

        mock_pytesseract = types.ModuleType("pytesseract")
        mock_pytesseract.image_to_string = MagicMock(return_value="  Hello OCR  ")

        mock_pil_image = MagicMock()
        mock_pil_module = types.ModuleType("PIL")
        mock_pil_image_class = MagicMock(return_value=mock_pil_image)
        mock_pil_module.Image = MagicMock()
        mock_pil_module.Image.open = MagicMock(return_value=mock_pil_image)

        with patch.dict(
            "sys.modules",
            {"pytesseract": mock_pytesseract, "PIL": mock_pil_module, "PIL.Image": mock_pil_module.Image},
        ):
            result = _ocr_with_tesseract(b"PNG_BYTES")

        assert result == "Hello OCR"

    def test_raises_import_error_when_tesseract_missing(self):
        from app.rag.ocr import _ocr_with_tesseract
        with patch.dict("sys.modules", {"pytesseract": None, "PIL": None, "PIL.Image": None}):
            with pytest.raises(ImportError, match="pytesseract"):
                _ocr_with_tesseract(b"PNG_BYTES")


# ── ocr_page ─────────────────────────────────────────────────────────────────

class TestOcrPage:
    def test_uses_tesseract_by_default(self, monkeypatch):
        import app.rag.ocr as ocr_module
        monkeypatch.setattr(ocr_module, "OCR_BACKEND", "tesseract")
        monkeypatch.setattr(ocr_module, "_render_page_to_image", lambda page, dpi: b"PNG")
        monkeypatch.setattr(ocr_module, "_ocr_with_tesseract", lambda b: "tesseract text")

        page = _make_fitz_page()
        result = ocr_module.ocr_page(page)
        assert result == "tesseract text"

    def test_uses_easyocr_when_configured(self, monkeypatch):
        import app.rag.ocr as ocr_module
        monkeypatch.setattr(ocr_module, "OCR_BACKEND", "easyocr")
        monkeypatch.setattr(ocr_module, "_render_page_to_image", lambda page, dpi: b"PNG")
        monkeypatch.setattr(ocr_module, "_ocr_with_easyocr", lambda b: "easyocr text")

        page = _make_fitz_page()
        result = ocr_module.ocr_page(page)
        assert result == "easyocr text"


# ── extract_pdf_with_ocr ─────────────────────────────────────────────────────

class TestExtractPdfWithOcr:
    def test_native_text_pages_skip_ocr(self, monkeypatch, tmp_path):
        import app.rag.ocr as ocr_module

        rich_text = "A" * 100
        doc, pages = _make_fitz_doc([rich_text])

        monkeypatch.setattr("fitz.open", lambda path: doc)
        ocr_called = []
        monkeypatch.setattr(ocr_module, "ocr_page", lambda page, dpi=200: ocr_called.append(1) or "")

        result = ocr_module.extract_pdf_with_ocr(str(tmp_path / "test.pdf"))

        assert len(result) == 1
        assert result[0]["ocr"] is False
        assert result[0]["text"] == rich_text.strip()
        assert ocr_called == []

    def test_image_only_pages_trigger_ocr(self, monkeypatch, tmp_path):
        import app.rag.ocr as ocr_module

        doc, _ = _make_fitz_doc([""])  # empty page
        monkeypatch.setattr("fitz.open", lambda path: doc)
        monkeypatch.setattr(ocr_module, "ocr_page", lambda page, dpi=200: "Scanned text here")

        result = ocr_module.extract_pdf_with_ocr(str(tmp_path / "scan.pdf"))

        assert len(result) == 1
        assert result[0]["ocr"] is True
        assert result[0]["text"] == "Scanned text here"
        assert result[0]["page"] == 1

    def test_mixed_pages_handled_correctly(self, monkeypatch, tmp_path):
        import app.rag.ocr as ocr_module

        rich = "B" * 100
        doc, _ = _make_fitz_doc([rich, ""])
        monkeypatch.setattr("fitz.open", lambda path: doc)
        monkeypatch.setattr(ocr_module, "ocr_page", lambda page, dpi=200: "OCR result")

        result = ocr_module.extract_pdf_with_ocr(str(tmp_path / "mixed.pdf"))

        assert len(result) == 2
        assert result[0]["ocr"] is False
        assert result[0]["page"] == 1
        assert result[1]["ocr"] is True
        assert result[1]["page"] == 2

    def test_ocr_returning_empty_skips_page(self, monkeypatch, tmp_path):
        import app.rag.ocr as ocr_module

        doc, _ = _make_fitz_doc([""])
        monkeypatch.setattr("fitz.open", lambda path: doc)
        monkeypatch.setattr(ocr_module, "ocr_page", lambda page, dpi=200: "")

        result = ocr_module.extract_pdf_with_ocr(str(tmp_path / "blank.pdf"))
        assert result == []

    def test_ocr_import_error_skips_page_gracefully(self, monkeypatch, tmp_path):
        import app.rag.ocr as ocr_module

        doc, _ = _make_fitz_doc([""])
        monkeypatch.setattr("fitz.open", lambda path: doc)
        monkeypatch.setattr(
            ocr_module, "ocr_page", MagicMock(side_effect=ImportError("no tesseract"))
        )

        result = ocr_module.extract_pdf_with_ocr(str(tmp_path / "fail.pdf"))
        assert result == []

    def test_ocr_exception_skips_page_gracefully(self, monkeypatch, tmp_path):
        import app.rag.ocr as ocr_module

        doc, _ = _make_fitz_doc([""])
        monkeypatch.setattr("fitz.open", lambda path: doc)
        monkeypatch.setattr(
            ocr_module, "ocr_page", MagicMock(side_effect=RuntimeError("segfault"))
        )

        result = ocr_module.extract_pdf_with_ocr(str(tmp_path / "crash.pdf"))
        assert result == []


# ── extract_pdf fallback chain (chunker integration) ─────────────────────────

class TestExtractPdfOcrFallback:
    def test_ocr_called_when_all_extractors_return_empty(self, monkeypatch):
        import app.rag.chunker as chunker_module
        import app.rag.ocr as ocr_module

        monkeypatch.setattr(
            chunker_module, "extract_pdf_with_unstructured",
            MagicMock(side_effect=Exception("unavailable")),
        )
        monkeypatch.setattr(
            chunker_module, "extract_pdf_with_tables",
            MagicMock(side_effect=Exception("unavailable")),
        )
        monkeypatch.setattr(
            chunker_module, "extract_pdf_with_pymupdf",
            MagicMock(return_value=[]),
        )
        monkeypatch.setattr(
            ocr_module, "extract_pdf_with_ocr",
            MagicMock(return_value=[{"text": "OCR text", "page": 1, "chunk_type": "text", "ocr": True}]),
        )

        result = chunker_module.extract_pdf("dummy.pdf")

        assert len(result) == 1
        assert result[0]["ocr"] is True
        assert result[0]["text"] == "OCR text"

    def test_ocr_not_called_when_extractor_succeeds(self, monkeypatch):
        import app.rag.chunker as chunker_module
        import app.rag.ocr as ocr_module

        monkeypatch.setattr(
            chunker_module, "extract_pdf_with_unstructured",
            MagicMock(return_value=[{"text": "Native text", "page": 1, "chunk_type": "text"}]),
        )
        ocr_spy = MagicMock(return_value=[])
        monkeypatch.setattr(ocr_module, "extract_pdf_with_ocr", ocr_spy)

        result = chunker_module.extract_pdf("dummy.pdf")

        ocr_spy.assert_not_called()
        assert result[0]["text"] == "Native text"

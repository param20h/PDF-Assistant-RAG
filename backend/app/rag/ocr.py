"""
OCR fallback for image-based PDF pages.

Uses pytesseract (Tesseract OCR) to extract text from pages that contain
no selectable text. easyocr is supported as an optional alternative backend
controlled by the OCR_BACKEND environment variable.

Detection strategy: a page is considered image-only when PyMuPDF's
get_text() returns fewer than MIN_TEXT_CHARS characters after stripping.
"""

import logging
import os
from typing import Any, Dict, List

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Pages with fewer than this many characters are treated as image-only
MIN_TEXT_CHARS = 20

# OCR backend: "tesseract" (default) or "easyocr"
OCR_BACKEND = os.getenv("OCR_BACKEND", "tesseract").lower()


def _page_is_image_only(page: fitz.Page) -> bool:
    """Return True when a PDF page has no meaningful selectable text."""
    text = page.get_text().strip()
    return len(text) < MIN_TEXT_CHARS


def _render_page_to_image(page: fitz.Page, dpi: int = 200) -> bytes:
    """Render a fitz page to PNG bytes at the given DPI."""
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes("png")


def _ocr_with_tesseract(image_bytes: bytes) -> str:
    """Run Tesseract OCR on raw PNG bytes and return extracted text."""
    try:
        import io
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "pytesseract and Pillow are required for OCR. "
            "Install them with: pip install pytesseract Pillow"
        ) from exc

    image = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(image, lang="eng")
    return text.strip()


def _ocr_with_easyocr(image_bytes: bytes) -> str:
    """Run EasyOCR on raw PNG bytes and return extracted text."""
    try:
        import easyocr
        import numpy as np
        from PIL import Image
        import io
    except ImportError as exc:
        raise ImportError(
            "easyocr, Pillow, and numpy are required for EasyOCR. "
            "Install them with: pip install easyocr Pillow numpy"
        ) from exc

    # EasyOCR reader is expensive to initialise — cache it at module level
    global _easyocr_reader  # noqa: PLW0603
    if "_easyocr_reader" not in globals():
        _easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_array = np.array(image)
    results = _easyocr_reader.readtext(img_array, detail=0, paragraph=True)
    return "\n".join(results).strip()


def ocr_page(page: fitz.Page, dpi: int = 200) -> str:
    """
    OCR a single fitz page and return the extracted text.

    Renders the page to a raster image at *dpi* resolution, then runs the
    configured OCR backend (``OCR_BACKEND`` env var, default ``tesseract``).

    Args:
        page: An open fitz.Page object.
        dpi:  Render resolution. Higher values give better accuracy at the
              cost of memory and speed.

    Returns:
        Extracted text string, possibly empty if OCR yields nothing.

    Raises:
        ImportError: If the selected backend's dependencies are not installed.
    """
    image_bytes = _render_page_to_image(page, dpi=dpi)

    if OCR_BACKEND == "easyocr":
        return _ocr_with_easyocr(image_bytes)
    return _ocr_with_tesseract(image_bytes)


def extract_pdf_with_ocr(filepath: str, dpi: int = 200) -> List[Dict[str, Any]]:
    """
    Extract text from a PDF, using OCR for image-only pages.

    For each page:
    - If PyMuPDF can extract at least ``MIN_TEXT_CHARS`` characters,
      use that text directly (fast path).
    - Otherwise render the page and run OCR (slow path).

    Pages that yield no text via either method are skipped.

    Args:
        filepath: Absolute path to the PDF file.
        dpi:      Render DPI for OCR pages (default 200).

    Returns:
        List of dicts with keys ``text``, ``page``, ``chunk_type``,
        and ``ocr`` (bool, True when the text came from OCR).
    """
    doc = fitz.open(filepath)
    pages: List[Dict[str, Any]] = []

    try:
        for page_num, page in enumerate(doc, start=1):
            native_text = page.get_text().strip()

            if len(native_text) >= MIN_TEXT_CHARS:
                pages.append({
                    "text": native_text,
                    "page": page_num,
                    "chunk_type": "text",
                    "ocr": False,
                })
                continue

            # Image-only page — fall back to OCR
            logger.info(
                "Page %d of '%s' has no selectable text — running OCR (backend=%s)",
                page_num,
                filepath,
                OCR_BACKEND,
            )
            try:
                ocr_text = ocr_page(page, dpi=dpi)
                if ocr_text:
                    pages.append({
                        "text": ocr_text,
                        "page": page_num,
                        "chunk_type": "text",
                        "ocr": True,
                    })
                else:
                    logger.warning(
                        "OCR returned no text for page %d of '%s'",
                        page_num,
                        filepath,
                    )
            except ImportError:
                logger.warning(
                    "OCR backend '%s' not installed — skipping page %d of '%s'",
                    OCR_BACKEND,
                    page_num,
                    filepath,
                )
            except Exception as exc:
                logger.warning(
                    "OCR failed for page %d of '%s': %s",
                    page_num,
                    filepath,
                    exc,
                )
    finally:
        doc.close()

    return pages

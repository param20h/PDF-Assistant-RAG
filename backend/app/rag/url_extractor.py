"""
PDF URL extraction using PyMuPDF link annotations.

Extracts all unique HTTP/HTTPS URLs from a PDF's link annotations
and text-based URIs across all pages. Called during document ingestion
so URLs are stored in the document metadata column.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# Matches http/https URLs in plain text as a fallback
_URL_RE = re.compile(
    r"https?://"
    r"(?:[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%])"
    r"[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]*",
    re.IGNORECASE,
)


def extract_urls_from_pdf(filepath: str) -> List[str]:
    """Extract unique HTTP/HTTPS URLs from a PDF file.

    Two passes per page:
    1. Link annotations  — catches hyperlinks embedded by the PDF author.
    2. Plain-text regex  — catches URLs typed inline that aren't annotated.

    Args:
        filepath: Absolute path to the PDF file.

    Returns:
        Deduplicated list of URLs preserving first-seen order.
        Returns an empty list for non-PDF files or on any extraction error.
    """
    if not filepath.rsplit(".", 1)[-1].lower() == "pdf":
        return []

    try:
        import fitz  # PyMuPDF — already in requirements.txt
    except ImportError:
        logger.warning("PyMuPDF not available; skipping URL extraction")
        return []

    seen: dict = {}   # preserves insertion order, deduplicates
    doc = None

    try:
        doc = fitz.open(filepath)

        for page_num, page in enumerate(doc):
            # ── Pass 1: link annotations ──────────────────────────────────
            for link in page.get_links():
                uri = link.get("uri", "")
                if uri and uri.lower().startswith(("http://", "https://")):
                    seen.setdefault(uri.strip(), None)

            # ── Pass 2: plain-text regex ──────────────────────────────────
            text = page.get_text()
            for match in _URL_RE.finditer(text):
                url = match.group(0).rstrip(".,;:)\"'")
                seen.setdefault(url, None)

    except Exception as exc:
        logger.warning("URL extraction failed for %s: %s", filepath, exc)
        return []
    finally:
        if doc:
            doc.close()

    return list(seen.keys())

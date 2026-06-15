"""Image captioning / vision helpers for RAG pipeline.

Caption resolution order for each image chunk:
1. Bounding-box proximity  — nearest text block below/above the image in the PDF
                            (rich, zero-cost, works offline).
2. OCR (pytesseract)       — when proximity yields nothing and tesseract is installed.
3. Placeholder             — "Figure on page N (WxH px)" as a guaranteed non-empty fallback.

An optional OpenAI GPT-4o-mini vision hook is provided for deployments that set
VISION_PROVIDER=openai and OPENAI_API_KEY in settings.
"""
import base64
import logging
import app.vision.providers  # noqa: F401 — triggers self-registration
from app.vision.registry import get_vision_provider
from io import BytesIO
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Minimum image area (px²) — smaller images are decorative and skipped.
_MIN_IMAGE_AREA = 1_000


# ── 1. Proximity-based caption extraction ────────────────────────────────────

def _find_caption_near_image(
    page: fitz.Page,
    img_bbox: fitz.Rect,
    search_margin: float = 60.0,
) -> str:
    """Return the closest text block directly below (or above) an image rect."""
    page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
    blocks = page_dict.get("blocks", [])

    def _closest(region: fitz.Rect) -> str:
        candidates = []
        for block in blocks:
            if block.get("type") != 0:  # 0 == text block
                continue
            bx0, by0, bx1, by1 = block["bbox"]
            if fitz.Rect(bx0, by0, bx1, by1).intersects(region):
                text = " ".join(
                    span["text"]
                    for line in block.get("lines", [])
                    for span in line.get("spans", [])
                ).strip()
                if text:
                    candidates.append((abs(by0 - img_bbox.y1), text))
        if candidates:
            return min(candidates, key=lambda t: t[0])[1]
        return ""

    # Search below first, fall back to above
    below = fitz.Rect(img_bbox.x0, img_bbox.y1, img_bbox.x1, img_bbox.y1 + search_margin)
    caption = _closest(below)
    if caption:
        return caption

    above = fitz.Rect(img_bbox.x0, img_bbox.y0 - search_margin, img_bbox.x1, img_bbox.y0)
    return _closest(above)


def extract_captions_from_pdf(filepath: str) -> List[Dict[str, Any]]:
    """Extract proximity-based image captions from a PDF.

    Returns a list of dicts ordered by (page, figure_index):
        {
            "page": int,           # 1-based
            "figure_index": int,   # 0-based within the page
            "caption": str,        # may be empty string
            "bbox": list[float],   # [x0, y0, x1, y1] normalised to [0, 1]
        }
    """
    results: List[Dict[str, Any]] = []
    doc = fitz.open(filepath)

    try:
        for page_num, page in enumerate(doc):
            W, H = float(page.rect.width), float(page.rect.height)
            figure_index = 0

            for img_info in page.get_images(full=True):
                xref = img_info[0]
                try:
                    rects = page.get_image_rects(xref)
                    if not rects:
                        continue
                    img_rect = rects[0]

                    if img_rect.width * img_rect.height < _MIN_IMAGE_AREA:
                        continue  # skip decorative images

                    caption = _find_caption_near_image(page, img_rect)
                    results.append(
                        {
                            "page": page_num + 1,
                            "figure_index": figure_index,
                            "caption": caption,
                            "bbox": [
                                round(img_rect.x0 / W, 4),
                                round(img_rect.y0 / H, 4),
                                round(img_rect.x1 / W, 4),
                                round(img_rect.y1 / H, 4),
                            ],
                        }
                    )
                    figure_index += 1

                except Exception as exc:
                    logger.warning(
                        "Skipping image xref=%s on page %s: %s", xref, page_num + 1, exc
                    )
    finally:
        doc.close()

    return results


# ── 2. OCR fallback ──────────────────────────────────────────────────────────

def _ocr_caption(image_bytes: bytes) -> str:
    """Attempt OCR via pytesseract; returns empty string if unavailable."""
    try:
        from PIL import Image
        import pytesseract
    except Exception:
        return ""

    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        text = pytesseract.image_to_string(img).strip()
        return (text[:500] + "...") if len(text) > 500 else text
    except Exception as exc:
        logger.debug("OCR failed: %s", exc)
        return ""


# ── 3. Optional OpenAI GPT-4o-mini vision hook ───────────────────────────────

def _openai_caption(image_bytes: bytes) -> str:
    """Call OpenAI Chat Completions vision API; returns empty string on any failure."""
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        return ""

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=120,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64}",
                                "detail": "low",
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Describe this figure or diagram in one concise sentence "
                                "suitable for use as a search index caption."
                            ),
                        },
                    ],
                }
            ],
        )
        return response.choices[0].message.content.strip()

   except Exception as exc:
        logger.warning(
            "OpenAI vision caption failed — falling back to OCR/placeholder. "
            "This may be a transient API error (rate-limit, timeout). Error: %s",
            exc,
            exc_info=True,
        )
        return ""


# ── Public API ───────────────────────────────────────────────────────────────

def caption_image(
    image_bytes: "bytes | List[bytes]",
    page: "int | List[int] | None" = None,
) -> "str | List[str]":
    """Generate a caption for a single image or a batch of images.

    Resolution order:
      1. Configured VLM provider (set VISION_PROVIDER in .env)
      2. Local OCR via pytesseract
      3. Placeholder string with page number and dimensions
    """
    if isinstance(image_bytes, list):
        pages = (
            page if isinstance(page, list)
            else ([page] * len(image_bytes) if page is not None else [None] * len(image_bytes))
        )
        return [caption_image(img, pg) for img, pg in zip(image_bytes, pages)]

    # Strategy: try the configured VLM provider
    provider = get_vision_provider(getattr(settings, "VISION_PROVIDER", None))
    if provider is not None:
        result = provider.caption(image_bytes)
        if result:
            return result

    # Fallback 1: local OCR
    ocr = _ocr_caption(image_bytes)
    if ocr:
        return ocr

    # Fallback 2: placeholder
    try:
        pix = fitz.Pixmap(image_bytes)
        dims = f"{pix.width}x{pix.height} px"
    except Exception:
        dims = "unknown size"

    return f"Figure on page {page} ({dims})." if page else f"Figure ({dims})."
    # Placeholder for provider-based captioning (e.g., OpenAI / LLaVA hooks)
    provider = getattr(settings, "VISION_PROVIDER", None)

    if provider == "openai":
        caption = _openai_caption(image_bytes)
        if caption:
            return caption

    ocr = _ocr_caption(image_bytes)
    if ocr:
        return ocr

    # Derive dimensions for the placeholder
    try:
        pix = fitz.Pixmap(image_bytes)
        dims = f"{pix.width}x{pix.height} px"
    except Exception:
        dims = "unknown size"

    return f"Figure on page {page} ({dims})." if page else f"Figure ({dims})."


def generate_captions_for_chunks(chunks: List[Dict[str, Any]]) -> None:
    """Mutate image chunks in-place: fill empty ``text`` with a caption.

    Called by vectorstore.store_chunks() before embedding.
    Proximity-based captions should already be written into chunk["image_caption"]
    by document_ingestion.ingest_document() before this point.
    This function handles the OCR / placeholder fallback for any remaining gaps.
    """
    for chunk in chunks:
        if not chunk.get("image_bytes"):
            continue
        if chunk.get("text", "").strip():
            continue  # already captioned by proximity pass

        try:
            # Use pre-extracted proximity caption if available
            caption = chunk.get("image_caption") or caption_image(
                chunk["image_bytes"], page=chunk.get("page")
            )
            chunk["text"] = caption
            chunk["is_image"] = True
            chunk["image_caption"] = caption
        except Exception as exc:
            page = chunk.get("page", "?")
            logger.warning(
                "Caption generation failed for image on page %s — image_bytes will be "
                "permanently discarded. This may indicate a transient network error "
                "(e.g. API rate-limit or timeout). If this repeats, check your VLM "
                "provider configuration. Error: %s",
                page,
                exc,
                exc_info=True,
            )
            chunk["is_image"] = True
            fallback = f"Image on page {page}"
            chunk.setdefault("text", fallback)
            chunk["image_caption"] = chunk["text"]
        finally:
            # Always strip raw bytes — never serialise them into ChromaDB
            chunk.pop("image_bytes", None)
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
from io import BytesIO
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global availability flag for OCR dependencies to avoid repetitive runtime overhead
try:
    from PIL import Image
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


def _ocr_caption(image_bytes: bytes) -> str:
    """Try to produce a caption using pytesseract OCR; returns empty string if not available."""
    if not HAS_OCR:
        return ""

    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        text = pytesseract.image_to_string(img)
        text = text.strip()
        return text
    except Exception as e:
        logger.debug(f"OCR failed: {e}")
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
        logger.debug("OpenAI vision caption failed: %s", exc)
        return ""


# ── Public API ───────────────────────────────────────────────────────────────

def caption_image(image_bytes: bytes, page: Optional[int] = None) -> str:
    """Generate a caption for a single image (bytes).

    Resolution order: OpenAI (if configured) → OCR → placeholder.
    """
def caption_image(image_bytes: bytes | List[bytes], page: int | List[int] | None = None) -> str | List[str]:
    """Generate a caption for a single image or a batch of images.

    Order of operations:
    - If a list of image bytes is passed, returns a list of captions.
    - If an external VLM provider is configured, attempt to call it.
    - Fall back to local OCR (pytesseract) if available.
    - Otherwise return a simple placeholder caption including the page number.
    """
    if isinstance(image_bytes, list):
        pages = page if isinstance(page, list) else ([page] * len(image_bytes) if page is not None else [None] * len(image_bytes))
        return [caption_image(img, pg) for img, pg in zip(image_bytes, pages)]

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
            logger.debug("Failed to caption image chunk: %s", exc)
            chunk["is_image"] = True
            fallback = f"Image on page {chunk.get('page', '?')}"
            chunk.setdefault("text", fallback)
            chunk["image_caption"] = chunk["text"]
        finally:
            # Always strip raw bytes — never serialise them into ChromaDB
            chunk.pop("image_bytes", None)

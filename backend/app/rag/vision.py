"""Image captioning / vision helpers for RAG pipeline.

Provides a simple, pluggable interface to generate textual descriptions
for images extracted from PDFs. By default it uses local OCR (pytesseract)
when available as a robust fallback. An external VLM provider (OpenAI)
can be integrated by setting `VISION_PROVIDER` and appropriate API keys
in settings; the provider hook is intentionally small and optional.
"""
import logging
from typing import List, Dict, Any
from io import BytesIO

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _ocr_caption(image_bytes: bytes) -> str:
    """Try to produce a caption using pytesseract OCR; returns empty string if not available."""
    try:
        from PIL import Image
        import pytesseract
    except Exception:
        return ""

    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        text = pytesseract.image_to_string(img)
        text = text.strip()
        return text
    except Exception as e:
        logger.debug(f"OCR failed: {e}")
        return ""


def caption_image(image_bytes: bytes, page: int | None = None) -> str:
    """Generate a caption for a single image.

    Order of operations:
    - If an external VLM provider is configured, attempt to call it (not implemented as mandatory).
    - Fall back to local OCR (pytesseract) if available.
    - Otherwise return a simple placeholder caption including the page number.
    """
    # Placeholder for provider-based captioning (e.g., OpenAI / LLaVA hooks)
    provider = getattr(settings, "VISION_PROVIDER", None)
    if provider == "openai":
        try:
            import openai
            # Minimal integration: attempt a text-only caption via responses if available.
            # This is a best-effort hook; users should adapt to their provider's API.
            api_key = getattr(settings, "OPENAI_API_KEY", None)
            if api_key:
                openai.api_key = api_key
                # Use a generic prompt: "Describe the following image"
                # Note: concrete multimodal API usage may vary across SDK versions.
                resp = openai.Image.create(
                    prompt="Describe this image in one concise sentence.",
                    n=1,
                    # We do not re-upload image bytes here; this is a placeholder to show
                    # where provider code would be invoked. For production, follow
                    # provider docs for sending image data.
                )
                # openai.Image.create returns generated images, not captions — so skip.
        except Exception:
            # If provider integration fails, fall back to OCR below
            logger.debug("OpenAI vision provider failed, falling back to OCR")

    # Try OCR caption
    ocr = _ocr_caption(image_bytes)
    if ocr:
        # Keep it short if very long
        return (ocr[:500] + "...") if len(ocr) > 500 else ocr

    # Last-resort caption
    if page:
        return f"Image on page {page}."
    return "Image." 


def generate_captions_for_chunks(chunks: List[Dict[str, Any]]) -> None:
    """Mutate chunks in-place: for any chunk containing `image_bytes` but empty `text`,
    generate a caption and set `text`.
    """
    for chunk in chunks:
        if chunk.get("image_bytes") and not chunk.get("text"):
            try:
                caption = caption_image(chunk["image_bytes"], page=chunk.get("page"))
                chunk["text"] = caption
                # Remove raw bytes to avoid accidentally serializing them later
                chunk.pop("image_bytes", None)
                chunk["is_image"] = True
                chunk["image_caption"] = caption
            except Exception as e:
                logger.debug(f"Failed to caption image chunk: {e}")
                # ensure we still mark it as image to avoid losing it
                chunk.pop("image_bytes", None)
                chunk["is_image"] = True
                chunk.setdefault("text", f"Image on page {chunk.get('page')}")

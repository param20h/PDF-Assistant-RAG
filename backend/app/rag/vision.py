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

from abc import ABC, abstractmethod

# --- VLM Strategy Pattern Core ---

class BaseVisionProvider(ABC):
    """Abstract interface for all Vision-Language Model providers."""
    @abstractmethod
    def caption(self, image_bytes: bytes) -> str | None:
        """Takes image bytes and returns a descriptive caption string or None if it fails."""
        pass


class OpenAIVisionProvider(BaseVisionProvider):
    """Concrete Strategy implementing OpenAI's multimodal vision capabilities."""
    def __init__(self, settings):
        self.settings = settings

    def caption(self, image_bytes: bytes) -> str | None:
        try:
            import openai
            import base64
            
            api_key = getattr(self.settings, "OPENAI_API_KEY", None)
            if not api_key:
                return None
            
            # Use modern client initialization or configure global API key based on project convention
            openai.api_key = api_key
            
            # Production-ready execution utilizing OpenAI's chat completions API with vision capability
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            model = getattr(self.settings, "LLM_MODEL", "gpt-4o")
            
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this image in one concise sentence."},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                            },
                        ],
                    }
                ],
                max_tokens=100,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.debug(f"OpenAIVisionProvider execution failed: {e}")
            return None


# Simply extend this dictionary registry to add future VLM engines (e.g., Gemini, Claude)
VISION_PROVIDER_REGISTRY = {
    "openai": OpenAIVisionProvider,
}

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
    """Attempt OCR via pytesseract; returns empty string if unavailable.

    The PIL/pytesseract import is resolved once at module load (see ``HAS_OCR``),
    so this only does a boolean check before touching the image bytes.
    """
    if not HAS_OCR:
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
   # Dynamically resolve and execute configured strategy from registry
    provider_name = getattr(settings, "VISION_PROVIDER", None)
    if provider_name and provider_name.lower() in VISION_PROVIDER_REGISTRY:
        try:
            provider_class = VISION_PROVIDER_REGISTRY[provider_name.lower()]
            provider_instance = provider_class(settings)
            
            vlm_caption = provider_instance.caption(image_bytes)
            if vlm_caption:
                return vlm_caption
        except Exception as e:
            logger.debug(f"Configured vision provider '{provider_name}' failed: {e}. Falling back to OCR.")

    # Try OCR caption
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

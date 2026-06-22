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

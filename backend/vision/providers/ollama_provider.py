"""Ollama / LLaVA local Vision provider.
Activated when VISION_PROVIDER=ollama. No API key needed.
Make sure the model is pulled first: ollama pull llava
"""
import base64
import logging

from app.config import get_settings
from app.vision.base import BaseVisionProvider
from app.vision.registry import register_provider

logger = logging.getLogger(__name__)
settings = get_settings()

_CAPTION_PROMPT = (
    "Describe this figure or diagram in one concise sentence "
    "suitable for use as a search index caption."
)


class OllamaVisionProvider(BaseVisionProvider):

    def __init__(self) -> None:
        self._base_url: str = (
            getattr(settings, "OLLAMA_BASE_URL", None) or "http://localhost:11434"
        ).rstrip("/")
        self._model: str = getattr(settings, "VISION_MODEL", None) or "llava"

    def caption(self, image_bytes: bytes) -> str:
        try:
            import httpx
        except ImportError:
            logger.error("Run: pip install httpx")
            return ""

        try:
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            response = httpx.post(
                f"{self._base_url}/api/generate",
                json={"model": self._model, "prompt": _CAPTION_PROMPT, "images": [b64], "stream": False},
                timeout=60.0,
            )
            response.raise_for_status()
            text = response.json().get("response", "")
            return text.strip() if text else ""
        except Exception as exc:
            logger.debug("Ollama vision caption failed: %s", exc)
            return ""


register_provider("ollama", OllamaVisionProvider)
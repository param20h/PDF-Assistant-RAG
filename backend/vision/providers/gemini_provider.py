"""Google Gemini Vision provider.
Activated when VISION_PROVIDER=gemini and GOOGLE_API_KEY is set.
"""
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


class GeminiVisionProvider(BaseVisionProvider):

    def __init__(self) -> None:
        self._api_key: str = getattr(settings, "GOOGLE_API_KEY", "")
        self._model: str = getattr(settings, "VISION_MODEL", None) or "gemini-1.5-flash"
        if not self._api_key:
            raise ValueError(
                "GOOGLE_API_KEY must be set when VISION_PROVIDER=gemini."
            )

    def caption(self, image_bytes: bytes) -> str:
        try:
            import google.generativeai as genai
        except ImportError:
            logger.error("Run: pip install google-generativeai")
            return ""

        try:
            from io import BytesIO
            import PIL.Image
            genai.configure(api_key=self._api_key)
            model = genai.GenerativeModel(self._model)
            image = PIL.Image.open(BytesIO(image_bytes))
            response = model.generate_content([_CAPTION_PROMPT, image])
            text = getattr(response, "text", None)
            return text.strip() if text else ""
        except Exception as exc:
            logger.debug("Gemini vision caption failed: %s", exc)
            return ""


register_provider("gemini", GeminiVisionProvider)
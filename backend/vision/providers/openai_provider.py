"""OpenAI GPT-4o-mini Vision provider.
Activated when VISION_PROVIDER=openai and OPENAI_API_KEY is set.
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


class OpenAIVisionProvider(BaseVisionProvider):

    def __init__(self) -> None:
        self._api_key: str = getattr(settings, "OPENAI_API_KEY", "")
        self._model: str = getattr(settings, "VISION_MODEL", None) or "gpt-4o-mini"
        if not self._api_key:
            raise ValueError(
                "OPENAI_API_KEY must be set when VISION_PROVIDER=openai."
            )

    def caption(self, image_bytes: bytes) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            logger.error("Run: pip install openai")
            return ""

        try:
            client = OpenAI(api_key=self._api_key)
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            response = client.chat.completions.create(
                model=self._model,
                max_tokens=120,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "low"}},
                        {"type": "text", "text": _CAPTION_PROMPT},
                    ],
                }],
            )
            choices = response.choices
            if not choices:
                return ""
            content = choices[0].message.content
            return content.strip() if content else ""
        except Exception as exc:
            logger.debug("OpenAI vision caption failed: %s", exc)
            return ""


register_provider("openai", OpenAIVisionProvider)
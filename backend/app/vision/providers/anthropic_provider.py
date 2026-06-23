"""Anthropic Claude Vision provider.
Activated when VISION_PROVIDER=anthropic and ANTHROPIC_API_KEY is set.
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


class AnthropicVisionProvider(BaseVisionProvider):

    def __init__(self) -> None:
        self._api_key: str = getattr(settings, "ANTHROPIC_API_KEY", "")
        self._model: str = getattr(settings, "VISION_MODEL", None) or "claude-3-haiku-20240307"
        if not self._api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY must be set when VISION_PROVIDER=anthropic."
            )

    def caption(self, image_bytes: bytes) -> str:
        try:
            import anthropic
        except ImportError:
            logger.error("Run: pip install anthropic")
            return ""

        try:
            client = anthropic.Anthropic(api_key=self._api_key)
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            message = client.messages.create(
                model=self._model,
                max_tokens=120,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                        {"type": "text", "text": _CAPTION_PROMPT},
                    ],
                }],
            )
            content = message.content
            if not content:
                return ""
            text_block = next((b for b in content if getattr(b, "type", None) == "text"), None)
            return text_block.text.strip() if text_block else ""
        except Exception as exc:
            logger.debug("Anthropic vision caption failed: %s", exc)
            return ""


register_provider("anthropic", AnthropicVisionProvider)
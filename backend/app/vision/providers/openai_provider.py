"""OpenAI GPT-4o-mini based vision captioning provider."""
import base64
import logging
from typing import Optional

from app.config import get_settings
from app.vision.base import BaseVisionProvider

logger = logging.getLogger(__name__)


class OpenAIVisionProvider(BaseVisionProvider):
    """Captions images using OpenAI's Chat Completions vision API.

    Requires ``VISION_PROVIDER=openai`` and ``OPENAI_API_KEY`` to be set
    in settings; otherwise ``is_available`` reports ``False`` and the
    caller should fall through to the next provider.
    """

    name = "openai"

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def is_available(self) -> bool:
        provider = getattr(self._settings, "VISION_PROVIDER", None)
        api_key = getattr(self._settings, "OPENAI_API_KEY", None)
        return provider == "openai" and bool(api_key)

    def caption(self, image_bytes: bytes, page: Optional[int] = None) -> str:
        if not self.is_available:
            return ""

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._settings.OPENAI_API_KEY)
            b64 = base64.b64encode(image_bytes).decode("utf-8")

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=150,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe this image in one concise sentence.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64}",
                                },
                            },
                        ],
                    }
                ],
            )

            caption_text = response.choices[0].message.content
            return caption_text.strip() if caption_text else ""

        except Exception as exc:
            logger.warning("OpenAI vision provider failed: %s", exc)
            return ""
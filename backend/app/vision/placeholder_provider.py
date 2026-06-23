"""Placeholder vision provider — guaranteed non-empty fallback caption."""
import logging
from typing import Optional

from app.vision.base import BaseVisionProvider

logger = logging.getLogger(__name__)


class PlaceholderVisionProvider(BaseVisionProvider):
    """Always-available fallback that returns a generic figure caption.

    Used as the last link in the provider chain so callers always get a
    non-empty string even when no real captioning backend is configured
    or every other provider failed.
    """

    name = "placeholder"

    @property
    def is_available(self) -> bool:
        return True

    def caption(self, image_bytes: bytes, page: Optional[int] = None) -> str:
        dims = self._dimensions(image_bytes)
        if page:
            return f"Figure on page {page} ({dims})."
        return f"Figure ({dims})."

    @staticmethod
    def _dimensions(image_bytes: bytes) -> str:
        try:
            import fitz  # PyMuPDF

            pix = fitz.Pixmap(image_bytes)
            return f"{pix.width}x{pix.height} px"
        except Exception:
            return "unknown size"
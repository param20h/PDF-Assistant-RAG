"""Abstract base class that every VLM provider must implement."""
from abc import ABC, abstractmethod


class BaseVisionProvider(ABC):
    """Strategy interface for Vision-Language Model providers."""

    @abstractmethod
    def caption(self, image_bytes: bytes) -> str:
        """Generate a one-sentence caption for the given image.

        Returns a non-empty string, or empty string on failure (so caller can fall back).
        """
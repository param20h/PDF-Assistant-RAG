"""Vision package: pluggable VLM provider strategy for image captioning."""
from app.vision.registry import get_vision_provider, register_provider
from app.vision.base import BaseVisionProvider

__all__ = ["BaseVisionProvider", "get_vision_provider", "register_provider"]
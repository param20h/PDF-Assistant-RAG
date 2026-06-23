"""Provider registry for VLM strategy lookup."""
import logging
from typing import Dict, Optional, Type

from app.vision.base import BaseVisionProvider

logger = logging.getLogger(__name__)

_REGISTRY: Dict[str, Type[BaseVisionProvider]] = {}


def register_provider(name: str, cls: Type[BaseVisionProvider]) -> None:
    _REGISTRY[name.lower()] = cls
    logger.debug("Registered VLM provider: %s → %s", name, cls.__name__)


def get_vision_provider(name: Optional[str]) -> Optional[BaseVisionProvider]:
    if not name:
        return None

    cls = _REGISTRY.get(name.lower())
    if cls is None:
        logger.warning(
            "Unknown VISION_PROVIDER=%r. Available: %s",
            name,
            list(_REGISTRY.keys()) or ["(none)"],
        )
        return None

    try:
        return cls()
    except Exception as exc:
        logger.error("Failed to instantiate VLM provider %r: %s", name, exc)
        return None
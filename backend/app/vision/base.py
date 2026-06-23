"""Abstract base class for image-captioning vision providers.

A ``BaseVisionProvider`` turns raw image bytes into a short text caption.
Concrete providers (OpenAI vision, local OCR, placeholder) implement
``caption()`` and report their own availability via ``is_available``.

This abstraction lets the RAG pipeline try providers in priority order
(e.g. OpenAI → OCR → placeholder) without the call site needing to know
which backend actually produced the caption.
"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseVisionProvider(ABC):
    """Common interface every vision/captioning backend must implement."""

    #: Short machine-readable name (e.g. "openai", "ocr", "placeholder").
    #: Subclasses should override this.
    name: str = "base"

    @property
    def is_available(self) -> bool:
        """Whether this provider is usable in the current environment.

        Default implementation is permissive (always available); providers
        that depend on optional packages or API keys should override this
        to report ``False`` when their dependency/config is missing, so
        callers can skip straight to the next provider in the chain.
        """
        return True

    @abstractmethod
    def caption(self, image_bytes: bytes, page: Optional[int] = None) -> str:
        """Return a short caption for ``image_bytes``.

        Implementations must never raise: on any internal failure they
        should return ``""`` so the caller can fall through to the next
        provider in the chain. ``page`` is optional 1-based page context
        that providers may use to build a placeholder caption.
        """
        raise NotImplementedError
"""
Optional LangSmith tracing helpers for the RAG pipeline.
Safe to import even when LangSmith is not installed or configured.
"""
import logging
import os
from functools import wraps
from typing import Any, Callable, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

from abc import ABC, abstractmethod

# 1. Base Class Strategy Interface
class BaseTracingProvider(ABC):
    @abstractmethod
    def trace_call(
        self,
        name: str,
        fn: Callable[..., Any],
        *args: Any,
        run_type: str = "chain",
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        pass


# 2. Refactored LangSmith Implementation
class LangSmithProvider(BaseTracingProvider):
    def __init__(self):
        try:
            from langsmith import traceable as _langsmith_traceable
            self._traceable = _langsmith_traceable
        except Exception:
            self._traceable = None
        self.enabled = self._configure()

    def _configure(self) -> bool:
        # Check if the global tracing provider setting matches this provider
        provider_setting = getattr(settings, "TRACING_PROVIDER", "none").lower()
        if provider_setting != "langsmith":
            return False

        if not settings.LANGSMITH_API_KEY:
            logger.warning("LangSmith tracing enabled but LANGSMITH_API_KEY is not set; tracing disabled.")
            return False

        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
        os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
        os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
        return self._traceable is not None

    def trace_call(self, name, fn, *args, run_type="chain", metadata=None, **kwargs):
        if not self.enabled or self._traceable is None:
            return fn(*args, **kwargs)

        sanitized = {k: v for k, v in (metadata or {}).items() if v is not None}
        try:
            decorator = self._traceable(name=name, run_type=run_type, metadata=sanitized or None)
        except TypeError:
            decorator = self._traceable(name=name, run_type=run_type)

        return decorator(fn)(*args, **kwargs)


# 3. Fallback/No-Op Provider for "none" or alternative defaults
class NoOpProvider(BaseTracingProvider):
    def trace_call(self, name, fn, *args, run_type="chain", metadata=None, **kwargs):
        return fn(*args, **kwargs)


# 4. Factory Initialization
def _get_active_provider() -> BaseTracingProvider:
    provider_setting = getattr(settings, "TRACING_PROVIDER", "none").lower()
    if provider_setting == "langsmith":
        return LangSmithProvider()
    # Note: You can easily plug in LangfuseProvider here later!
    return NoOpProvider()

_active_provider = _get_active_provider()


def _sanitize_metadata(metadata: Optional[dict[str, Any]]) -> dict[str, Any]:
    return {key: value for key, value in (metadata or {}).items() if value is not None}


def _build_traceable(name: str, run_type: str, metadata: Optional[dict[str, Any]] = None):
    """Build a LangSmith traceable decorator safely across versions."""
    if _langsmith_traceable is None:
        return None

    sanitized = _sanitize_metadata(metadata)
    try:
        return _langsmith_traceable(
            name=name,
            run_type=run_type,
            metadata=sanitized or None,
        )
    except TypeError:
        return _langsmith_traceable(name=name, run_type=run_type)


def trace_call(
    name: str,
    fn: Callable[..., Any],
    *args: Any,
    run_type: str = "chain",
    metadata: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> Any:
    """Execute a callable routing to the configured monitoring provider."""
    return _active_provider.trace_call(
        name, fn, *args, run_type=run_type, metadata=metadata, **kwargs
    )


def trace_function(
    name: str,
    *,
    run_type: str = "chain",
    metadata_factory: Optional[Callable[..., dict[str, Any]]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator wrapper that becomes a no-op when LangSmith is disabled."""
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            metadata = metadata_factory(*args, **kwargs) if metadata_factory else None
            return trace_call(
                name,
                fn,
                *args,
                run_type=run_type,
                metadata=metadata,
                **kwargs,
            )

        return wrapped

    return decorator

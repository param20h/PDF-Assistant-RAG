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

try:
    from langsmith import traceable as _langsmith_traceable
except Exception:  # pragma: no cover - optional dependency safety
    _langsmith_traceable = None


def configure_langsmith() -> bool:
    """Configure LangSmith environment variables when tracing is enabled."""
    if not settings.LANGSMITH_TRACING:
        return False

    if not settings.LANGSMITH_API_KEY:
        logger.warning("LangSmith tracing enabled but LANGSMITH_API_KEY is not set; tracing disabled.")
        return False

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
    return _langsmith_traceable is not None


LANGSMITH_ENABLED = configure_langsmith()


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
    """Execute a callable with LangSmith tracing when available."""
    if not LANGSMITH_ENABLED:
        return fn(*args, **kwargs)

    decorator = _build_traceable(name, run_type, metadata)
    if decorator is None:
        return fn(*args, **kwargs)

    traced_fn = decorator(fn)
    return traced_fn(*args, **kwargs)


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

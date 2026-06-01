"""Prometheus instrumentation for the FastAPI application."""

import sys

try:
    import resource
except ImportError:  # pragma: no cover - resource is unavailable on some platforms.
    resource = None

from fastapi import FastAPI
from prometheus_client import Gauge
from prometheus_fastapi_instrumentator import Instrumentator

APP_PROCESS_RSS_BYTES = Gauge(
    "app_process_resident_memory_bytes",
    "Resident memory used by the backend process in bytes.",
)


def _get_process_rss_bytes() -> float:
    if resource is None:
        return 0.0

    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return float(usage)
    return float(usage * 1024)


APP_PROCESS_RSS_BYTES.set_function(_get_process_rss_bytes)


def setup_prometheus_metrics(app: FastAPI) -> Instrumentator:
    """Expose process and HTTP metrics on ``/metrics`` for Prometheus."""
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics"],
    )
    instrumentator.instrument(app).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
    )
    app.state.prometheus_instrumentator = instrumentator
    return instrumentator

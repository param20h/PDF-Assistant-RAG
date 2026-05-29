"""
Runtime metrics helpers for lightweight operational statistics.
"""
from threading import Lock


_metrics_lock = Lock()
_query_count = 0
_query_response_time_total_ms = 0.0


def record_query_response_time(duration_seconds: float) -> None:
    """Record one completed query response duration."""
    global _query_count, _query_response_time_total_ms

    duration_ms = max(duration_seconds, 0) * 1000
    with _metrics_lock:
        _query_count += 1
        _query_response_time_total_ms += duration_ms


def get_query_metrics() -> dict[str, float | int]:
    """Return aggregate query metrics for the current process lifetime."""
    with _metrics_lock:
        average_ms = (
            _query_response_time_total_ms / _query_count
            if _query_count
            else 0.0
        )
        return {
            "query_count": _query_count,
            "average_query_response_time_ms": round(average_ms, 2),
        }

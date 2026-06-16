"""
Deep health check endpoint — verifies DB, Redis, Celery, and ChromaDB.

GET /api/v1/health/status
- No authentication required (monitoring tools must reach it freely).
- Never raises a 5xx — always returns 200 with per-component status so
  load balancers and uptime monitors can parse the JSON body.
"""
import logging
import time
from typing import Dict, Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


def _check_database() -> Dict[str, Any]:
    """Ping the configured database (SQLite or PostgreSQL)."""
    start = time.perf_counter()
    try:
        from app.database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {"status": "up", "latency_ms": latency_ms}
    except Exception as exc:
        logger.warning("DB health check failed: %s", exc)
        return {"status": "down", "error": str(exc)[:120]}


def _check_redis() -> Dict[str, Any]:
    """Ping the Redis broker used by Celery and the response cache."""
    start = time.perf_counter()
    try:
        from app.cache import _get_redis
        r = _get_redis()
        if r is None:
            return {"status": "unavailable", "detail": "REDIS_URL not configured"}
        r.ping()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {"status": "up", "latency_ms": latency_ms}
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        return {"status": "down", "error": str(exc)[:120]}


def _check_celery() -> Dict[str, Any]:
    """
    Verify at least one Celery worker is reachable via the inspect API.
    Uses a short timeout so the endpoint stays fast even when workers
    are offline.
    """
    start = time.perf_counter()
    try:
        from app.celery_app import celery_app

        inspector = celery_app.control.inspect(timeout=2.0)
        active = inspector.active()         # None if no workers respond
        ping = inspector.ping()

        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        if not ping:
            return {
                "status": "down",
                "detail": "No Celery workers responded to ping",
                "latency_ms": latency_ms,
            }

        worker_names = list(ping.keys())
        active_task_count = sum(
            len(tasks) for tasks in (active or {}).values()
        )
        return {
            "status": "up",
            "workers": len(worker_names),
            "worker_names": worker_names,
            "active_tasks": active_task_count,
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        logger.warning("Celery health check failed: %s", exc)
        return {"status": "down", "error": str(exc)[:120]}


def _check_chromadb() -> Dict[str, Any]:
    """Ping the ChromaDB vector store."""
    start = time.perf_counter()
    try:
        from app.rag.vectorstore import get_chroma_client
        client = get_chroma_client()
        client.heartbeat()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {"status": "up", "latency_ms": latency_ms}
    except Exception as exc:
        logger.warning("ChromaDB health check failed: %s", exc)
        return {"status": "down", "error": str(exc)[:120]}


@router.get(
    "/status",
    summary="Deep system health check",
    description=(
        "Returns connection status for PostgreSQL/SQLite, Redis, "
        "Celery workers, and ChromaDB. Always returns HTTP 200 — "
        "inspect the `overall` field to determine system health."
    ),
)
def health_status():
    """
    Deep health check — verifies all backend dependencies.

    Returns HTTP 200 always. Callers should inspect the ``overall`` field:
    - ``healthy``  — all components up.
    - ``degraded`` — one or more components down or unavailable.
    """
    checks = {
        "database": _check_database(),
        "redis":    _check_redis(),
        "celery":   _check_celery(),
        "chromadb": _check_chromadb(),
    }

    # overall is healthy only when every component is "up"
    all_up = all(
        v.get("status") == "up"
        for v in checks.values()
    )
    overall = "healthy" if all_up else "degraded"

    return JSONResponse(
        status_code=200,
        content={
            "overall": overall,
            "components": checks,
        },
    )

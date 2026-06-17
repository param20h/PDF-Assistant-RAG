"""Prometheus instrumentation for the FastAPI application."""

import sys

try:
    import resource
except ImportError:  # pragma: no cover - resource is unavailable on some platforms.
    resource = None

from fastapi import FastAPI
from prometheus_client import Gauge
from prometheus_fastapi_instrumentator import Instrumentator, routing
from starlette.routing import Match

# ── Workaround for FastAPI 0.135+ and prometheus-fastapi-instrumentator 8.0.0 ──
# Newer FastAPI versions include _IncludedRouter objects in app.routes which
# lack a '.path' attribute, causing AttributeErrors during instrumentation.
def _patched_get_route_name(scope, routes, route_name=None):
    """Safe version of _get_route_name that handles routes without a .path attribute."""
    for route in routes:
        try:
            match, child_scope = route.matches(scope)
        except Exception:
            continue

        if match == Match.FULL:
            # If we have a full match and the route has a path, use it and return early.
            # This matches Starlette's behavior where the first matching route wins.
            if hasattr(route, "path"):
                return route.path
        elif match == Match.PARTIAL and hasattr(route, "routes"):
            # Recursive call for nested routes (e.g. Mounts)
            route_name = _patched_get_route_name(child_scope, route.routes, route_name)
            if route_name:
                return route_name
    return route_name

routing._get_route_name = _patched_get_route_name

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


# ── Structured JSON Logging Implementation with Loguru ──

import os
import time
import uuid
import json
import logging
import contextvars
from loguru import logger
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import get_settings

# ── Context Variables for request-local structured logs ──
request_id_var = contextvars.ContextVar("request_id", default="")
user_id_var = contextvars.ContextVar("user_id", default="")
upload_filename_var = contextvars.ContextVar("upload_filename", default="")
upload_filesize_var = contextvars.ContextVar("upload_filesize", default=None)
query_text_var = contextvars.ContextVar("query_text", default="")
chunks_retrieved_var = contextvars.ContextVar("chunks_retrieved", default=None)


class InterceptHandler(logging.Handler):
    """Logs from Python standard logging are redirected to Loguru."""

    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def json_serializer(record):
    """Custom format function to serialize logs as clean JSON."""
    log_record = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }
    
    # Inject extra attributes (bound context, patch attributes)
    if record["extra"]:
        for key, val in record["extra"].items():
            if key != "serialized":
                log_record[key] = val
            
    # Include formatted exception if any
    if record["exception"]:
        exception = record["exception"]
        log_record["exception"] = f"{exception.type.__name__}: {exception.value}"
        
    record["extra"]["serialized"] = json.dumps(log_record)
    return "{extra[serialized]}\n"


def setup_logging():
    """Setup and configure Loguru logging framework."""
    settings = get_settings()
    
    # Determine log level
    log_level = settings.LOG_LEVEL
    if not log_level:
        log_level = "DEBUG" if settings.ENVIRONMENT == "development" else "INFO"
        
    # Remove default handlers
    logger.remove()
    
    # Configure global patcher to inject ContextVars into extra
    def patch_record(record):
        req_id = request_id_var.get()
        if req_id:
            record["extra"]["request_id"] = req_id
            
        u_id = user_id_var.get()
        if u_id:
            record["extra"]["user_id"] = u_id
            
        fn = upload_filename_var.get()
        if fn:
            record["extra"]["filename"] = fn
            
        fs = upload_filesize_var.get()
        if fs is not None:
            record["extra"]["file_size"] = fs
            
        q = query_text_var.get()
        if q:
            record["extra"]["query"] = q
            
        chunks = chunks_retrieved_var.get()
        if chunks is not None:
            record["extra"]["chunks_retrieved"] = chunks
            
    logger.configure(patcher=patch_record)
    
    # Add stdout handler
    logger.add(
        sys.stdout,
        format=json_serializer,
        level=log_level,
        backtrace=True,
        diagnose=True,
    )
    
    # Add file handler with rotation and retention
    os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)
    logger.add(
        settings.LOG_FILE,
        format=json_serializer,
        level=log_level,
        rotation="10 MB",
        retention="10 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )
    
    # Intercept standard library logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Redirect Uvicorn logs to loguru
    for name in ("uvicorn", "uvicorn.asgi", "uvicorn.access", "uvicorn.error"):
        logging_logger = logging.getLogger(name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False
        
    logger.info(f"Logging initialized with level: {log_level}, log file: {settings.LOG_FILE}")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to inject context variables and log HTTP requests in structured JSON format."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        
        # Unique Request ID per request
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        
        # Set request-local context variables
        token_req = request_id_var.set(request_id)
        token_user = user_id_var.set("")
        token_filename = upload_filename_var.set("")
        token_filesize = upload_filesize_var.set(None)
        token_query = query_text_var.set("")
        token_chunks = chunks_retrieved_var.set(None)
        
        # Also store on request state for reliable retrieval
        request.state.request_id = request_id
        request.state.user_id = ""
        request.state.filename = ""
        request.state.filesize = None
        request.state.query = ""
        request.state.chunks_retrieved = None

        try:
            response = await call_next(request)
        except Exception as exc:
            duration = time.perf_counter() - start_time
            # Log exception with request details
            logger.opt(exception=exc).error(
                f"HTTP request failed: {request.method} {request.url.path} - Exception: {str(exc)}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "response_time_ms": round(duration * 1000, 2),
                }
            )
            raise exc from None
        finally:
            duration = time.perf_counter() - start_time
            
            # Read state variables and set contextvars again in case they didn't propagate back
            u_id = getattr(request.state, "user_id", "")
            fn = getattr(request.state, "filename", "")
            fs = getattr(request.state, "filesize", None)
            q = getattr(request.state, "query", "")
            chunks = getattr(request.state, "chunks_retrieved", None)
            
            if u_id: user_id_var.set(u_id)
            if fn: upload_filename_var.set(fn)
            if fs is not None: upload_filesize_var.set(fs)
            if q: query_text_var.set(q)
            if chunks is not None: chunks_retrieved_var.set(chunks)
            
            # Log final response details
            # We don't log health check endpoints or metrics endpoints in standard INFO logs to reduce clutter,
            # but we can log them at DEBUG level.
            is_health_or_metrics = request.url.path in ("/api/health", "/health", "/metrics")
            log_fn = logger.debug if is_health_or_metrics else logger.info
            
            status_code = getattr(response, "status_code", 500)
            log_fn(
                f"HTTP request completed: {request.method} {request.url.path} - {status_code}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "response_time_ms": round(duration * 1000, 2),
                }
            )
            
            # Add X-Request-ID to response headers
            if response is not None:
                response.headers["X-Request-ID"] = request_id
                
            # Reset ContextVars to avoid leaking
            request_id_var.reset(token_req)
            user_id_var.reset(token_user)
            upload_filename_var.reset(token_filename)
            upload_filesize_var.reset(token_filesize)
            query_text_var.reset(token_query)
            chunks_retrieved_var.reset(token_chunks)
            
        return response


"""
FastAPI application entry point.
Mounts all routes, configures CORS, and serves the Next.js frontend build.
"""
import os
import uuid
import signal
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from app.security import verify_secure_sandbox_path
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.exceptions import AppException
from app.rate_limit import limiter
from app.database import init_db, get_db
from app.observability import setup_prometheus_metrics, setup_logging, StructuredLoggingMiddleware
from app.rag.vectorstore import get_chroma_client
from app.scheduler import start_scheduler, stop_scheduler
from app.routes.profile import router as profile_router
from app.routes.health import router as health_router

# Configure logging using loguru structured JSON logging
setup_logging()
from loguru import logger


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────
    app.state.is_shutting_down = False
    logger.info(f"Starting {settings.APP_NAME}")

    # Validate production settings
    try:
        settings.validate_production()
    except ValueError as e:
        logger.error("Configuration error: %s", e)
        raise

    # Create tables
    init_db()
    logger.info("Database initialized")

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

    # Pre-load embedding model (warm up)
    try:
        from app.rag.embeddings import get_embedding_model
        get_embedding_model()
        logger.info("Embedding model pre-loaded")
    except Exception as e:
        logger.warning(f"Failed to pre-load embedding model: {e}")

    yield

    # ── Graceful Shutdown ────────────────────────────
    logger.info("Shutdown signal received — draining in-flight requests")
    app.state.is_shutting_down = True
    # Give in-flight requests a short window to complete
    await asyncio.sleep(5)
    stop_scheduler()
    logger.info("Shutdown complete")


# ── Create App ───────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise Agentic RAG System — Upload PDFs and chat with AI",
    version="2.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter


# ── Request ID Middleware ─────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Global Exception Handlers ─────────────────────────
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded. Please try again later.",
                "details": {},
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = [
        {"field": " -> ".join(str(p) for p in e.get("loc", [])), "message": e.get("msg", "")}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": details},
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    if settings.DEBUG:
        raise
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {},
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


app.add_middleware(SlowAPIMiddleware)

# ── CORS (allow frontend dev server) ─────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info(f"CORS origins: {settings.cors_origins}")

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security-critical HTTP headers to every API response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'wasm-unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https:;"
        )
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)


# Request Body Size Limit Middleware
_MAX_BODY_BYTES = settings.MAX_REQUEST_BODY_SIZE_MB * 1024 * 1024


@app.middleware("http")
async def limit_request_body_size(request: Request, call_next):
    content_type = request.headers.get("content-type", "")
    if (
        request.method in ("POST", "PUT", "PATCH")
        and "multipart/form-data" not in content_type
    ):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "REQUEST_TOO_LARGE",
                        "message": f"Request body exceeds the {settings.MAX_REQUEST_BODY_SIZE_MB}MB limit",
                        "details": {},
                    }
                },
            )
    return await call_next(request)


# Add structured logging middleware as the outermost middleware
app.add_middleware(StructuredLoggingMiddleware)

# ── Mount API Routes ─────────────────────────────────
from app.routes.auth import router as auth_router
from app.routes.documents import router as documents_router
from app.routes.chat import router as chat_router
from app.routes.github import router as github_router
from app.routes.admin import router as admin_router
from app.routes.workspaces import router as workspaces_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(github_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(workspaces_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")

setup_prometheus_metrics(app)


# ── Health Check ─────────────────────────────────────
@app.get("/api/health")
def health_check():
    # Return 503 during graceful shutdown so load balancers stop routing
    if getattr(app.state, "is_shutting_down", False):
        return JSONResponse(
            status_code=503,
            content={"status": "shutting_down", "app": settings.APP_NAME},
        )
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "2.0.0",
    }

@app.get('/health')
def db_health():
    db_status = "down"
    chroma_status = "down"

    # --- DB check ---
    try:
        db = next(get_db())
        db.execute(select(1))
        db_status = "up"
    except SQLAlchemyError:
        db_status = "down"
    except Exception:
        db_status = "down"

    # --- Chroma check ---
    try:
        chroma = get_chroma_client()
        chroma.heartbeat()
        chroma_status = "up"
    except Exception:
        chroma_status = "down"

    if db_status == "up" and chroma_status == "up":
        overall_status = "healthy"
    elif db_status == "down" and chroma_status == "down":
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "chroma": chroma_status,
        "db": db_status
    }

# ── API Root ──────────────────────────────────────────
# Frontend is hosted separately on Vercel/Netlify.
# This backend serves only the API.
@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs": "/docs",
        "health": "/api/health",
    }

app.include_router(profile_router)

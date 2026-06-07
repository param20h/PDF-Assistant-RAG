"""
FastAPI application entry point.
Mounts all routes, configures CORS, and serves the Next.js frontend build.
"""
import os
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from app.security import verify_secure_sandbox_path
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.exceptions import AppException
from app.rate_limit import limiter
from app.database import init_db, get_db
from app.observability import setup_prometheus_metrics
from app.rag.vectorstore import get_chroma_client
from app.scheduler import start_scheduler, stop_scheduler
from app.routes.profile import router as profile_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


async def document_cleanup_job():
    """Background loop to periodically purge documents not accessed in 30 days."""
    import asyncio
    from datetime import datetime, timedelta, timezone
    logger.info("Starting document cleanup background job loop")
    while True:
        try:
            from app.database import SessionLocal
            from app.models import Document
            from app.rag.vectorstore import delete_document_chunks
            from sqlalchemy import or_
            
            db = SessionLocal()
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                expired_docs = db.query(Document).filter(
                    or_(
                        Document.last_accessed_at < cutoff,
                        Document.last_accessed_at.is_(None) & (Document.uploaded_at < cutoff)
                    )
                ).all()
                
                for doc in expired_docs:
                    logger.info(f"Auto-cleanup: Purging document {doc.id} ('{doc.original_name}') due to inactivity since {doc.last_accessed_at or doc.uploaded_at}")
                    
                    # Delete physical file
                    filepath = os.path.join(settings.UPLOAD_DIR, doc.user_id, doc.filename)
                    if os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                        except Exception as e:
                            logger.warning(f"Auto-cleanup: Failed to delete physical file {filepath}: {e}")
                    
                    # Delete vectors
                    try:
                        delete_document_chunks(document_id=doc.id, user_id=doc.user_id)
                    except Exception as e:
                        logger.warning(f"Auto-cleanup: Error deleting vectors for document {doc.id}: {e}")
                    
                    # Delete database record
                    db.delete(doc)
                
                db.commit()
                if expired_docs:
                    logger.info(f"Auto-cleanup: Purged {len(expired_docs)} documents.")
            except Exception as exc:
                logger.error(f"Auto-cleanup job encountered error: {exc}", exc_info=True)
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in document cleanup background loop: {e}", exc_info=True)
            
        # Run every 24 hours (86400 seconds)
        await asyncio.sleep(86400)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────
    logger.info(f"Starting {settings.APP_NAME}")

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

    # Start background cleanup task
    import asyncio
    cleanup_task = asyncio.create_task(document_cleanup_job())

    yield

    # ── Shutdown ─────────────────────────────────────
    stop_scheduler()
    logger.info("Shutting down")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning(f"Error cancelling cleanup task: {e}")


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

setup_prometheus_metrics(app)


# ── Health Check ─────────────────────────────────────
@app.get("/api/health")
def health_check():
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

    overall_status = "ok" if db_status == "up" and chroma_status == "up" else "degraded"
    return{
        "status": db_status,
        "chroma": chroma_status,
        "db": db_status
    }

# ── Serve Next.js Frontend (production) ──────────────
# In local development, frontend build is at ../../frontend/out relative to backend/app/main.py
# In Docker container (where app is copied to /app/app), frontend build is at /app/frontend/out (which is ../frontend/out relative to /app/app/main.py)
_local_build_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "out"))
_docker_build_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "out"))

if os.path.exists(_docker_build_dir):
    FRONTEND_BUILD_DIR = _docker_build_dir
else:
    FRONTEND_BUILD_DIR = _local_build_dir

if os.path.exists(FRONTEND_BUILD_DIR):
    # Serve static assets (JS, CSS, images)
    app.mount("/_next", StaticFiles(directory=os.path.join(FRONTEND_BUILD_DIR, "_next")), name="next_static")

    # Serve other static files if they exist
    static_dir = os.path.join(FRONTEND_BUILD_DIR, "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
    async def serve_frontend(full_path: str):
        """Serve Next.js static export — tries exact file, then .html, then index.html."""
        # Try exact file path
        file_path = os.path.join(FRONTEND_BUILD_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)

        # Try with .html extension
        html_path = os.path.join(FRONTEND_BUILD_DIR, f"{full_path}.html")
        if os.path.isfile(html_path):
            return FileResponse(html_path)

        # Try .txt for RSC payloads (Next.js uses .txt for RSC data)
        txt_path = os.path.join(FRONTEND_BUILD_DIR, f"{full_path}.txt")
        if os.path.isfile(txt_path):
            return FileResponse(txt_path)

        # Try as directory index
        index_path = os.path.join(FRONTEND_BUILD_DIR, full_path, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)

        # Fallback to root index.html (SPA routing)
        root_index = os.path.join(FRONTEND_BUILD_DIR, "index.html")
        if os.path.isfile(root_index):
            return FileResponse(root_index)

        return FileResponse(root_index) if os.path.exists(root_index) else {"error": "Not found"}
else:
    logger.info("No frontend build found — running in API-only mode")

    @app.get("/")
    def root():
        return {
            "message": f"Welcome to {settings.APP_NAME} API",
            "docs": "/docs",
            "health": "/api/health",
        }
app.include_router(profile_router)

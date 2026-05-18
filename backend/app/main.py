"""
FastAPI application entry point.
Mounts all routes, configures CORS, and serves the Next.js frontend build.
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


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

    yield

    # ── Shutdown ─────────────────────────────────────
    logger.info("Shutting down")


# ── Create App ───────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise Agentic RAG System — Upload PDFs and chat with AI",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS (allow frontend dev server) ─────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:7860", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount API Routes ─────────────────────────────────
from app.routes.auth import router as auth_router
from app.routes.documents import router as documents_router
from app.routes.chat import router as chat_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")


# ── Health Check ─────────────────────────────────────
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "2.0.0",
    }


# ── Serve Next.js Frontend (production) ──────────────
FRONTEND_BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "out")

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

"""
Application configuration via pydantic-settings.
All config is loaded from environment variables with sensible defaults.
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "Document AI Analyst"
    SECRET_KEY: str = "change-me-in-production-please"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:7860"

    # ── Database ─────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # ── Auth ─────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRY_MINUTES: int = 15
    JWT_REFRESH_EXPIRY_DAYS: int = 7
    GOOGLE_CLIENT_ID: str = ""

    # ── File Upload ──────────────────────────────────────
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_EXTENSIONS: set = {"pdf", "docx", "txt", "md"}
    ALLOWED_MIME_TYPES: dict = {
        ".pdf": ["application/pdf"],
        ".docx": [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/zip",
        ]
    }

    # ── RAG Pipeline ─────────────────────────────────────
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RETRIEVAL: int = 10
    TOP_K_RERANK: int = 5

    # ── Embeddings (local HuggingFace model) ─────────────
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # ── ChromaDB ─────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"

    # ── LLM (HuggingFace Inference API) ──────────────────
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")  # HuggingFace API token (set in .env)
    LLM_MODEL: str = "Qwen/Qwen2.5-72B-Instruct"
    LLM_MAX_NEW_TOKENS: int = 1024
    LLM_TEMPERATURE: float = 0.3
    SUMMARY_MAX_TOKENS: int = 512

    # ── Reranker ─────────────────────────────────────────
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    # ── Vision / Image captioning ─────────────────────
    VISION_PROVIDER: str | None = None  # e.g. 'openai'
    VISION_MODEL: str | None = None
    OPENAI_API_KEY: str = ""


    @property
    def cors_origins(self) -> list[str]:
        if self.ENVIRONMENT == "production":
            return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]
        return ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — loaded once on startup."""
    return Settings()

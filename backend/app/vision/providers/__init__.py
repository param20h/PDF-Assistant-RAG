"""Auto-registers all built-in providers on import."""
from app.vision.providers import (  # noqa: F401
    openai_provider,
    anthropic_provider,
    gemini_provider,
    ollama_provider,
)
"""Celery application configured for Redis-backed background jobs."""
from celery import Celery

from app.config import get_settings


settings = get_settings()

celery_app = Celery(
    "pdf_assistant_rag",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
)


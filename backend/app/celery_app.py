import os
from celery import Celery

# Initialize the Celery application instance
celery_app = Celery(
    "worker",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

# Optional configuration updates for reliable serialization
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)

# Tell Celery to discover background tasks dynamically to break circular loops
celery_app.autodiscover_tasks(["app"])
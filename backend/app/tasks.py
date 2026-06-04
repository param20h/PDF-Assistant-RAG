"""Celery tasks for document processing."""
from app.celery_app import celery_app
from app.services.document_ingestion import ingest_document


@celery_app.task(bind=True, name="app.tasks.process_document")
def process_document(
    self,
    document_id: str,
    filepath: str,
    original_name: str,
    user_id: str,
) -> dict[str, str]:
    """Run the RAG ingestion pipeline for a stored document."""
    ingest_document(
        document_id=document_id,
        filepath=filepath,
        original_name=original_name,
        user_id=user_id,
    )
    return {"document_id": document_id, "status": "completed"}


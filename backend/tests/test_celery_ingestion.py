import pytest
from unittest.mock import patch, MagicMock

# Core app imports
from app.models import Document
from app.tasks import process_document


def test_process_document_ingestion_pipeline(db_session):
    """
    Test that the Celery task updates document status from pending to completed
    by executing the layout-aware parser pipeline inside the active test database session.
    """

    # 1. SETUP: Create a mock document that starts as 'pending'
    test_doc = Document(
        id="test-doc-123",
        filename="sample.pdf",
        original_name="sample.pdf",
        status="pending",
        user_id="user-456",
    )
    db_session.add(test_doc)
    db_session.commit()

    # 2. ACT: Create a mock engine session factory context that yields our test db_session
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__enter__.return_value = db_session
    mock_session_factory.return_value = db_session

    # Patch the factory globally, and mock AdvancedPDFParser so no real PDF is parsed
    with patch("app.database.SessionLocal", mock_session_factory, create=True), \
         patch("app.services.document_ingestion.SessionLocal", mock_session_factory, create=True), \
         patch("app.services.layout_parser.AdvancedPDFParser") as mock_parser_cls:

        mock_parser = MagicMock()
        mock_parser_cls.return_value = mock_parser
        mock_parser.ingest_document.return_value = [
            {"text": "mock chunk 1", "page_number": 1, "type": "text_layout"},
        ]

        task_result = process_document.apply(
            kwargs={
                "document_id": "test-doc-123",
                "filepath": "/tmp/sample.pdf",
                "original_name": "sample.pdf",
                "user_id": "user-456",
            }
        )

        # 3. ASSERT: Verify the task metrics and status changes inside the session context
        assert task_result.status == "SUCCESS"

        # Query the database to verify the state update
        updated_doc = db_session.query(Document).filter_by(id="test-doc-123").first()
        assert updated_doc is not None
        assert updated_doc.status == "completed"
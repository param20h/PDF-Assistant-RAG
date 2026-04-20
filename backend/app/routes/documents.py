"""
Document management routes — upload, list, delete, and serve PDF files.
Background ingestion via FastAPI BackgroundTasks.
"""
import os
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Document
from app.schemas import DocumentResponse, DocumentListResponse
from app.auth import get_current_user
from app.config import get_settings
from app.rag.chunker import chunk_document, get_page_count
from app.rag.vectorstore import store_chunks, delete_document_chunks

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/documents", tags=["Documents"])


def _ingest_document(document_id: str, filepath: str, original_name: str, user_id: str):
    """
    Background task: chunk document, generate embeddings, store in ChromaDB.
    Updates document status in the database.
    """
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Document {document_id} not found for ingestion")
            return

        # Update status to processing
        doc.status = "processing"
        db.commit()

        # Get page count
        page_count = get_page_count(filepath)
        doc.page_count = page_count

        # Chunk the document
        chunks = chunk_document(filepath)

        if not chunks:
            doc.status = "failed"
            doc.error_message = "No text could be extracted from the document"
            db.commit()
            return

        # Store embeddings in ChromaDB
        chunk_count = store_chunks(
            chunks=chunks,
            document_id=document_id,
            filename=original_name,
            user_id=user_id,
        )

        # Update document record
        doc.chunk_count = chunk_count
        doc.status = "ready"
        db.commit()

        logger.info(f"Document {document_id} ingested: {page_count} pages, {chunk_count} chunks")

    except Exception as e:
        logger.error(f"Ingestion error for {document_id}: {e}")
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = "failed"
                doc.error_message = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a document for RAG processing."""
    # ── Validate file type ───────────────────────────
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '.{ext}' not supported. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    # ── Read and validate size ───────────────────────
    content = await file.read()
    file_size = len(content)

    if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB",
        )

    # ── Save file to disk ────────────────────────────
    user_dir = os.path.join(settings.UPLOAD_DIR, user.id)
    os.makedirs(user_dir, exist_ok=True)

    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(user_dir, stored_filename)

    with open(filepath, "wb") as f:
        f.write(content)

    # ── Create database record ───────────────────────
    document = Document(
        user_id=user.id,
        filename=stored_filename,
        original_name=file.filename,
        file_size=file_size,
        status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # ── Trigger background ingestion ─────────────────
    background_tasks.add_task(
        _ingest_document,
        document_id=document.id,
        filepath=filepath,
        original_name=file.filename,
        user_id=user.id,
    )

    return DocumentResponse.model_validate(document)


@router.get("/", response_model=DocumentListResponse)
def list_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents for the authenticated user."""
    docs = (
        db.query(Document)
        .filter(Document.user_id == user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific document's details."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user.id,
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse.model_validate(doc)


@router.get("/{document_id}/pdf")
def serve_pdf(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Serve the PDF file for the document viewer."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user.id,
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    filepath = os.path.join(settings.UPLOAD_DIR, user.id, doc.filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        filepath,
        media_type="application/pdf",
        filename=doc.original_name,
    )


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document and its vector embeddings."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user.id,
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from disk
    filepath = os.path.join(settings.UPLOAD_DIR, user.id, doc.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    # Delete vectors from ChromaDB
    try:
        delete_document_chunks(document_id=document_id, user_id=user.id)
    except Exception as e:
        logger.warning(f"Error deleting vectors: {e}")

    # Delete from database (cascades to chat messages)
    db.delete(doc)
    db.commit()

    return {"message": f"Document '{doc.original_name}' deleted successfully"}

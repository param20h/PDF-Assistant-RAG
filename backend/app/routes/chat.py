"""
Chat routes — ask questions with RAG, stream responses via SSE, manage history.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ChatMessage, Document
from app.schemas import ChatRequest, ChatResponse, ChatMessageResponse, ChatHistoryResponse, SourceChunk
from app.auth import get_current_user
from app.rag.agent import generate_answer, generate_answer_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/ask", response_model=ChatResponse)
def ask_question(
    payload: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ask a question with RAG retrieval (non-streaming)."""
    # Validate document exists if specified
    if payload.document_id:
        doc = db.query(Document).filter(
            Document.id == payload.document_id,
            Document.user_id == user.id,
        ).first()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        if doc.status != "ready":
            raise HTTPException(
                status_code=400,
                detail=f"Document is still {doc.status}. Please wait for processing to complete.",
            )

    # Generate answer
    result = generate_answer(
        question=payload.question,
        user_id=user.id,
        document_id=payload.document_id,
    )

    # Save to chat history
    _save_message(db, user.id, payload.document_id, "user", payload.question)
    _save_message(db, user.id, payload.document_id, "assistant", result["answer"], result["sources"])

    return ChatResponse(
        answer=result["answer"],
        sources=[SourceChunk(**s) for s in result["sources"]],
        document_id=payload.document_id,
    )


@router.post("/ask/stream")
def ask_question_stream(
    payload: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ask a question with SSE streaming response."""
    # Validate document
    if payload.document_id:
        doc = db.query(Document).filter(
            Document.id == payload.document_id,
            Document.user_id == user.id,
        ).first()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        if doc.status != "ready":
            raise HTTPException(
                status_code=400,
                detail=f"Document is still {doc.status}. Please wait for processing to complete.",
            )

    # Save user message immediately
    _save_message(db, user.id, payload.document_id, "user", payload.question)

    # Stream response
    def event_stream():
        full_answer = ""
        sources = []

        for chunk in generate_answer_stream(
            question=payload.question,
            user_id=user.id,
            document_id=payload.document_id,
        ):
            yield chunk

            # Parse to accumulate full answer for history
            try:
                if chunk.startswith("data: "):
                    data = json.loads(chunk[6:].strip())
                    if data.get("type") == "token":
                        full_answer += data.get("data", "")
                    elif data.get("type") == "sources":
                        sources = data.get("data", [])
            except Exception:
                pass

        # Save assistant response to history
        from app.database import SessionLocal
        save_db = SessionLocal()
        try:
            _save_message(save_db, user.id, payload.document_id, "assistant", full_answer, sources)
        finally:
            save_db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history/{document_id}", response_model=ChatHistoryResponse)
def get_chat_history(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get chat history for a specific document."""
    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == user.id,
            ChatMessage.document_id == document_id,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    formatted = []
    for msg in messages:
        sources = []
        if msg.sources_json:
            try:
                sources = [SourceChunk(**s) for s in json.loads(msg.sources_json)]
            except Exception:
                pass

        formatted.append(ChatMessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            sources=sources,
            created_at=msg.created_at,
        ))

    return ChatHistoryResponse(messages=formatted, document_id=document_id)


@router.delete("/history/{document_id}")
def clear_chat_history(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear chat history for a specific document."""
    db.query(ChatMessage).filter(
        ChatMessage.user_id == user.id,
        ChatMessage.document_id == document_id,
    ).delete()
    db.commit()

    return {"message": "Chat history cleared"}


def _save_message(
    db: Session,
    user_id: str,
    document_id: Optional[str],
    role: str,
    content: str,
    sources: list = None,
):
    """Helper: save a chat message to the database."""
    msg = ChatMessage(
        user_id=user_id,
        document_id=document_id,
        role=role,
        content=content,
        sources_json=json.dumps(sources) if sources else None,
    )
    db.add(msg)
    db.commit()

"""
Chat routes — ask questions with RAG, stream responses via SSE, manage history.
"""
import html
import json
import time
from datetime import datetime, timezone
from io import BytesIO
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.metrics import record_query_response_time
from app.models import User, ChatMessage, Document, SharedMessage, ChatSession
from app.rate_limit import CHAT_QUERY_RATE_LIMIT, limiter
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ChatMessageResponse,
    ChatHistoryResponse,
    ShareAnswerResponse,
    ShareLinkResponse,
    SourceChunk,
    ChatSessionCreate,
    ChatSessionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/share/{message_id}", response_model=ShareAnswerResponse)
def get_shared_answer(
    message_id: str,
    db: Session = Depends(get_db),
):
    message = db.query(ChatMessage).filter(
        ChatMessage.id == message_id,
        ChatMessage.role == "assistant",
    ).first()

    if not message or not db.query(SharedMessage).filter(SharedMessage.message_id == message.id).first():
        raise HTTPException(status_code=404, detail="Shared answer not found")

    return _share_answer_response(message)


@router.post("/share/{message_id}", response_model=ShareLinkResponse)
def create_share_link(
    message_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = db.query(ChatMessage).filter(
        ChatMessage.id == message_id,
        ChatMessage.user_id == user.id,
    ).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message.role != "assistant":
        raise HTTPException(status_code=400, detail="Only assistant messages can be shared")

    shared_message = db.query(SharedMessage).filter(SharedMessage.message_id == message.id).first()
    if not shared_message:
        shared_message = SharedMessage(message_id=message.id)
        db.add(shared_message)
        db.commit()

    return ShareLinkResponse(
        message_id=str(message.id),
        share_url=f"/share?message_id={message.id}",
    )


@router.get("/sessions", response_model=List[ChatSessionResponse])
def get_chat_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all chat sessions for the authenticated user."""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return sessions


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
def create_chat_session(
    payload: ChatSessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new chat session."""
    session = ChatSession(
        user_id=user.id,
        title=payload.title,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
def rename_chat_session(
    session_id: str,
    payload: ChatSessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rename an existing chat session."""
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    session.title = payload.title
    db.commit()
    db.refresh(session)
    return session


@router.delete("/sessions/{session_id}")
def delete_chat_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a chat session and all its messages."""
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    db.delete(session)
    db.commit()
    return Response(status_code=204)


@router.get("/history/session/{session_id}", response_model=ChatHistoryResponse)
def get_session_history(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve chat history for a specific chat session."""
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id == session_id,
            ChatMessage.user_id == user.id,
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

        formatted.append(
            ChatMessageResponse(
                id=str(msg.id),
                role=msg.role,
                content=msg.content,
                sources=sources,
                created_at=msg.created_at,
            )
        )

    return ChatHistoryResponse(messages=formatted, document_id=None)


def generate_answer(question: str, user_id: str, document_id: Optional[str] = None, hf_token: Optional[str] = None):
    from app.rag.agent import generate_answer as _generate_answer

    return _generate_answer(question=question, user_id=user_id, document_id=document_id, hf_token=hf_token)


def generate_answer_stream(question: str, user_id: str, document_id: Optional[str] = None, hf_token: Optional[str] = None):
    from app.rag.agent import generate_answer_stream as _generate_answer_stream

    return _generate_answer_stream(question=question, user_id=user_id, document_id=document_id, hf_token=hf_token)


@router.post("/ask", response_model=ChatResponse)
@limiter.limit(CHAT_QUERY_RATE_LIMIT)
def ask_question(
    request: Request,
    payload: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ask a question with RAG retrieval (non-streaming)."""
    started_at = time.perf_counter()
    try:
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
            
            # Update last_accessed_at timestamp
            doc.last_accessed_at = datetime.now(timezone.utc)
            db.commit()

        # Resolve or create session
        session_id = payload.session_id
        if not session_id:
            session = db.query(ChatSession).filter(ChatSession.user_id == user.id).first()
            if not session:
                session = ChatSession(user_id=user.id, title="Default Chat")
                db.add(session)
                db.commit()
                db.refresh(session)
            session_id = session.id

        result = generate_answer(
            question=payload.question,
            user_id=user.id,
            document_id=payload.document_id,
            hf_token=user.hf_token,
        )

        # Save to chat history
        _save_message(db, user.id, payload.document_id, "user", payload.question, session_id=session_id)
        _save_message(db, user.id, payload.document_id, "assistant", result["answer"], result["sources"], session_id=session_id)

        return ChatResponse(
            answer=result["answer"],
            sources=[SourceChunk(**s) for s in result["sources"]],
            document_id=payload.document_id,
        )
    finally:
        record_query_response_time(time.perf_counter() - started_at)


@router.post("/ask/stream")
@limiter.limit(CHAT_QUERY_RATE_LIMIT)
def ask_question_stream(
    request: Request,
    payload: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ask a question with Server-Sent Events (SSE) streaming response."""
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
        
        # Update last_accessed_at timestamp
        doc.last_accessed_at = datetime.now(timezone.utc)
        db.commit()

    started_at = time.perf_counter()

    # Resolve or create session
    session_id = payload.session_id
    if not session_id:
        session = db.query(ChatSession).filter(ChatSession.user_id == user.id).first()
        if not session:
            session = ChatSession(user_id=user.id, title="Default Chat")
            db.add(session)
            db.commit()
            db.refresh(session)
        session_id = session.id

    # Save user message immediately
    _save_message(db, user.id, payload.document_id, "user", payload.question, session_id=session_id)

    # Stream response
    def event_stream():
        full_answer = ""
        sources = []

        try:
            for chunk in generate_answer_stream(
                question=payload.question,
                user_id=user.id,
                document_id=payload.document_id,
                hf_token=user.hf_token,
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
                _save_message(save_db, user.id, payload.document_id, "assistant", full_answer, sources, session_id=session_id)
            finally:
                save_db.close()
        finally:
            record_query_response_time(time.perf_counter() - started_at)

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
    """Retrieve the complete chat history for a specific document."""
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
            id=str(msg.id),
            role=msg.role,
            content=msg.content,
            sources=sources,
            created_at=msg.created_at,
        ))

    return ChatHistoryResponse(messages=formatted, document_id=document_id)


@router.get("/export/{document_id}")
def export_chat_history(
    document_id: str,
    format: str = "md",
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Export the chat history for a document as a downloadable file."""
    from app.auth import decode_token as _decode

    # Resolve user from query-param token (browser download links can't set headers)
    resolved_user = None
    if token:
        user_id = _decode(token)
        if user_id:
            resolved_user = db.query(User).filter(User.id == user_id).first()
    
    if resolved_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    if format not in ("md", "txt", "pdf"):
        raise HTTPException(status_code=400, detail="Format must be 'md', 'txt', or 'pdf'")

    # Verify document exists and belongs to user
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == resolved_user.id,
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == resolved_user.id,
            ChatMessage.document_id == document_id,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    if not messages:
        raise HTTPException(status_code=404, detail="No chat history found for this document")

    if format == "md":
        content = _format_markdown(doc, messages)
        media_type = "text/markdown"
        extension = "md"
    elif format == "txt":
        content = _format_plaintext(doc, messages)
        media_type = "text/plain"
        extension = "txt"
    else:
        from app.routes.chat_export import format_pdf as _format_pdf
        content = _format_pdf(doc, messages)
        media_type = "application/pdf"
        extension = "pdf"

    safe_name = doc.original_name.rsplit(".", 1)[0]
    filename = f"{safe_name}_chat_history.{extension}"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.delete("/history/{document_id}")
def clear_chat_history(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete all chat messages associated with a specific document."""
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
    session_id: Optional[str] = None,
):
    """Save a chat message to the database."""
    if not session_id:
        session = db.query(ChatSession).filter(ChatSession.user_id == user_id).first()
        if not session:
            session = ChatSession(user_id=user_id, title="Default Chat")
            db.add(session)
            db.commit()
            db.refresh(session)
        session_id = session.id

    msg = ChatMessage(
        user_id=user_id,
        document_id=document_id,
        session_id=session_id,
        role=role,
        content=content,
        sources_json=json.dumps(sources) if sources else None,
    )
    db.add(msg)
    db.commit()


def _share_answer_response(message: ChatMessage) -> ShareAnswerResponse:
    """Format a shared assistant message with only safe public fields."""
    sources = []
    if message.sources_json:
        try:
            sources = [SourceChunk(**item) for item in json.loads(message.sources_json)]
        except Exception:
            sources = []

    return ShareAnswerResponse(
        id=str(message.id),
        content=message.content,
        created_at=message.created_at,
        sources=sources,
    )


def _format_markdown(doc, messages) -> str:
    """Format chat history as a Markdown document."""
    lines = [
        f"# Chat History — {doc.original_name}",
        "",
        f"**Document:** {doc.original_name}  ",
        f"**Exported at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Total messages:** {len(messages)}",
        "",
        "---",
        "",
    ]

    for msg in messages:
        timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S") if msg.created_at else ""
        role_label = "**You**" if msg.role == "user" else "**Assistant**"

        lines.append(f"### {role_label}")
        lines.append(f"*{timestamp}*")
        lines.append("")
        lines.append(msg.content)
        lines.append("")

        if msg.role == "assistant" and msg.sources_json:
            try:
                sources = json.loads(msg.sources_json)
                if sources:
                    lines.append("**Sources:**")
                    lines.append("")
                    for i, src in enumerate(sources, 1):
                        lines.append(f"> **[{i}]** {src.get('filename', 'Unknown')}, "
                                     f"Page {src.get('page', '?')} "
                                     f"(Confidence: {src.get('confidence', 0)}%)")
                        text_preview = src.get("text", "")[:150]
                        if text_preview:
                            lines.append(f"> {text_preview}...")
                        lines.append(">")
                    lines.append("")
            except Exception:
                pass

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _format_plaintext(doc, messages) -> str:
    """Format chat history as a plain text document."""
    lines = [
        f"Chat History — {doc.original_name}",
        f"Exported at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total messages: {len(messages)}",
        "=" * 60,
        "",
    ]

    for msg in messages:
        timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S") if msg.created_at else ""
        role_label = "You" if msg.role == "user" else "Assistant"

        lines.append(f"[{role_label}] ({timestamp})")
        lines.append(msg.content)

        if msg.role == "assistant" and msg.sources_json:
            try:
                sources = json.loads(msg.sources_json)
                if sources:
                    lines.append("")
                    lines.append("Sources:")
                    for i, src in enumerate(sources, 1):
                        lines.append(f"  [{i}] {src.get('filename', 'Unknown')}, "
                                     f"Page {src.get('page', '?')} "
                                     f"(Confidence: {src.get('confidence', 0)}%)")
            except Exception:
                pass

        lines.append("-" * 60)
        lines.append("")

    return "\n".join(lines)

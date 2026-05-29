"""
Chat routes — ask questions with RAG, stream responses via SSE, manage history.
"""
import html
import json
import time
from datetime import datetime
from io import BytesIO
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ChatMessage, Document
from app.metrics import record_query_response_time
from app.schemas import ChatRequest, ChatResponse, ChatMessageResponse, ChatHistoryResponse, SourceChunk
from app.auth import get_current_user
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


def generate_answer(question: str, user_id: str, document_id: Optional[str] = None):
    """Import the RAG agent lazily so route tests can patch this boundary."""
    from app.rag.agent import generate_answer as _generate_answer

    return _generate_answer(
        question=question,
        user_id=user_id,
        document_id=document_id,
    )


def generate_answer_stream(question: str, user_id: str, document_id: Optional[str] = None):
    """Import the streaming RAG agent lazily so route tests can patch this boundary."""
    from app.rag.agent import generate_answer_stream as _generate_answer_stream

    return _generate_answer_stream(
        question=question,
        user_id=user_id,
        document_id=document_id,
    )


@router.post("/ask", response_model=ChatResponse)
@limiter.limit("10/minute")
def ask_question(
    request: Request,
    payload: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ask a question with RAG retrieval (non-streaming).

    Processes a user's question by retrieving relevant document chunks,
    generating an answer using an LLM, and saving the conversation to chat
    history. If a `document_id` is provided, the retrieval is scoped to that
    specific document; otherwise, it searches across all documents owned by
    the user.

    Args:
        payload: ChatRequest containing the `question` text and optionally a
            `document_id` to limit the retrieval scope.
        user: The currently authenticated user, obtained from the dependency.
        db: SQLAlchemy database session, obtained from the dependency.

    Returns:
        ChatResponse: An object containing:
            - answer: The generated answer text.
            - sources: A list of `SourceChunk` objects with metadata about
              the retrieved chunks (e.g., filename, page number, text snippet).
            - document_id: The document ID that was used (if any).

    Raises:
        HTTPException: 404 if the specified `document_id` does not exist or
            does not belong to the authenticated user.
        HTTPException: 400 if the document exists but its status is not
            "ready" (e.g., still processing or failed).
    """
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
    finally:
        record_query_response_time(time.perf_counter() - started_at)


@router.post("/ask/stream")
@limiter.limit("10/minute")
def ask_question_stream(
    request: Request,
    payload: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ask a question with Server-Sent Events (SSE) streaming response.

    Processes a user's question using RAG and streams the answer token by
    token over SSE. The user's question is saved to chat history immediately.
    The assistant's answer is accumulated on the server and saved to history
    only after the stream completes. If a `document_id` is provided, retrieval
    is scoped to that document.

    Args:
        payload: ChatRequest containing the `question` text and optionally a
            `document_id` to limit the retrieval scope.
        user: The currently authenticated user, obtained from the dependency.
        db: SQLAlchemy database session, obtained from the dependency.

    Returns:
        StreamingResponse: A FastAPI `StreamingResponse` with:
            - media_type: "text/event-stream"
            - Headers: Cache-Control, Connection, and X-Accel-Buffering set
              for proper SSE behavior.
            - Body: A generator yielding SSE messages with `token` (partial
              answer) and `sources` (final source metadata) events.

    Raises:
        HTTPException: 404 if the specified `document_id` does not exist or
            does not belong to the authenticated user.
        HTTPException: 400 if the document exists but its status is not
            "ready" (e.g., still processing or failed).

    Note:
        The streaming response uses a generator `event_stream` that yields
        raw SSE chunks. The assistant's full answer is reconstructed from
        the stream to save the complete conversation history. A separate
        database session is created inside the generator to avoid using the
        closed request session.
    """
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

    started_at = time.perf_counter()

    # Save user message immediately
    _save_message(db, user.id, payload.document_id, "user", payload.question)

    # Stream response
    def event_stream():
        full_answer = ""
        sources = []

        try:
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
    """Retrieve the complete chat history for a specific document.

    Fetches all messages (both user and assistant) associated with the given
    document and the authenticated user, ordered chronologically from oldest
    to newest. Assistant messages that contain source metadata will have the
    `sources` field populated.

    Args:
        document_id: The unique identifier of the document whose chat history is requested.
        user: The currently authenticated user, obtained from the dependency.
        db: SQLAlchemy database session, obtained from the dependency.

    Returns:
        ChatHistoryResponse: An object containing:
            - messages: A list of `ChatMessageResponse` objects, each with
              `id`, `role` ("user" or "assistant"), `content`, `sources`
              (list of `SourceChunk` for assistant messages), and `created_at`.
            - document_id: The document ID that was queried.
    """
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


@router.get("/export/{document_id}")
def export_chat_history(
    document_id: str,
    format: str = "md",
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Export the chat history for a document as a downloadable file.

    Supports Markdown (.md), plain text (.txt), or PDF (.pdf) export. The function accepts
    authentication via either the standard `Authorization: Bearer <token>`
    header (handled by the dependency chain) or a `token` query parameter to
    facilitate browser-initiated downloads that cannot set custom headers.

    Args:
        document_id: The unique identifier of the document whose chat history is to be exported.
        format: Output format, either "md" (Markdown), "txt" (plain text), or "pdf". Defaults to "md".
        token: Optional JWT token passed as a query parameter. Used for browser
            downloads when the `Authorization` header is not available.
        db: SQLAlchemy database session, obtained from the dependency.

    Returns:
        Response: A FastAPI `Response` object with:
            - `content`: Formatted chat history as a string or PDF bytes.
            - `media_type`: `text/markdown`, `text/plain`, or `application/pdf`.
            - `headers`: `Content-Disposition` attachment header with a generated filename.

    Raises:
        HTTPException: 401 if neither the token query parameter nor a valid
            bearer token provides an authenticated user.
        HTTPException: 400 if the `format` parameter is not "md", "txt", or "pdf".
        HTTPException: 404 if the document does not exist or does not belong
            to the user, or if no chat messages are found for the document.
    """
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
    """Delete all chat messages associated with a specific document.

    Removes every chat message (both user and assistant) linked to the given
    `document_id` and the authenticated user. The deletion is permanent and
    cannot be undone.

    Args:
        document_id: The unique identifier of the document whose chat history should be cleared.
        user: The currently authenticated user, obtained from the dependency.
        db: SQLAlchemy database session, obtained from the dependency.

    Returns:
        dict: A simple JSON object with a `message` field confirming the deletion.
    """
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
    """Save a chat message to the database.

    Creates a `ChatMessage` record with the provided user, document,
    role, content, and optional source metadata. The message is added to
    the session and committed immediately. The database session must be
    managed by the caller (e.g., closed after use).

    Args:
        user_id: The ID of the authenticated user.
        document_id: Optional document ID that the message pertains to.
            Can be `None` for global chat contexts.
        db: SQLAlchemy database session (active, typically from a dependency).
        role: The message sender role, e.g., "user" or "assistant".
        content: The full text content of the message.
        sources: Optional list of source dictionaries (usually from RAG
            retrieval) to be stored as JSON. Defaults to `None`.

    Returns:
        None

    Note:
        The function commits the transaction. It does not close the session,
        leaving that responsibility to the caller. If `sources` is provided,
        it is serialized using `json.dumps()`.
    """
    msg = ChatMessage(
        user_id=user_id,
        document_id=document_id,
        role=role,
        content=content,
        sources_json=json.dumps(sources) if sources else None,
    )
    db.add(msg)
    db.commit()


def _format_markdown(doc, messages) -> str:
    """Format chat history as a Markdown document.

    Generates a Markdown string containing the document metadata and the
    full conversation. User messages are labeled "You", assistant messages
    are labeled "Assistant". For assistant responses, if source information
    is available, it is rendered as a numbered list with filename, page,
    confidence, and a text preview.

    Args:
        doc: The Document object (must have `original_name` attribute).
        messages: List of ChatMessage objects, each with attributes:
            `role` (str), `content` (str), `created_at` (datetime, optional),
            and `sources_json` (str, JSON-encoded list of source dicts).

    Returns:
        str: A Markdown string ready for writing to a `.md` file.
    """
    lines = [
        f"# Chat History — {doc.original_name}",
        "",
        f"**Document:** {doc.original_name}  ",
        f"**Exported at:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
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

        # Include source citations for assistant messages
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
    """Format chat history as a plain text document.

    Generates a plain text string containing the document metadata and the
    full conversation. User messages are labeled "You", assistant messages
    are labeled "Assistant". For assistant responses, if source information
    is available, it is rendered as a numbered list with filename, page,
    and confidence (text preview is omitted in plain text format).

    Args:
        doc: The Document object (must have `original_name` attribute).
        messages: List of ChatMessage objects, each with attributes:
            `role` (str), `content` (str), `created_at` (datetime, optional),
            and `sources_json` (str, JSON‑encoded list of source dicts).

    Returns:
        str: A plain text string ready for writing to a `.txt` file.
    """
    lines = [
        f"Chat History — {doc.original_name}",
        f"Exported at: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total messages: {len(messages)}",
        "=" * 60,
        "",
    ]

    for msg in messages:
        timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S") if msg.created_at else ""
        role_label = "You" if msg.role == "user" else "Assistant"

        lines.append(f"[{role_label}] ({timestamp})")
        lines.append(msg.content)

        # Include source citations for assistant messages
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


def _format_pdf(doc, messages) -> bytes:
    """Format chat history as a PDF document."""
    buffer = BytesIO()
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    metadata_style = styles["Normal"]
    metadata_style.spaceAfter = 6
    content_style = ParagraphStyle(
        "ChatContent",
        parent=styles["BodyText"],
        leading=14,
        spaceAfter=10,
    )
    source_style = ParagraphStyle(
        "ChatSource",
        parent=styles["BodyText"],
        leftIndent=14,
        leading=12,
        spaceAfter=4,
    )

    story = [
        Paragraph(f"Chat History - {html.escape(doc.original_name)}", styles["Title"]),
        Spacer(1, 0.15 * inch),
        Paragraph(f"Document: {html.escape(doc.original_name)}", metadata_style),
        Paragraph(f"Exported at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", metadata_style),
        Paragraph(f"Total messages: {len(messages)}", metadata_style),
        Spacer(1, 0.2 * inch),
    ]

    for msg in messages:
        timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S") if msg.created_at else ""
        role_label = "You" if msg.role == "user" else "Assistant"

        story.append(Paragraph(f"<b>{html.escape(role_label)}</b>", styles["Heading3"]))
        story.append(Paragraph(html.escape(timestamp), styles["Italic"]))
        story.append(Paragraph(_pdf_text(msg.content), content_style))

        if msg.role == "assistant" and msg.sources_json:
            try:
                sources = json.loads(msg.sources_json)
                if sources:
                    story.append(Paragraph("<b>Sources:</b>", metadata_style))
                    for i, src in enumerate(sources, 1):
                        filename = html.escape(str(src.get("filename", "Unknown")))
                        page = html.escape(str(src.get("page", "?")))
                        confidence = html.escape(str(src.get("confidence", 0)))
                        story.append(
                            Paragraph(
                                f"[{i}] {filename}, Page {page} (Confidence: {confidence}%)",
                                source_style,
                            )
                        )
                        text_preview = str(src.get("text", "")).strip()
                        if text_preview:
                            story.append(Paragraph(_pdf_text(text_preview), source_style))
            except Exception:
                pass

        story.append(Spacer(1, 0.15 * inch))

    pdf.build(story)
    return buffer.getvalue()


def _pdf_text(text: str) -> str:
    """Escape text for ReportLab paragraphs while preserving line breaks."""
    return html.escape(text or "").replace("\n", "<br/>")

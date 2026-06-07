"""
PDF export helper for chat transcripts.

Called by the /chat/export/{document_id}?format=pdf route in chat.py.
Uses ReportLab (already in requirements.txt) to produce a clean, readable
PDF from a list of ChatMessage ORM objects.
"""
import json
import textwrap
from datetime import datetime
from io import BytesIO
from typing import List

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Palette ───────────────────────────────────────────────────────────────────
_PRIMARY = colors.HexColor("#4F46E5")       # indigo — user bubble accent
_ASSISTANT = colors.HexColor("#059669")     # emerald — assistant bubble accent
_MUTED = colors.HexColor("#6B7280")         # gray-500 — timestamps / meta
_SOURCE_BG = colors.HexColor("#F3F4F6")     # gray-100 — source card background
_DIVIDER = colors.HexColor("#E5E7EB")       # gray-200 — horizontal rules
_BLACK = colors.HexColor("#111827")         # near-black — body text


def _build_styles() -> dict:
    """Return a dict of named ParagraphStyles used throughout the PDF."""
    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Normal"],
            fontSize=20,
            leading=26,
            textColor=_BLACK,
            spaceAfter=2 * mm,
            fontName="Helvetica-Bold",
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=base["Normal"],
            fontSize=9,
            leading=13,
            textColor=_MUTED,
            spaceAfter=4 * mm,
            fontName="Helvetica",
        ),
        "role_user": ParagraphStyle(
            "RoleUser",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            textColor=_PRIMARY,
            fontName="Helvetica-Bold",
            spaceAfter=1 * mm,
        ),
        "role_assistant": ParagraphStyle(
            "RoleAssistant",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            textColor=_ASSISTANT,
            fontName="Helvetica-Bold",
            spaceAfter=1 * mm,
        ),
        "timestamp": ParagraphStyle(
            "Timestamp",
            parent=base["Normal"],
            fontSize=8,
            leading=11,
            textColor=_MUTED,
            fontName="Helvetica-Oblique",
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=10,
            leading=15,
            textColor=_BLACK,
            fontName="Helvetica",
            spaceAfter=3 * mm,
            wordWrap="LTR",
        ),
        "source_label": ParagraphStyle(
            "SourceLabel",
            parent=base["Normal"],
            fontSize=8,
            leading=11,
            textColor=_MUTED,
            fontName="Helvetica-Bold",
            spaceAfter=1 * mm,
        ),
        "source_item": ParagraphStyle(
            "SourceItem",
            parent=base["Normal"],
            fontSize=8,
            leading=12,
            textColor=_BLACK,
            fontName="Helvetica",
            leftIndent=4 * mm,
        ),
        "source_preview": ParagraphStyle(
            "SourcePreview",
            parent=base["Normal"],
            fontSize=8,
            leading=12,
            textColor=_MUTED,
            fontName="Helvetica-Oblique",
            leftIndent=6 * mm,
            spaceAfter=1 * mm,
        ),
    }


def _safe_text(text: str) -> str:
    """Escape XML special characters so ReportLab Paragraph doesn't crash."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def _wrap_body(text: str, width: int = 100) -> str:
    """Soft-wrap long lines so they fit inside the PDF column."""
    paragraphs = text.split("\n")
    wrapped = []
    for para in paragraphs:
        if len(para) <= width:
            wrapped.append(_safe_text(para))
        else:
            wrapped.extend(_safe_text(line) for line in textwrap.wrap(para, width))
    return "<br/>".join(wrapped) if wrapped else "&nbsp;"


def format_pdf(doc, messages: List) -> bytes:
    """Render chat history as a PDF and return the raw bytes.

    Args:
        doc:      SQLAlchemy Document ORM object (needs .original_name).
        messages: Ordered list of ChatMessage ORM objects.

    Returns:
        Raw PDF bytes ready to be returned as a FastAPI Response.
    """
    buffer = BytesIO()
    styles = _build_styles()

    page_w, page_h = A4
    margin = 18 * mm

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"Chat History — {doc.original_name}",
        author="PDF Assistant RAG",
    )

    story = []

    # ── Cover block ───────────────────────────────────────────────────────────
    story.append(Paragraph("Chat Transcript", styles["title"]))
    story.append(
        Paragraph(
            f"Document: <b>{_safe_text(doc.original_name)}</b><br/>"
            f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
            f"Messages: {len(messages)}",
            styles["meta"],
        )
    )
    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=_PRIMARY,
            spaceAfter=6 * mm,
        )
    )

    # ── Messages ──────────────────────────────────────────────────────────────
    for msg in messages:
        is_user = msg.role == "user"
        role_label = "You" if is_user else "Assistant"
        role_style = styles["role_user"] if is_user else styles["role_assistant"]

        timestamp = (
            msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if msg.created_at
            else ""
        )

        # Role + timestamp
        story.append(Paragraph(role_label, role_style))
        if timestamp:
            story.append(Paragraph(timestamp, styles["timestamp"]))

        # Message body — handle multi-line content
        body_html = _wrap_body(msg.content or "")
        story.append(Paragraph(body_html, styles["body"]))

        # Sources (assistant messages only)
        if not is_user and msg.sources_json:
            try:
                sources = json.loads(msg.sources_json)
                if sources:
                    story.append(Paragraph("Sources:", styles["source_label"]))
                    for i, src in enumerate(sources, 1):
                        filename = _safe_text(src.get("filename", "Unknown"))
                        page = src.get("page", "?")
                        confidence = src.get("confidence", 0)
                        preview = _safe_text(src.get("text", "")[:120])

                        story.append(
                            Paragraph(
                                f"[{i}] {filename} — Page {page} "
                                f"(Confidence: {confidence}%)",
                                styles["source_item"],
                            )
                        )
                        if preview:
                            story.append(
                                Paragraph(
                                    f"{preview}{'...' if len(src.get('text','')) > 120 else ''}",
                                    styles["source_preview"],
                                )
                            )
            except Exception:
                pass

        # Divider between messages
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                color=_DIVIDER,
                spaceBefore=2 * mm,
                spaceAfter=4 * mm,
            )
        )

    # ── Footer note ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            f"Generated by PDF Assistant RAG · {datetime.now().strftime('%Y-%m-%d')}",
            styles["meta"],
        )
    )

    pdf.build(story)
    return buffer.getvalue()

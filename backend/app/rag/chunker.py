"""
Smart document chunking using LangChain's RecursiveCharacterTextSplitter.
Supports PDF, DOCX, TXT, and Markdown files with page-level metadata.
"""
import fitz  # PyMuPDF
import docx
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.config import get_settings

settings = get_settings()


def extract_pdf(filepath: str) -> List[Dict[str, Any]]:
    """Extract text from PDF with page numbers."""
    doc = fitz.open(filepath)
    pages = []

    for page_num, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            pages.append({
                "text": text,
                "page": page_num + 1,
            })

    doc.close()
    return pages


def extract_docx(filepath: str) -> List[Dict[str, Any]]:
    """Extract text from DOCX files."""
    doc = docx.Document(filepath)
    full_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])

    return [{"text": full_text, "page": 1}] if full_text else []


def extract_txt(filepath: str) -> List[Dict[str, Any]]:
    """Extract text from TXT/Markdown files."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    return [{"text": text, "page": 1}] if text.strip() else []


def chunk_document(filepath: str) -> List[Dict[str, Any]]:
    """
    Load a document, extract text per page, and split into semantic chunks.
    Returns list of dicts with 'text', 'page', and 'chunk_index'.
    """
    ext = filepath.rsplit(".", 1)[-1].lower()

    # ── Extract text by file type ────────────────────
    if ext == "pdf":
        pages = extract_pdf(filepath)
    elif ext == "docx":
        pages = extract_docx(filepath)
    elif ext in ("txt", "md"):
        pages = extract_txt(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    if not pages:
        return []

    # ── LangChain recursive splitter ─────────────────
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    all_chunks = []
    chunk_index = 0

    for page_data in pages:
        text = page_data["text"]
        page_num = page_data["page"]

        # Split this page's text
        splits = splitter.split_text(text)

        for split_text in splits:
            if split_text.strip():
                all_chunks.append({
                    "text": split_text.strip(),
                    "page": page_num,
                    "chunk_index": chunk_index,
                })
                chunk_index += 1

    return all_chunks


def get_page_count(filepath: str) -> int:
    """Get total page count of a document."""
    ext = filepath.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        doc = fitz.open(filepath)
        count = len(doc)
        doc.close()
        return count

    return 1  # DOCX, TXT, MD are treated as single-page

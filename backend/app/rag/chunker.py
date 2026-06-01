"""
Smart document chunking using LangChain's RecursiveCharacterTextSplitter.
Supports PDF, DOCX, TXT, and Markdown files with page-level metadata.
"""
import json
import fitz  # PyMuPDF
import docx
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import get_settings

settings = get_settings()


def _is_word_inside_bbox(word: Dict[str, Any], bbox: tuple) -> bool:
    """Return True when the word center falls inside a pdfplumber bbox."""
    x0, top, x1, bottom = bbox
    word_x = (float(word["x0"]) + float(word["x1"])) / 2
    word_y = (float(word["top"]) + float(word["bottom"])) / 2
    return x0 <= word_x <= x1 and top <= word_y <= bottom


def _words_to_text(words: List[Dict[str, Any]], line_tolerance: float = 3.0) -> str:
    """Rebuild readable text from positioned pdfplumber words."""
    if not words:
        return ""

    sorted_words = sorted(words, key=lambda item: (round(float(item["top"]) / line_tolerance), item["x0"]))
    lines: List[List[Dict[str, Any]]] = []

    for word in sorted_words:
        if not lines:
            lines.append([word])
            continue

        current_top = sum(float(item["top"]) for item in lines[-1]) / len(lines[-1])
        if abs(float(word["top"]) - current_top) <= line_tolerance:
            lines[-1].append(word)
        else:
            lines.append([word])

    text_lines = [
        " ".join(item["text"] for item in sorted(line, key=lambda item: item["x0"]))
        for line in lines
    ]
    return "\n".join(line for line in text_lines if line.strip())


def _table_to_markdown(rows: List[List[Any]]) -> str:
    """Serialize extracted table rows into Markdown for retrieval."""
    cleaned_rows = [
        ["" if cell is None else str(cell).replace("\n", " ").strip() for cell in row]
        for row in rows
        if row and any(cell is not None and str(cell).strip() for cell in row)
    ]
    if not cleaned_rows:
        return ""

    width = max(len(row) for row in cleaned_rows)
    normalized = [row + [""] * (width - len(row)) for row in cleaned_rows]

    def fmt(row: List[str]) -> str:
        return "| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |"

    header = normalized[0]
    separator = ["---"] * width
    body = normalized[1:]
    return "\n".join([fmt(header), fmt(separator), *[fmt(row) for row in body]])


def extract_pdf(filepath: str) -> List[Dict[str, Any]]:
    """Extract PDF text while preserving tables as separate bbox-aware chunks."""
    try:
        return extract_pdf_with_tables(filepath)
    except ImportError:
        return extract_pdf_with_pymupdf(filepath)


def extract_pdf_with_pymupdf(filepath: str) -> List[Dict[str, Any]]:
    """Fallback PDF extraction with page numbers using PyMuPDF."""
    doc = fitz.open(filepath)
    pages = []

    for page_num, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            pages.append({
                "text": text,
                "page": page_num + 1,
                "chunk_type": "text",
            })
        else:
            # Fallback to OCR
            try:
                import pytesseract
                from PIL import Image
                import io
                import logging

                pix = page.get_pixmap(dpi=300)
                img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                ocr_text = pytesseract.image_to_string(img).strip()

                if ocr_text:
                    pages.append({
                        "text": ocr_text,
                        "page": page_num + 1,
                        "chunk_type": "text",
                        "ocr": True,
                    })
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"OCR fallback failed for page {page_num + 1}: {e}")

    doc.close()
    return pages


def extract_pdf_with_tables(filepath: str) -> List[Dict[str, Any]]:
    """Detect tables with pdfplumber, remove table text from paragraphs, and keep table bboxes."""
    import pdfplumber

    pages: List[Dict[str, Any]] = []

    with pdfplumber.open(filepath) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.find_tables()
            table_bboxes = [table.bbox for table in tables]

            words = page.extract_words() or []
            paragraph_words = [
                word for word in words
                if not any(_is_word_inside_bbox(word, bbox) for bbox in table_bboxes)
            ]
            paragraph_text = _words_to_text(paragraph_words)

            if paragraph_text.strip():
                pages.append({
                    "text": paragraph_text,
                    "page": page_num,
                    "chunk_type": "text",
                })
            elif not tables:
                # Fallback to OCR for scanned image pages
                try:
                    import pytesseract
                    import logging
                    
                    img = page.to_image(resolution=300).original.convert("RGB")
                    ocr_text = pytesseract.image_to_string(img).strip()
                    
                    if ocr_text:
                        pages.append({
                            "text": ocr_text,
                            "page": page_num,
                            "chunk_type": "text",
                            "ocr": True,
                        })
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"OCR fallback failed for page {page_num}: {e}")

            for table_index, table in enumerate(tables):
                table_text = _table_to_markdown(table.extract() or [])
                if table_text.strip():
                    pages.append({
                        "text": table_text,
                        "page": page_num,
                        "chunk_type": "table",
                        "bbox": json.dumps([round(float(value), 2) for value in table.bbox]),
                        "table_index": table_index,
                    })

    return pages


def extract_pdf_images(filepath: str) -> List[Dict[str, Any]]:
    """Extract images from a PDF and return list of dicts with image bytes and page number.

    Each entry: {"image_bytes": b"...", "page": int}
    """
    images = []
    doc = fitz.open(filepath)

    for page_num, page in enumerate(doc):
        # get_images returns a list of tuples where first item is xref
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                # Convert to RGB if it's CMYK or has alpha
                if pix.n >= 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)

                img_bytes = pix.tobytes("png")
                images.append({"image_bytes": img_bytes, "page": page_num + 1})
            except Exception:
                # ignore extracting this image
                continue

    doc.close()
    return images


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
    images = []

    # ── Extract text by file type ────────────────────
    if ext == "pdf":
        pages = extract_pdf(filepath)
        # also extract images for later captioning/embedding
        images = extract_pdf_images(filepath)
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
        chunk_type = page_data.get("chunk_type", "text")

        if chunk_type == "table":
            all_chunks.append({
                "text": text.strip(),
                "page": page_num,
                "chunk_index": chunk_index,
                "chunk_type": "table",
                "bbox": page_data.get("bbox", ""),
                "table_index": page_data.get("table_index", 0),
            })
            chunk_index += 1
            continue

        # Split this page's text
        splits = splitter.split_text(text)

        for split_text in splits:
            if split_text.strip():
                all_chunks.append({
                    "text": split_text.strip(),
                    "page": page_num,
                    "chunk_index": chunk_index,
                    "chunk_type": chunk_type,
                })
                chunk_index += 1

        # Attach any images that belong to this page after text chunks for the page
        for img in [i for i in images if i["page"] == page_num]:
            all_chunks.append({
                "text": "",
                "page": page_num,
                "chunk_index": chunk_index,
                "image_bytes": img["image_bytes"],
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

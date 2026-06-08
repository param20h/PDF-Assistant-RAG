"""
Smart document chunking using LangChain's RecursiveCharacterTextSplitter.
Supports PDF, DOCX, TXT, and Markdown files with page-level metadata.
"""
import json
import re
import fitz  # PyMuPDF
import docx
import logging
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


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


def _clean_table_cell(cell: Any) -> str:
    """Normalize extracted table cell text for Markdown serialization."""
    if cell is None:
        return ""
    return re.sub(r"\s+", " ", str(cell)).strip().replace("|", "\\|")


def _table_to_markdown(rows: List[List[Any]]) -> str:
    """Serialize extracted table rows into Markdown for retrieval."""
    cleaned_rows = [
        [_clean_table_cell(cell) for cell in row]
        for row in rows
        if row and any(_clean_table_cell(cell) for cell in row)
    ]
    if not cleaned_rows:
        return ""

    width = max(len(row) for row in cleaned_rows)
    normalized = [row + [""] * (width - len(row)) for row in cleaned_rows]

    def fmt(row: List[str]) -> str:
        return "| " + " | ".join(row) + " |"

    header = normalized[0]
    separator = ["---"] * width
    body = normalized[1:]
    return "\n".join([fmt(header), fmt(separator), *[fmt(row) for row in body]])


def extract_pdf(filepath: str) -> List[Dict[str, Any]]:
    """Extract PDF text while preserving tables as separate chunks.

    Prefer Unstructured for robust table extraction. Fall back to pdfplumber
    if Unstructured is not available, then to PyMuPDF as a last resort.
    """
    try:
        return extract_pdf_with_unstructured(filepath)
    except Exception as e:
        # Unstructured may be installed but require native deps (poppler/pdfinfo).
        # If anything goes wrong, fall back to pdfplumber then PyMuPDF.
        logger.warning(f"Unstructured extraction failed, falling back: {e}")
        try:
            return extract_pdf_with_tables(filepath)
        except Exception as e2:
            logger.warning(f"pdfplumber extraction failed, falling back: {e2}")
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

    doc.close()
    return pages


def extract_pdf_with_unstructured(filepath: str) -> List[Dict[str, Any]]:
    """Use Unstructured to partition PDF into elements and extract tables.

    This function will raise ImportError when Unstructured isn't installed so
    callers can fall back to other extractors.
    """
    try:
        from unstructured.partition.pdf import partition_pdf
        from unstructured.documents.elements import Table
    except Exception as e:
        raise ImportError("unstructured not available") from e

    elements = partition_pdf(filename=filepath)
    pages: List[Dict[str, Any]] = []
    table_idx = 0

    for elem in elements:
        # Determine element type and page number
        elem_type = getattr(elem, "element_type", None) or elem.__class__.__name__
        page_num = None
        if hasattr(elem, "page_number"):
            page_num = getattr(elem, "page_number")
        elif getattr(elem, "metadata", None):
            page_num = elem.metadata.get("page_number") or elem.metadata.get("page")
        page_num = int(page_num) if page_num else 1

        if isinstance(elem, Table) or (isinstance(elem_type, str) and elem_type.lower() == "table"):
            rows = []
            for raw_row in getattr(elem, "rows", []) or []:
                row = []
                for cell in raw_row:
                    # Cells may be elements or lists of elements
                    if isinstance(cell, (list, tuple)):
                        cell_text = " ".join(getattr(c, "text", str(c)) for c in cell)
                    else:
                        cell_text = getattr(cell, "text", str(cell))
                    row.append(cell_text)
                rows.append(row)

            table_text = _table_to_markdown(rows)
            if table_text.strip():
                pages.append({
                    "text": table_text,
                    "page": page_num,
                    "chunk_type": "table",
                    "table_index": table_idx,
                })
                table_idx += 1
        else:
            text = getattr(elem, "text", str(elem) if elem else "")
            if text and text.strip():
                pages.append({
                    "text": text,
                    "page": page_num,
                    "chunk_type": "text",
                })

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

            for table_index, table in enumerate(tables):
                table_text = _table_to_markdown(table.extract() or [])
                if table_text.strip():
                    # Normalize table bbox: [x0/W, y0/H, x1/W, y1/H]
                    W, H = float(page.width), float(page.height)
                    normalized_bbox = [
                        round(float(table.bbox[0]) / W, 4),
                        round(float(table.bbox[1]) / H, 4),
                        round(float(table.bbox[2]) / W, 4),
                        round(float(table.bbox[3]) / H, 4),
                    ]
                    pages.append({
                        "text": table_text,
                        "page": page_num,
                        "chunk_type": "table",
                        "bbox": json.dumps(normalized_bbox),
                        "table_index": table_index,
                    })

    return pages


def extract_pdf_images(
    doc_or_path: Any,
    min_width: int = 50,
    min_height: int = 50,
    min_size: int = 10240,
) -> Any:
    """Generator to yield extracted images from a PDF page-by-page.

    Accepts either a file path (str) or an open fitz.Document object.
    Yields dict: {"image_bytes": b"...", "page": int, "width": int, "height": int}
    """
    if not doc_or_path:
        return

    is_path = isinstance(doc_or_path, str)
    doc = None
    if is_path:
        try:
            doc = fitz.open(doc_or_path)
        except Exception as e:
            logger.warning(f"Could not open PDF with fitz for image extraction: {e}")
            return
    else:
        doc = doc_or_path

    try:
        for page_num, page in enumerate(doc):
            processed_xrefs = set()
            for img in page.get_images(full=True):
                xref = img[0]
                if xref in processed_xrefs:
                    continue
                processed_xrefs.add(xref)

                try:
                    pix = fitz.Pixmap(doc, xref)
                    width, height = pix.width, pix.height
                    
                    # Convert to RGB if it's CMYK or has alpha
                    if pix.n >= 4:
                        pix = fitz.Pixmap(fitz.csRGB, pix)

                    img_bytes = pix.tobytes("png")
                    
                    # Skip tiny/decorative images (bullet points, spacers, logos)
                    if width < min_width or height < min_height or len(img_bytes) < min_size:
                        del img_bytes
                        del pix
                        continue

                    yield {
                        "image_bytes": img_bytes,
                        "page": page_num + 1,
                        "width": width,
                        "height": height,
                    }
                except Exception:
                    continue
    finally:
        if is_path and doc:
            doc.close()


def extract_docx(filepath: str) -> List[Dict[str, Any]]:
    """Extract text from DOCX files."""
    doc = docx.Document(filepath)
    full_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])

    return [{"text": full_text, "page": 1}] if full_text else []


def extract_txt(filepath: str) -> List[Dict[str, Any]]:
    """Extract text from TXT/Markdown files, preserving tables as separate chunks."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    if not text.strip():
        return []

    chunks = []
    current_text_lines = []
    table_lines = []
    in_table = False

    for line in text.splitlines():
        is_table_line = line.strip().startswith("|")

        if is_table_line:
            if not in_table:
                # flush any accumulated text first
                if current_text_lines:
                    chunk_text = "\n".join(current_text_lines).strip()
                    if chunk_text:
                        chunks.append({"text": chunk_text, "page": 1, "chunk_type": "text"})
                    current_text_lines = []
                in_table = True
            table_lines.append(line)
        else:
            if in_table:
                # flush the table
                table_text = "\n".join(table_lines).strip()
                if table_text:
                    chunks.append({"text": table_text, "page": 1, "chunk_type": "table"})
                table_lines = []
                in_table = False
            current_text_lines.append(line)

    # flush whatever's left
    if in_table and table_lines:
        chunks.append({"text": "\n".join(table_lines).strip(), "page": 1, "chunk_type": "table"})
    elif current_text_lines:
        chunk_text = "\n".join(current_text_lines).strip()
        if chunk_text:
            chunks.append({"text": chunk_text, "page": 1, "chunk_type": "text"})

    return chunks

# Change the chunk_document function input to take a file path and optional chunk size and overlap parameters. 
def chunk_document(filepath: str, chunk_size: int = None, chunk_overlap: int = None) -> List[Dict[str, Any]]:
    """
    Load a document, extract text per page, and split into semantic chunks.
    Accepts a file path and optional chunk size and overlap parameters. 
    If chunk size and overlap are not provided, defaults from settings will be used.
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

    pdf_doc = None
    if ext == "pdf":
        try:
            pdf_doc = fitz.open(filepath)
        except Exception as e:
            logger.warning(f"Could not open PDF with fitz: {e}")

    if not pages:
        if not pdf_doc or len(pdf_doc) == 0:
            if pdf_doc:
                pdf_doc.close()
            return []
    
    # Set chunk size and chunk overlap with defaults if not provided
    if not chunk_size:
        chunk_size = settings.CHUNK_SIZE
    if not chunk_overlap:
        chunk_overlap = settings.CHUNK_OVERLAP

    # ── LangChain recursive splitter ─────────────────
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, # Allow custom chunk size to be passed in for embedding
        chunk_overlap=chunk_overlap, # Allow custom chunk overlap to be passed in for embedding
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    all_chunks = []
    chunk_index = 0

    try:
        # Determine total pages to process
        max_page_in_data = max(page_data["page"] for page_data in pages) if pages else 0
        total_pages = max(max_page_in_data, len(pdf_doc) if pdf_doc else 0)

        # Set up image generator iterator
        image_iter = None
        next_image = None
        if pdf_doc:
            try:
                # pass pdf_doc to avoid opening it twice
                image_iter = iter(extract_pdf_images(pdf_doc))
                next_image = next(image_iter)
            except StopIteration:
                next_image = None
            except Exception as e:
                logger.warning(f"Could not initialize image iterator: {e}")

        # Group pages by page number for sequential access
        pages_by_num = {}
        for p_data in pages:
            pages_by_num.setdefault(p_data["page"], []).append(p_data)

        for page_num in range(1, total_pages + 1):
            # 1. Process text/table chunks for this page
            page_data_list = pages_by_num.get(page_num, [])
            for page_data in page_data_list:
                text = page_data["text"]
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
                        chunk = {
                            "text": split_text.strip(),
                            "page": page_num,
                            "chunk_index": chunk_index,
                            "chunk_type": chunk_type,
                        }

                        # Extract bbox for PDF text chunks
                        if pdf_doc and page_num <= len(pdf_doc):
                            try:
                                page_obj = pdf_doc[page_num - 1]
                                rects = page_obj.search_for(split_text.strip())
                                if rects:
                                    W, H = float(page_obj.rect.width), float(page_obj.rect.height)
                                    norm_rects = [
                                        [
                                            round(r.x0 / W, 4),
                                            round(r.y0 / H, 4),
                                            round(r.x1 / W, 4),
                                            round(r.y1 / H, 4)
                                        ]
                                        for r in rects
                                    ]
                                    chunk["bbox"] = json.dumps(norm_rects)
                            except Exception as e:
                                logger.warning(f"Bbox extraction error on page {page_num}: {e}")

                        all_chunks.append(chunk)
                        chunk_index += 1

            # 2. Attach any images that belong to this page (generating captions on-the-fly and discarding bytes)
            while next_image and next_image["page"] == page_num:
                img_bytes = next_image["image_bytes"]
                try:
                    # Generate caption immediately
                    from app.rag.vision import caption_image
                    caption = caption_image(img_bytes, page=page_num)

                    if caption:
                        all_chunks.append({
                            "text": caption,
                            "page": page_num,
                            "chunk_index": chunk_index,
                            "chunk_type": "text",
                            "is_image": True,
                            "image_caption": caption,
                        })
                        chunk_index += 1
                except Exception as e:
                    logger.warning(f"Failed to generate caption for image on page {page_num}: {e}")
                    fallback_text = f"Image on page {page_num}."
                    all_chunks.append({
                        "text": fallback_text,
                        "page": page_num,
                        "chunk_index": chunk_index,
                        "chunk_type": "text",
                        "is_image": True,
                        "image_caption": fallback_text,
                    })
                    chunk_index += 1
                finally:
                    # Explicitly remove reference to raw image bytes to free memory
                    if next_image:
                        next_image["image_bytes"] = None
                    if "img_bytes" in locals():
                        del img_bytes

                    # Fetch next image
                    try:
                        next_image = next(image_iter)
                    except StopIteration:
                        next_image = None
                    except Exception as e:
                        logger.warning(f"Error getting next image from iterator: {e}")
                        next_image = None

            # Collect garbage at the end of each page to prevent memory buildup
            import gc
            gc.collect()

    finally:
        if pdf_doc:
            pdf_doc.close()

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

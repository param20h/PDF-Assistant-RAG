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
    """Rebuild readable text from positioned pdfplumber words, preserving multi-column reading order."""
    if not words:
        return ""

    # 1. Group words into horizontal lines based on vertical proximity
    sorted_words = sorted(words, key=lambda item: (float(item["top"]), item["x0"]))
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

    # 2. Split each line into segments based on horizontal gaps (column gutters)
    GAP_THRESHOLD = 20.0
    line_segments_list = []
    for line in lines:
        sorted_line_words = sorted(line, key=lambda item: item["x0"])
        segments_in_line = []
        current_seg = [sorted_line_words[0]]

        for word in sorted_line_words[1:]:
            prev_word = current_seg[-1]
            gap = float(word["x0"]) - float(prev_word["x1"])
            if gap > GAP_THRESHOLD:
                segments_in_line.append(current_seg)
                current_seg = [word]
            else:
                current_seg.append(word)
        segments_in_line.append(current_seg)
        line_segments_list.append(segments_in_line)

    # 3. Detect global vertical gutters from lines with multiple layout segments
    gutter_intervals = []
    for seg_list in line_segments_list:
        if len(seg_list) > 1:
            for i in range(len(seg_list) - 1):
                x1_prev = max(float(w["x1"]) for w in seg_list[i])
                x0_next = min(float(w["x0"]) for w in seg_list[i+1])
                if x0_next > x1_prev:
                    gutter_intervals.append((x1_prev, x0_next))

    significant_gutter_centers = []
    if gutter_intervals:
        sorted_gutters = sorted(gutter_intervals, key=lambda g: g[0])
        current_gutter_groups = []
        for g in sorted_gutters:
            inserted = False
            for group in current_gutter_groups:
                group_x0 = max(item[0] for item in group)
                group_x1 = min(item[1] for item in group)
                if max(g[0], group_x0) < min(g[1], group_x1):
                    group.append(g)
                    inserted = True
                    break
            if not inserted:
                current_gutter_groups.append([g])

        num_multi_seg_lines = sum(1 for seg_list in line_segments_list if len(seg_list) > 1)
        min_group_size = max(2, int(num_multi_seg_lines * 0.15))

        for group in current_gutter_groups:
            if len(group) >= min_group_size:
                centers = [(g[0] + g[1]) / 2.0 for g in group]
                significant_gutter_centers.append(sum(centers) / len(centers))
        significant_gutter_centers.sort()

    # 4. Flatten segments and capture absolute structural bounds
    segment_objs = []
    for seg_list in line_segments_list:
        for seg in seg_list:
            seg_x0 = min(float(w["x0"]) for w in seg)
            seg_x1 = max(float(w["x1"]) for w in seg)
            seg_top = min(float(w["top"]) for w in seg)
            seg_bottom = max(float(w["bottom"]) for w in seg)
            seg_text = " ".join(w["text"] for w in seg)
            segment_objs.append({
                "x0": seg_x0,
                "x1": seg_x1,
                "top": seg_top,
                "bottom": seg_bottom,
                "text": seg_text
            })

    # 5. Sort segments vertically into horizontal layout bands divided by full-width text structures
    segment_objs.sort(key=lambda s: s["top"])

    final_segments = []
    current_band = []
    GUTTER_TOLERANCE = 3.0

    for seg in segment_objs:
        crosses_gutter = False
        for center in significant_gutter_centers:
            if (seg["x0"] + GUTTER_TOLERANCE) < center < (seg["x1"] - GUTTER_TOLERANCE):
                crosses_gutter = True
                break

        if crosses_gutter:
            if current_band:
                def get_col_idx(s):
                    idx = 0
                    s_mid = (s["x0"] + s["x1"]) / 2.0
                    for c in significant_gutter_centers:
                        if s_mid > c:
                            idx += 1
                    return idx
                current_band.sort(key=lambda s: (get_col_idx(s), s["top"]))
                final_segments.extend(current_band)
                current_band = []
            final_segments.append(seg)
        else:
            current_band.append(seg)

    if current_band:
        def get_col_idx(s):
            idx = 0
            s_mid = (s["x0"] + s["x1"]) / 2.0
            for c in significant_gutter_centers:
                if s_mid > c:
                    idx += 1
            return idx
        current_band.sort(key=lambda s: (get_col_idx(s), s["top"]))
        final_segments.extend(current_band)

    text_lines = [seg["text"] for seg in final_segments if seg["text"].strip()]
    return "\n".join(text_lines)


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

    Extraction is attempted in order of richness:
    1. Unstructured (tables + layout)
    2. pdfplumber (tables + multi-column)
    3. PyMuPDF native text
    4. OCR fallback for image-only pages (pytesseract or easyocr)

    Each stage only runs if the previous one raises an exception OR
    produces no text at all (e.g. a purely scanned PDF).
    """
    pages: List[Dict[str, Any]] = []

    try:
        pages = extract_pdf_with_unstructured(filepath)
    except Exception as e:
        logger.warning(f"Unstructured extraction failed, falling back: {e}")

    if not pages:
        try:
            pages = extract_pdf_with_tables(filepath)
        except Exception as e2:
            logger.warning(f"pdfplumber extraction failed, falling back: {e2}")

    if not pages:
        try:
            pages = extract_pdf_with_pymupdf(filepath)
        except Exception as e3:
            logger.warning(f"PyMuPDF extraction failed, falling back to OCR: {e3}")

    # If still no text, run a full OCR pass for scanned/image-only PDFs.
    if not pages:
        logger.info(
            "All text extractors returned empty for '%s' — running full OCR pass",
            filepath,
        )
        try:
            from app.rag.ocr import extract_pdf_with_ocr
            pages = extract_pdf_with_ocr(filepath)
        except Exception as exc:
            logger.warning("OCR pass failed for '%s': %s", filepath, exc)

    return pages


def extract_pdf_with_pymupdf(filepath: str) -> List[Dict[str, Any]]:
    """Fallback PDF extraction with page numbers using PyMuPDF.

    For pages with no selectable text (scanned/image-only pages) OCR is
    attempted automatically using the configured OCR backend.
    """
    from app.rag.ocr import MIN_TEXT_CHARS, OCR_BACKEND, ocr_page

    doc = fitz.open(filepath)
    pages = []

    try:
        for page_num, page in enumerate(doc):
            text = page.get_text().strip()

            if len(text) >= MIN_TEXT_CHARS:
                pages.append({
                    "text": text,
                    "page": page_num + 1,
                    "chunk_type": "text",
                    "ocr": False,
                })
                continue

            # No selectable text — attempt OCR
            logger.info(
                "Page %d of '%s' is image-only — running OCR (backend=%s)",
                page_num + 1,
                filepath,
                OCR_BACKEND,
            )
            try:
                ocr_text = ocr_page(page)
                if ocr_text:
                    pages.append({
                        "text": ocr_text,
                        "page": page_num + 1,
                        "chunk_type": "text",
                        "ocr": True,
                    })
                else:
                    logger.warning(
                        "OCR returned no text for page %d of '%s'",
                        page_num + 1,
                        filepath,
                    )
            except ImportError:
                logger.warning(
                    "OCR backend '%s' not installed — skipping image-only page %d",
                    OCR_BACKEND,
                    page_num + 1,
                )
            except Exception as exc:
                logger.warning(
                    "OCR failed for page %d of '%s': %s",
                    page_num + 1,
                    filepath,
                    exc,
                )
    finally:
        doc.close()

    return pages


def extract_pdf_with_unstructured(filepath: str) -> List[Dict[str, Any]]:
    """Use Unstructured to partition PDF into elements and extract tables."""
    try:
        from unstructured.partition.pdf import partition_pdf
        from unstructured.documents.elements import Table
    except Exception as e:
        raise ImportError("unstructured not available") from e

    elements = partition_pdf(filename=filepath)
    pages: List[Dict[str, Any]] = []
    table_idx = 0

    for elem in elements:
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
    """Generator to yield extracted images from a PDF page-by-page."""
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
                    
                    if pix.n >= 4:
                        pix = fitz.Pixmap(fitz.csRGB, pix)

                    img_bytes = pix.tobytes("png")
                    
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
                if current_text_lines:
                    chunk_text = "\n".join(current_text_lines).strip()
                    if chunk_text:
                        chunks.append({"text": chunk_text, "page": 1, "chunk_type": "text"})
                    current_text_lines = []
                in_table = True
            table_lines.append(line)
        else:
            if in_table:
                table_text = "\n".join(table_lines).strip()
                if table_text:
                    chunks.append({"text": table_text, "page": 1, "chunk_type": "table"})
                table_lines = []
                in_table = False
            current_text_lines.append(line)

    if in_table and table_lines:
        chunks.append({"text": "\n".join(table_lines).strip(), "page": 1, "chunk_type": "table"})
    elif current_text_lines:
        chunk_text = "\n".join(current_text_lines).strip()
        if chunk_text:
            chunks.append({"text": chunk_text, "page": 1, "chunk_type": "text"})

    return chunks


def chunk_document(filepath: str, chunk_size: int = None, chunk_overlap: int = None) -> List[Dict[str, Any]]:
    """Load a document, extract text per page, and split into semantic chunks."""
    ext = filepath.rsplit(".", 1)[-1].lower()

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
    
    if not chunk_size:
        chunk_size = settings.CHUNK_SIZE
    if not chunk_overlap:
        chunk_overlap = settings.CHUNK_OVERLAP

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    all_chunks = []
    chunk_index = 0

    try:
        max_page_in_data = max(page_data["page"] for page_data in pages) if pages else 0
        total_pages = max(max_page_in_data, len(pdf_doc) if pdf_doc else 0)

        image_iter = None
        next_image = None
        if pdf_doc:
            try:
                image_iter = iter(extract_pdf_images(pdf_doc))
                next_image = next(image_iter)
            except StopIteration:
                next_image = None
            except Exception as e:
                logger.warning(f"Could not initialize image iterator: {e}")

        pages_by_num = {}
        for p_data in pages:
            pages_by_num.setdefault(p_data["page"], []).append(p_data)

        for page_num in range(1, total_pages + 1):
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

                splits = splitter.split_text(text)

                for split_text in splits:
                    if split_text.strip():
                        chunk = {
                            "text": split_text.strip(),
                            "page": page_num,
                            "chunk_index": chunk_index,
                            "chunk_type": chunk_type,
                        }

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

            while next_image and next_image["page"] == page_num:
                img_bytes = next_image["image_bytes"]
                try:
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
                    if next_image:
                        next_image["image_bytes"] = None
                    if "img_bytes" in locals():
                        del img_bytes

                    try:
                        if image_iter is not None:
                            next_image = next(image_iter)
                        else:
                            next_image = None
                    except StopIteration:
                        next_image = None
                    except Exception as e:
                        logger.warning(f"Error getting next image from iterator: {e}")
                        next_image = None

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

    return 1

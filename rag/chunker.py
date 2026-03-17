import fitz  # PyMuPDF
import docx
from config import CHUNK_SIZE, CHUNK_OVERLAP

# ── Extract Text from PDF ────────────────────────────
def load_pdf(filepath):
    doc = fitz.open(filepath)
    text_pages = []

    for page_num, page in enumerate(doc):
        text = page.get_text()
        text_pages.append({
            "text": text,
            "page": page_num + 1
        })

    doc.close()
    return text_pages


# ── Extract Text from DOCX ───────────────────────────
def load_docx(filepath):
    doc = docx.Document(filepath)
    text_pages = []
    full_text = ""

    for para in doc.paragraphs:
        full_text += para.text + "\n"

    text_pages.append({
        "text": full_text,
        "page": 1
    })

    return text_pages


# ── Extract Text from TXT ────────────────────────────
def load_txt(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    return [{
        "text": text,
        "page": 1
    }]


# ── Split Text into Chunks ───────────────────────────
def split_text(text, page_num):
    chunks = []
    start = 0

    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]

        if chunk.strip():
            chunks.append({
                "text": chunk,
                "page": page_num
            })

        start = end - CHUNK_OVERLAP

    return chunks


# ── Main Function ────────────────────────────────────
def load_and_chunk(filepath):
    ext = filepath.rsplit(".", 1)[1].lower()

    if ext == "pdf":
        pages = load_pdf(filepath)
    elif ext == "docx":
        pages = load_docx(filepath)
    elif ext in ["txt", "md"]:
        pages = load_txt(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    all_chunks = []
    for page in pages:
        chunks = split_text(page["text"], page["page"])
        all_chunks.extend(chunks)

    return all_chunks
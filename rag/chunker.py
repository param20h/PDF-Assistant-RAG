import fitz
from config import CHUNK_SIZE, CHUNK_OVERLAP

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

def load_and_chunk(filepath):
    pages = load_pdf(filepath)
    all_chunks = []

    for page in pages:
        chunks = split_text(page["text"], page["page"])
        all_chunks.extend(chunks)

    return all_chunks
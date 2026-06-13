import os
from typing import Any, Dict, List

import fitz  # PyMuPDF
import pymupdf4llm


class AdvancedPDFParser:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found at: {pdf_path}")
        self.doc = fitz.open(pdf_path)

    def extract_structured_text(self) -> List[Dict[str, Any]]:
        """Parses PDF page-by-page preserving markdown layouts & tables."""
        pages_data = []
        try:
            md_pages = pymupdf4llm.to_markdown(self.pdf_path, page_chunks=True)
            for page in md_pages:
                pages_data.append(
                    {
                        "page_number": page["metadata"]["page"],
                        "text": page["text"],
                        "type": "text_layout",
                    }
                )
        except Exception as e:
            print(f"Layout parsing failed, falling back to standard text: {e}")
            for page_num in range(len(self.doc)):
                page = self.doc.load_page(page_num)
                pages_data.append(
                    {
                        "page_number": page_num + 1,
                        "text": page.get_text(),
                        "type": "fallback_text",
                    }
                )
        return pages_data

    def process_embedded_images(self, page_num: int, page_obj: fitz.Page) -> List[str]:
        """Extracts images/charts and uses Gemini Flash to generate dense data descriptions."""
        image_descriptions = []
        image_list = page_obj.get_images(full=True)

        try:
            from google import genai
            client = genai.Client()
        except Exception as e:
            print(f"Gemini client init failed, skipping vision: {e}")
            return image_descriptions

        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = self.doc.extract_image(xref)
            image_bytes = base_image["image"]

            try:
                # Use Gemini 2.5 Flash via standard structured part inputs
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        genai.types.Part.from_bytes(
                            data=image_bytes, mime_type="image/jpeg"
                        ),
                        "Analyze this chart/image extracted from a document. Provide a highly detailed summary of its numbers, structural trends, or data contents so it can be effectively used for downstream text retrieval.",
                    ],
                )
                if response.text:
                    image_descriptions.append(response.text)
            except Exception as e:
                print(f"Vision processing skipped for page {page_num + 1}: {e}")
                continue

        return image_descriptions

    def ingest_document(self) -> List[Dict[str, Any]]:
        """Executes the hybrid pipeline generating combined text and image context strings."""
        final_payload = []
        structured_chunks = self.extract_structured_text()
        final_payload.extend(structured_chunks)

        for page_num in range(len(self.doc)):
            page = self.doc.load_page(page_num)
            img_summaries = self.process_embedded_images(page_num, page)
            for summary in img_summaries:
                final_payload.append(
                    {
                        "page_number": page_num + 1,
                        "text": f"[Visual Data Extraction Summary]: {summary}",
                        "type": "visual_image_summary",
                    }
                )

        return final_payload

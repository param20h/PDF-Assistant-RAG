import logging
from app.config import get_settings
import os

from app.rag.agent import get_llm_client

logger = logging.getLogger(__name__)
settings = get_settings()

def generate_document_summary(filePath: str, max_sentences: int = 3) -> str | None:
    """
    Extract text from the first few chunks of the document and ask LLM to summarise.
    Returns a short summary string, or None on failure.

    Args:
        filePath (str): Path to the document file.
        max_sentences (int): Maximum number of sentences in the summary.
    
    Returns:
        str | None: Summary text or None if summarisation fails.
    
    Note:
        - This function is designed to be called after a document is uploaded and processed.
        - It uses the first few chunks of the document to generate a summary, which is then stored in the database.        
    """
    from app.rag.chunker import chunk_document

    try:
        chunks = chunk_document(filePath)

        if not chunks:
            logger.warning(f"No chunks extracted from {filePath}, cannot summarise.")
            return None
        
        # Extract text from each chunk and concatenate for summarisation
        chunk_texts = []
        for chunk in chunks[:10]:  # Use first 10 chunks to limit input size
            text = chunk.get("text")
            chunk_texts.append(text) 

        text_to_summarise = " ".join(chunk_texts)

        llm = get_llm_client()

        prompt = f"Summarise the following text in {max_sentences} sentences:\n\n{text_to_summarise}"

        response = llm.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=settings.LLM_MODEL,
            max_tokens=settings.SUMMARY_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
        )
        summary = response.choices[0].message.content.strip() if response.choices else None

        return summary if summary else None

    except Exception as e:
        logger.error(f"Summary generation failed for {filePath}: {e}")
        return None
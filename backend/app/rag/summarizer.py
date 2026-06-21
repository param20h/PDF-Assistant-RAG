import logging
from app.config import get_settings
import os

from app.rag.agent import get_llm_client

logger = logging.getLogger(__name__)
settings = get_settings()

def generate_document_summary(
    filePath: str | None = None, 
    max_sentences: int = 3, 
    chunks: list[dict] | None = None
) -> str | None:
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
        # Fall back to file parsing only if chunks are not pre-extracted
        if chunks is None:
            if not filePath:
                logger.error("Neither 'chunks' nor 'filePath' was provided.")
                return None
            chunks = chunk_document(filePath)

        if not chunks:
            identifier = filePath if filePath else "provided chunks"
            logger.warning(f"No chunks available for {identifier}, cannot summarise.")
            return None
        
        # Extract text from each chunk and concatenate for summarisation
        chunk_texts = []
        for chunk in chunks[:10]:  # Use first 10 chunks to limit input size
            text = chunk.get("text")
            # Ensure text is explicitly a string instance and not just whitespace
            if isinstance(text, str) and text.strip():
                chunk_texts.append(text) 

        if not chunk_texts:
            logger.warning("Extracted chunks contained no valid text content.")
            return None

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

        return summary or None

    except Exception as e:
        identifier = filePath if filePath else "pre-extracted chunks"
        logger.error(f"Summary generation failed for {identifier}: {e}")
        return None
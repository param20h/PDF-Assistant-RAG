"""
RAG Agent — generation with HuggingFace Inference API (chat completion).
Supports both streaming (SSE) and non-streaming responses.
"""
import logging
import json
from typing import List, Dict, Any, Optional, Generator

from huggingface_hub import InferenceClient
from app.config import get_settings
from app.rag.retriever import retrieve
from app.rag.prompts import SYSTEM_PROMPT, RAG_PROMPT_TEMPLATE, GREETING_PROMPT

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Singleton LLM client ─────────────────────────────
_llm_client = None


def get_llm_client() -> InferenceClient:
    """Get or create HuggingFace InferenceClient (singleton)."""
    global _llm_client

    if _llm_client is None:
        _llm_client = InferenceClient(
            token=settings.HF_TOKEN,
        )
        logger.info(f"LLM client initialized for model: {settings.LLM_MODEL}")

    return _llm_client


def is_greeting(question: str) -> bool:
    """Detect if the question is a casual greeting rather than a document query."""
    greetings = {
        "hi", "hello", "hey", "how are you", "what's up", "whats up",
        "good morning", "good evening", "good afternoon", "thanks", "thank you",
        "bye", "goodbye", "help", "what can you do", "who are you",
    }
    return question.lower().strip().rstrip("!?.") in greetings


def build_context(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks into a context string."""
    if not chunks:
        return "No relevant document context was found."

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        confidence = chunk.get("confidence", 0)
        context_parts.append(
            f"### Excerpt {i} — {chunk['filename']}, Page {chunk['page']} "
            f"(Relevance: {confidence}%)\n\n{chunk['text']}"
        )

    return "\n\n---\n\n".join(context_parts)


def _chat_messages(system: str, user_content: str) -> list:
    """Build messages list for chat completion API."""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]


def generate_answer(
    question: str,
    user_id: str,
    document_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full RAG pipeline: retrieve → build context → generate answer.
    Returns dict with 'answer' and 'sources'.
    """
    client = get_llm_client()

    # ── Handle greetings ─────────────────────────────
    if is_greeting(question):
        messages = _chat_messages(
            "You are Document AI Analyst, a friendly AI assistant for document analysis.",
            question,
        )
        response = client.chat_completion(
            messages=messages,
            model=settings.LLM_MODEL,
            max_tokens=256,
            temperature=0.7,
        )
        answer = response.choices[0].message.content.strip()
        return {"answer": answer, "sources": []}

    # ── Retrieve relevant chunks ─────────────────────
    chunks = retrieve(
        query=question,
        user_id=user_id,
        document_id=document_id,
    )

    # ── Build prompt ─────────────────────────────────
    context = build_context(chunks)
    user_content = RAG_PROMPT_TEMPLATE.format(context=context, question=question)
    messages = _chat_messages(SYSTEM_PROMPT, user_content)

    # ── Generate answer ──────────────────────────────
    try:
        response = client.chat_completion(
            messages=messages,
            model=settings.LLM_MODEL,
            max_tokens=settings.LLM_MAX_NEW_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM generation error: {e}")
        answer = f"I encountered an error generating a response. Please try again. Error: {str(e)}"

    # ── Format sources ───────────────────────────────
    sources = [
        {
            "text": chunk["text"][:300] + ("..." if len(chunk["text"]) > 300 else ""),
            "filename": chunk["filename"],
            "page": chunk["page"],
            "score": chunk["score"],
            "confidence": chunk["confidence"],
        }
        for chunk in chunks
    ]

    return {"answer": answer, "sources": sources}


def generate_answer_stream(
    question: str,
    user_id: str,
    document_id: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    Streaming RAG pipeline — yields SSE-formatted chunks.
    First yields sources, then streams answer tokens.
    """
    client = get_llm_client()

    # ── Handle greetings ─────────────────────────────
    if is_greeting(question):
        yield f"data: {json.dumps({'type': 'sources', 'data': []})}\n\n"

        try:
            messages = _chat_messages(
                "You are Document AI Analyst, a friendly AI assistant for document analysis.",
                question,
            )
            stream = client.chat_completion(
                messages=messages,
                model=settings.LLM_MODEL,
                max_tokens=256,
                temperature=0.7,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield f"data: {json.dumps({'type': 'token', 'data': delta})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    # ── Retrieve relevant chunks ─────────────────────
    chunks = retrieve(
        query=question,
        user_id=user_id,
        document_id=document_id,
    )

    # ── Yield sources first ──────────────────────────
    sources = [
        {
            "text": chunk["text"][:300] + ("..." if len(chunk["text"]) > 300 else ""),
            "filename": chunk["filename"],
            "page": chunk["page"],
            "score": chunk["score"],
            "confidence": chunk["confidence"],
        }
        for chunk in chunks
    ]
    yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"

    # ── Build prompt ─────────────────────────────────
    context = build_context(chunks)
    user_content = RAG_PROMPT_TEMPLATE.format(context=context, question=question)
    messages = _chat_messages(SYSTEM_PROMPT, user_content)

    # ── Stream answer tokens ─────────────────────────
    try:
        stream = client.chat_completion(
            messages=messages,
            model=settings.LLM_MODEL,
            max_tokens=settings.LLM_MAX_NEW_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield f"data: {json.dumps({'type': 'token', 'data': delta})}\n\n"

    except Exception as e:
        logger.error(f"LLM streaming error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"

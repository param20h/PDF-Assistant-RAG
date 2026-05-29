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
from app.rag.tracing import trace_function

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


@trace_function(
    "generate_answer",
    metadata_factory=lambda question, user_id, document_id=None: {
        "user_id": user_id,
        "document_id": document_id,
        "llm_model": settings.LLM_MODEL,
    },
)
def generate_answer(
    question: str,
    user_id: str,
    document_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full RAG pipeline: retrieve → build context → generate answer.
    Returns dict with 'answer' and 'sources'.
    """
    # Get HuggingFace InferenceClient singleton (created once, reused)
    client = get_llm_client()

    # ── Handle greetings ─────────────────────────────
    # Short-circuit: if user just says "hello", skip RAG entirely
    if is_greeting(question):
        try:
            # Send greeting to LLM with a friendly system prompt (no document context)
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
            answer = response.choices[0].message.content.strip() if response.choices else "Hello! I'm Document AI Analyst. Upload a PDF and ask me questions about it."
        except Exception as e:
            logger.error(f"Greeting error: {e}")
            answer = "Hello! I'm Document AI Analyst. Upload a PDF and ask me questions about it."
        return {"answer": answer, "sources": []}

    # ── Retrieve relevant chunks ─────────────────────
    # STAGE 1+2: Semantic search (ChromaDB) + cross-encoder reranking → top 5 chunks
    chunks = retrieve(
        query=question,
        user_id=user_id,
        document_id=document_id,
    )

    # ── Build prompt ─────────────────────────────────
    # Format retrieved chunks into a readable context block, then inject into the RAG prompt template
    context = build_context(chunks)
    user_content = RAG_PROMPT_TEMPLATE.format(context=context, question=question)
    messages = _chat_messages(SYSTEM_PROMPT, user_content)

    # ── Generate answer ──────────────────────────────
    # STAGE 3: Send prompt to HuggingFace Inference API and get the generated answer
    try:
        response = client.chat_completion(
            messages=messages,
            model=settings.LLM_MODEL,
            max_tokens=settings.LLM_MAX_NEW_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
        )
        if response.choices:
            answer = response.choices[0].message.content.strip()
        else:
            answer = "I couldn't generate a response. Please try again."
    except Exception as e:
        logger.error(f"LLM generation error: {e}")
        answer = f"I encountered an error generating a response. Please try again. Error: {str(e)}"

    # ── Format sources ───────────────────────────────
    # Truncate chunk text to 300 chars and attach metadata (filename, page, score, confidence) for frontend citation display
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


@trace_function(
    "generate_answer_stream",
    metadata_factory=lambda question, user_id, document_id=None: {
        "user_id": user_id,
        "document_id": document_id,
        "llm_model": settings.LLM_MODEL,
    },
)
def generate_answer_stream(
    question: str,
    user_id: str,
    document_id: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    Streaming RAG pipeline — yields SSE-formatted chunks.
    First yields sources, then streams answer tokens.
    """
    # Get HuggingFace InferenceClient singleton (created once, reused)
    client = get_llm_client()

    # ── Handle greetings ─────────────────────────────
    # Short-circuit: if user just says "hello", skip RAG entirely
    if is_greeting(question):
        # Yield empty sources array first so frontend resets its citation display
        yield f"data: {json.dumps({'type': 'sources', 'data': []})}\n\n"

        try:
            # Send greeting to LLM with a friendly system prompt (no document context)
            messages = _chat_messages(
                "You are Document AI Analyst, a friendly AI assistant for document analysis.",
                question,
            )
            # Stream greeting response token-by-token via SSE
            stream = client.chat_completion(
                messages=messages,
                model=settings.LLM_MODEL,
                max_tokens=256,
                temperature=0.7,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield f"data: {json.dumps({'type': 'token', 'data': delta})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

        # Signal end of stream, then exit early (no RAG)
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    # ── Retrieve relevant chunks ─────────────────────
    # STAGE 1+2: Semantic search (ChromaDB) + cross-encoder reranking → top 5 chunks
    chunks = retrieve(
        query=question,
        user_id=user_id,
        document_id=document_id,
    )

    # ── Yield sources first ──────────────────────────
    # Yield all sources first — frontend needs them to render citation cards before the answer starts appearing
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
    # Format retrieved chunks into a readable context block, then inject into the RAG prompt template
    context = build_context(chunks)
    user_content = RAG_PROMPT_TEMPLATE.format(context=context, question=question)
    messages = _chat_messages(SYSTEM_PROMPT, user_content)

    # ── Stream answer tokens ─────────────────────────
    # STAGE 3: Stream tokens from HuggingFace Inference API → forward each as an SSE 'token' event
    try:
        stream = client.chat_completion(
            messages=messages,
            model=settings.LLM_MODEL,
            max_tokens=settings.LLM_MAX_NEW_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield f"data: {json.dumps({'type': 'token', 'data': delta})}\n\n"

    # If LLM fails mid-stream, yield an error event so frontend can display the message
    except Exception as e:
        logger.error(f"LLM streaming error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    # Signal end of stream to frontend (stops the streaming indicator)
    yield f"data: {json.dumps({'type': 'done'})}\n\n"

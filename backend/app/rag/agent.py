"""
Agentic RAG — intelligent routing using ReAct (Reasoning and Acting).
Intelligently chooses between PDF search, Web Search, and Math tools.
"""
import logging
import json
from typing import List, Dict, Any, Optional, Generator

from sympy import python

from huggingface_hub import InferenceClient
from langchain_classic.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace

from app.config import get_settings
from app.rag.retriever import retrieve
from app.rag.graph_retriever import get_entity_context
from app.rag.prompts import AGENT_SYSTEM_PROMPT
from app.rag.security import MALFORMED_OUTPUT_MESSAGE, OutputParserError, parse_agent_output
from app.rag.tools import PDFSearchTool, MathTool, WebSearchTool
from app.rag.tracing import trace_function

logger = logging.getLogger(__name__)
settings = get_settings()



def get_llm_client(hf_token: Optional[str] = None) -> InferenceClient:
    """Create a HuggingFace InferenceClient per-request."""

    token = hf_token or settings.HF_TOKEN

    if not token:
        raise ValueError(
            "Hugging Face API token is missing. Please configure HF_TOKEN."
        )

    return InferenceClient(token=token)


def _format_chat_history(messages: List[Dict[str, str]]) -> str:
    if not messages:
        return ""
    lines = ["Previous conversation:"]
    for msg in messages:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def get_agent_executor(
    user_id: str,
    document_id: Optional[str] = None,
    hf_token: Optional[str] = None,
    top_k: Optional[int] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
):
    """Initialize the LangChain ReAct agent executor."""

    # Initialize tools
    pdf_tool = PDFSearchTool(user_id=user_id, document_id=document_id, top_k=top_k)
    tools = [pdf_tool, MathTool(), WebSearchTool()]

    # Initialize LLM
    token = hf_token or settings.HF_TOKEN

    if not token:
        raise ValueError(
            "Hugging Face API token is missing. Please configure HF_TOKEN."
        )

    llm = HuggingFaceEndpoint(
        repo_id=settings.LLM_MODEL,
        huggingfacehub_api_token=token,
        max_new_tokens=settings.LLM_MAX_NEW_TOKENS,
        temperature=settings.LLM_TEMPERATURE,
        timeout=300,
    )

    chat_llm = ChatHuggingFace(llm=llm)

    # Setup Agent
    prompt = PromptTemplate.from_template(AGENT_SYSTEM_PROMPT)
    agent = create_react_agent(chat_llm, tools, prompt)

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
    )

    formatted_history = _format_chat_history(chat_history) if chat_history else ""

    return executor, pdf_tool, formatted_history

def is_greeting(question: str) -> bool:
    """Detect if the question is a casual greeting rather than a document query."""
    greetings = {
        "hi", "hello", "hey", "how are you", "what's up", "whats up",
        "good morning", "good evening", "good afternoon", "thanks", "thank you",
        "bye", "goodbye", "help", "what can you do", "who are you",
    }
    return question.lower().strip().rstrip("!?.") in greetings


@trace_function(
    "generate_answer",
    metadata_factory=lambda question, user_id, document_id=None, **kwargs: {
        "user_id": user_id,
        "document_id": document_id,
        "llm_model": settings.LLM_MODEL,
    },
)
def generate_answer(
    question: str,
    user_id: str,
    document_id: Optional[str] = None,
    hf_token: Optional[str] = None,
    top_k: Optional[int] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Agentic generation: retrieve via tools → reason → generate answer.
    """
    # ── Handle greetings ─────────────────────────────
    if is_greeting(question):
        client = get_llm_client(hf_token)
        try:
            messages = [
                {"role": "system", "content": "You are Document AI Analyst, a friendly AI assistant."},
                {"role": "user", "content": question},
            ]
            response = client.chat_completion(
                messages=messages,
                model=settings.LLM_MODEL,
                max_tokens=256,
            )
            answer = response.choices[0].message.content.strip() if response.choices else "Hello! How can I help you today?"
        except Exception:
            answer = "Hello! I'm Document AI Analyst. How can I help you with your documents?"
        return {"answer": answer, "sources": []}

    # ── Run Agent ────────────────────────────────────
    try:
        executor, pdf_tool, formatted_history = get_agent_executor(user_id, document_id, hf_token, top_k, chat_history)
        result = executor.invoke({"input": question, "chat_history": formatted_history})

        raw_answer = result.get("output", "")
        try:
            answer = parse_agent_output(raw_answer)
        except OutputParserError as e:
            logger.warning(f"Rejected malformed LLM output: {e}")
            answer = MALFORMED_OUTPUT_MESSAGE

        # Retrieve sources from the PDF tool if it was used
        sources = [
            {
                "text": chunk["text"][:300] + ("..." if len(chunk["text"]) > 300 else ""),
                "filename": chunk["filename"],
                "page": chunk["page"],
                "score": chunk["score"],
                "confidence": chunk.get("confidence", 0),
                "bbox": chunk.get("bbox", ""),
            }
            for chunk in getattr(pdf_tool, "last_sources", [])
        ]

        return {"answer": answer, "sources": sources}

    except Exception as e:
        logger.error(f"Agent execution error: {e}")
        return {
            "answer": f"I encountered an error while processing your request: {str(e)}",
            "sources": []
        }


@trace_function(
    "generate_answer_stream",
    metadata_factory=lambda question, user_id, document_id=None, **kwargs: {
        "user_id": user_id,
        "document_id": document_id,
        "llm_model": settings.LLM_MODEL,
    },
)
def generate_answer_stream(
    question: str,
    user_id: str,
    document_id: Optional[str] = None,
    hf_token: Optional[str] = None,
    top_k: Optional[int] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> Generator[str, None, None]:
    """
    Streaming Agentic pipeline.
    """
    # ── Handle greetings ─────────────────────────────
    if is_greeting(question):
        yield f"data: {json.dumps({'type': 'sources', 'data': []})}\n\n"
        client = get_llm_client(hf_token)
        try:
            stream = client.chat_completion(
                messages=[{"role": "user", "content": question}],
                model=settings.LLM_MODEL,
                max_tokens=256,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield f"data: {json.dumps({'type': 'token', 'data': chunk.choices[0].delta.content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    # ── Run Agent ────────────────────────────────────
    try:
        executor, pdf_tool, formatted_history = get_agent_executor(user_id, document_id, hf_token, top_k, chat_history)

        sources_sent = False

        for step in executor.stream({"input": question, "chat_history": formatted_history}):
            if "actions" in step:
                continue

            elif "intermediate_steps" in step:
                if not sources_sent and getattr(pdf_tool, "last_sources", []):
                    sources = [
                        {
                            "text": chunk["text"][:300] + ("..." if len(chunk["text"]) > 300 else ""),
                            "filename": chunk["filename"],
                            "page": chunk["page"],
                            "score": chunk["score"],
                            "confidence": chunk.get("confidence", 0),
                            "bbox": chunk.get("bbox", ""),
                        }
                        for chunk in pdf_tool.last_sources
                    ]
                    yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"
                    sources_sent = True

            elif "output" in step:
                full_answer = step["output"]
                try:
                    clean_answer = parse_agent_output(full_answer)
                except OutputParserError as e:
                    logger.warning(f"Rejected malformed streamed LLM output: {e}")
                    clean_answer = MALFORMED_OUTPUT_MESSAGE
                yield f"data: {json.dumps({'type': 'token', 'data': clean_answer})}\n\n"

    except Exception as e:
        logger.error(f"Agent streaming error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"

import json
from unittest.mock import MagicMock, patch
import pytest
from app.rag.agent import generate_answer, generate_answer_stream

@pytest.fixture
def mock_llm_client():
    with patch("app.rag.agent.get_llm_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        yield client

@pytest.fixture
def mock_retriever():
    with patch("app.rag.agent.retrieve") as mock_retrieve:
        yield mock_retrieve

@pytest.fixture
def mock_agent_executor():
    with patch("app.rag.agent.get_agent_executor") as mock_get:
        executor = MagicMock()
        pdf_tool = MagicMock()
        mock_get.return_value = (executor, pdf_tool, "")
        yield executor, pdf_tool

def test_generate_answer_success(mock_agent_executor, mock_retriever):
    executor, pdf_tool = mock_agent_executor
    
    # Mock executor output
    executor.invoke.return_value = {"output": '{"answer": "Test answer"}'}
    
    # Mock last_sources on pdf_tool
    pdf_tool.last_sources = [
        {
            "text": "This is a test chunk.",
            "filename": "test.pdf",
            "page": 1,
            "score": 0.9,
            "confidence": 90
        }
    ]

    result = generate_answer("test question", "user123", "doc123")

    assert result["answer"] == "Test answer"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["filename"] == "test.pdf"
    assert result["sources"][0]["text"] == "This is a test chunk."
    
    executor.invoke.assert_called_once_with({"input": "test question", "chat_history": ""})

def test_generate_answer_empty_retrieval(mock_agent_executor, mock_retriever):
    executor, pdf_tool = mock_agent_executor
    executor.invoke.return_value = {"output": '{"answer": "I don\'t know."}'}
    pdf_tool.last_sources = []

    result = generate_answer("test question", "user123", "doc123")

    assert result["answer"] == "I don't know."
    assert len(result["sources"]) == 0
    executor.invoke.assert_called_once_with({"input": "test question", "chat_history": ""})

def test_generate_answer_stream_success(mock_agent_executor, mock_retriever):
    executor, pdf_tool = mock_agent_executor
    pdf_tool.last_sources = [
        {
            "text": "Chunk text.",
            "filename": "test.pdf",
            "page": 1,
            "score": 0.8,
            "confidence": 80
        }
    ]

    def mock_stream(*args, **kwargs):
        yield {"intermediate_steps": [("action", "observation")]}
        yield {"output": '{"answer": "Hello world"}'}

    executor.stream.side_effect = mock_stream

    stream = generate_answer_stream("test question", "user123", "doc123")
    events = list(stream)

    # First event: sources
    sources_event = json.loads(events[0].replace("data: ", "").strip())
    assert sources_event["type"] == "sources"
    assert len(sources_event["data"]) == 1
    assert sources_event["data"][0]["filename"] == "test.pdf"

    # Second event: token "Hello world"
    token_event = json.loads(events[1].replace("data: ", "").strip())
    assert token_event["type"] == "token"
    assert token_event["data"] == "Hello world"

    # Last event: done
    done_event = json.loads(events[-1].replace("data: ", "").strip())
    assert done_event["type"] == "done"

def test_generate_answer_greeting(mock_llm_client, mock_retriever):
    # "hi" is a greeting, should skip RAG
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Hello there!"
    mock_response.choices = [mock_choice]
    mock_llm_client.chat_completion.return_value = mock_response

    result = generate_answer("hi", "user123")

    assert result["answer"] == "Hello there!"
    assert len(result["sources"]) == 0
    mock_retriever.assert_not_called()

def test_generate_answer_stream_empty_retrieval(mock_agent_executor, mock_retriever):
    executor, pdf_tool = mock_agent_executor
    pdf_tool.last_sources = []

    def mock_stream(*args, **kwargs):
        yield {"intermediate_steps": []}
        yield {"output": '{"answer": "I don\'t know."}'}

    executor.stream.side_effect = mock_stream

    stream = generate_answer_stream("test question", "user123", "doc123")
    events = list(stream)

    # First event: token "I don't know."
    token_event = json.loads(events[0].replace("data: ", "").strip())
    assert token_event["type"] == "token"
    assert token_event["data"] == "I don't know."

    # Last event: done
    done_event = json.loads(events[-1].replace("data: ", "").strip())
    assert done_event["type"] == "done"

def test_generate_answer_stream_error(mock_agent_executor, mock_retriever):
    executor, pdf_tool = mock_agent_executor
    executor.stream.side_effect = Exception("LLM Down")

    stream = generate_answer_stream("test question", "user123", "doc123")
    events = list(stream)

    error_event = [json.loads(e.replace("data: ", "").strip()) for e in events if "error" in e]
    assert len(error_event) > 0
    assert error_event[0]["data"] == "LLM Down"

def test_generate_answer_error(mock_agent_executor, mock_retriever):
    executor, pdf_tool = mock_agent_executor
    executor.invoke.side_effect = Exception("LLM Down")

    result = generate_answer("test question", "user123", "doc123")

    assert "I encountered an error while processing your request:" in result["answer"]
    assert "LLM Down" in result["answer"]

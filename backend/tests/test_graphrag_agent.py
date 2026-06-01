from unittest.mock import MagicMock, patch
from app.rag import agent


def test_generate_answer_appends_graph_context_without_changing_sources(monkeypatch):
    # Mock chunks
    chunks = [
        {
            "text": "Vector context",
            "filename": "doc.pdf",
            "page": 1,
            "score": 0.9,
            "confidence": 100.0,
        }
    ]

    # Mock the executor and the tool
    mock_executor = MagicMock()
    mock_executor.invoke.return_value = {"output": '{"answer":"Agent answer"}'}
    
    mock_pdf_tool = MagicMock()
    mock_pdf_tool.last_sources = chunks

    # Mock get_agent_executor to return our mocks
    monkeypatch.setattr(agent, "get_agent_executor", lambda *args, **kwargs: (mock_executor, mock_pdf_tool))

    result = agent.generate_answer("How are OpenAI and Microsoft related?", "user-1", "doc-1")

    assert result["answer"] == "Agent answer"
    assert result["sources"] == [
        {
            "text": "Vector context",
            "filename": "doc.pdf",
            "page": 1,
            "score": 0.9,
            "confidence": 100.0,
        }
    ]
    mock_executor.invoke.assert_called_once_with({"input": "How are OpenAI and Microsoft related?"})


def test_generate_answer_stream_appends_graph_context(monkeypatch):
    # Mock chunks
    chunks = [
        {
            "text": "Vector stream context",
            "filename": "doc.pdf",
            "page": 1,
            "score": 0.9,
            "confidence": 100.0,
        }
    ]

    # Mock the executor and the tool
    mock_executor = MagicMock()
    # Mock the stream method to yield chunks
    import json
    mock_executor.stream.return_value = iter([
        {"actions": [MagicMock(log="Thought: I should search. Action: pdf_search")]},
        {"intermediate_steps": []}, # This triggers source yielding in my implementation if last_sources is set
        {"output": 'Final Answer: {"answer":"Streamed answer"}'}
    ])
    
    mock_pdf_tool = MagicMock()
    mock_pdf_tool.last_sources = chunks

    monkeypatch.setattr(agent, "get_agent_executor", lambda *args, **kwargs: (mock_executor, mock_pdf_tool))

    events = list(agent.generate_answer_stream("OpenAI Microsoft", "user-1", "doc-1"))

    # Verify event types and data
    assert not any("Thinking" in e for e in events)
    assert any("Streamed answer" in e for e in events)
    assert any("Vector stream context" in e for e in events)
    assert events[-1] == f"data: {json.dumps({'type': 'done'})}\n\n"

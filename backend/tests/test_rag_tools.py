import pytest

from app.rag import tools
from app.rag.tools import (
    CALCULATOR_TOOL,
    TOOLS,
    WEB_SEARCH_TOOL,
    MathTool,
    PDFSearchTool,
    WebSearchTool,
    calculate_expression,
    execute_tool,
    web_search,
)


def test_calculator_tool_evaluates_basic_expression():
    assert calculate_expression("1000 - 250") == "750"
    assert calculate_expression("10 + 5 * 2") == "20"
    assert calculate_expression("10 / 4") == "2.5"


def test_calculator_tool_rejects_unsafe_expression():
    try:
        calculate_expression("__import__('os').system('echo x')")
    except ValueError as exc:
        assert "Invalid calculator expression" in str(
            exc
        ) or "Unsupported expression" in str(exc)
    else:
        assert False, "Unsafe expressions should not be evaluated"


def test_math_tool_run():
    tool = MathTool()
    result = tool.run({"expression": "12 * 3"})
    assert "Result: 36" in result


def test_math_tool_metadata():
    tool = MathTool()
    assert tool.name == "calculator"
    assert "mathematical calculations" in tool.description
    assert tool.args_schema is not None


def test_execute_tool_dispatches_calculator():
    assert execute_tool("calculator", {"expression": "(1000 - 250) * 0.2"}) == "150"


def test_execute_tool_dispatches_web_search(monkeypatch):
    calls = []

    def fake_web_search(query, max_results=5):
        calls.append((query, max_results))
        return "mock result"

    monkeypatch.setattr(tools, "web_search", fake_web_search)

    assert (
        execute_tool("web_search", {"query": "latest rag papers", "max_results": 2})
        == "mock result"
    )
    assert calls == [("latest rag papers", 2)]


@pytest.mark.parametrize(
    ("name", "arguments", "message"),
    [
        ("calculator", {"expression": ""}, "calculator tool requires"),
        ("web_search", {"query": "   "}, "web_search tool requires"),
        ("unknown", {}, "Unknown tool"),
    ],
)
def test_execute_tool_rejects_invalid_inputs(name, arguments, message):
    with pytest.raises(ValueError, match=message):
        execute_tool(name, arguments)


class FakeDDGS:
    def __init__(self, results=None, error=None):
        self.results = results or []
        self.error = error
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def text(self, query, max_results=5):
        self.calls.append((query, max_results))
        if self.error:
            raise self.error
        return self.results


def test_web_search_formats_duckduckgo_results(monkeypatch):
    fake_ddgs = FakeDDGS(
        results=[
            {
                "title": "First result",
                "href": "https://example.com/one",
                "body": "Useful snippet",
            },
            {
                "title": "Second result",
                "href": "https://example.com/two",
                "body": "Another snippet",
            },
        ]
    )
    monkeypatch.setattr(tools, "DDGS", lambda: fake_ddgs)

    result = web_search("agentic rag", max_results=2)

    assert fake_ddgs.calls == [("agentic rag", 2)]
    assert "1. **First result**" in result
    assert "URL: https://example.com/one" in result
    assert "Useful snippet" in result
    assert "2. **Second result**" in result


def test_web_search_handles_empty_results(monkeypatch):
    monkeypatch.setattr(tools, "DDGS", lambda: FakeDDGS(results=[]))

    assert web_search("missing topic") == "No web search results found."


def test_web_search_handles_provider_errors(monkeypatch):
    monkeypatch.setattr(
        tools, "DDGS", lambda: FakeDDGS(error=RuntimeError("network unavailable"))
    )

    assert web_search("agentic rag").startswith(
        "Web search failed: network unavailable"
    )


def test_web_search_tool_uses_shared_search_function(monkeypatch):
    monkeypatch.setattr(tools, "web_search", lambda query: f"searched: {query}")

    result = WebSearchTool().run({"query": "retrieval augmented generation"})

    assert result == "searched: retrieval augmented generation"


def test_pdf_search_tool_formats_chunks_and_graph_context(monkeypatch):
    chunks = [
        {"filename": "alpha.pdf", "page": 1, "text": "Alpha revenue grew by 12%."},
        {"filename": "beta.pdf", "page": 4, "text": "Beta margin narrowed."},
    ]
    retrieve_calls = []
    graph_calls = []

    def fake_retrieve(query, user_id, document_id=None):
        retrieve_calls.append((query, user_id, document_id))
        return chunks

    def fake_get_entity_context(query, user_id, document_id=None):
        graph_calls.append((query, user_id, document_id))
        return "Alpha -> acquired -> Beta"

    monkeypatch.setattr(tools, "retrieve", fake_retrieve)
    monkeypatch.setattr(tools, "get_entity_context", fake_get_entity_context)

    tool = PDFSearchTool(user_id="user-1", document_id="doc-1")
    result = tool.run({"query": "What happened to Alpha?"})

    assert retrieve_calls == [("What happened to Alpha?", "user-1", "doc-1")]
    assert graph_calls == [("What happened to Alpha?", "user-1", "doc-1")]
    assert tool.last_sources == chunks
    assert "Excerpt 1 (alpha.pdf, Page 1):\nAlpha revenue grew by 12%." in result
    assert "Excerpt 2 (beta.pdf, Page 4):\nBeta margin narrowed." in result
    assert "Additional Relationships found:\nAlpha -> acquired -> Beta" in result


def test_pdf_search_tool_skips_graph_lookup_when_no_chunks(monkeypatch):
    graph_called = False

    def fake_get_entity_context(*_args, **_kwargs):
        nonlocal graph_called
        graph_called = True
        return "unused"

    monkeypatch.setattr(tools, "retrieve", lambda **_kwargs: [])
    monkeypatch.setattr(tools, "get_entity_context", fake_get_entity_context)

    tool = PDFSearchTool(user_id="user-1")
    result = tool.run({"query": "missing"})

    assert result == "No relevant information found in the documents."
    assert tool.last_sources == []
    assert graph_called is False


def test_pdf_search_tool_returns_error_message_on_retriever_failure(monkeypatch):
    def failing_retrieve(**_kwargs):
        raise RuntimeError("vector store offline")

    monkeypatch.setattr(tools, "retrieve", failing_retrieve)

    result = PDFSearchTool(user_id="user-1").run({"query": "anything"})

    assert result == "Error searching documents: vector store offline"


def test_huggingface_tool_definitions_expose_expected_schemas():
    calculator_schema = CALCULATOR_TOOL.function.parameters
    web_schema = WEB_SEARCH_TOOL.function.parameters

    assert CALCULATOR_TOOL.function.name == "calculator"
    assert calculator_schema["required"] == ["expression"]
    assert calculator_schema["properties"]["expression"]["type"] == "string"

    assert WEB_SEARCH_TOOL.function.name == "web_search"
    assert web_schema["required"] == ["query"]
    assert web_schema["properties"]["query"]["type"] == "string"
    assert web_schema["properties"]["max_results"]["default"] == 5
    assert [tool.function.name for tool in TOOLS] == ["calculator", "web_search"]

from app.rag import agent


class FakeMessage:
    content = "Graph answer"


class FakeChoice:
    message = FakeMessage()


class FakeResponse:
    choices = [FakeChoice()]


class FakeClient:
    def __init__(self):
        self.messages = None

    def chat_completion(self, messages, **kwargs):
        self.messages = messages
        return FakeResponse()


def test_generate_answer_appends_graph_context_without_changing_sources(monkeypatch):
    client = FakeClient()
    chunks = [
        {
            "text": "Vector context",
            "filename": "doc.pdf",
            "page": 1,
            "score": 0.9,
            "confidence": 100.0,
        }
    ]

    monkeypatch.setattr(agent, "get_llm_client", lambda: client)
    monkeypatch.setattr(agent, "retrieve", lambda **kwargs: chunks)
    monkeypatch.setattr(
        agent,
        "get_entity_context",
        lambda **kwargs: "## Knowledge Graph Context\n- OpenAI is related to Microsoft on page 1.",
    )

    result = agent.generate_answer("How are OpenAI and Microsoft related?", "user-1", "doc-1")

    prompt = client.messages[1]["content"]
    assert "Vector context" in prompt
    assert "Knowledge Graph Context" in prompt
    assert result["sources"] == [
        {
            "text": "Vector context",
            "filename": "doc.pdf",
            "page": 1,
            "score": 0.9,
            "confidence": 100.0,
        }
    ]


def test_generate_answer_stream_appends_graph_context(monkeypatch):
    captured = {}

    class StreamingClient:
        def chat_completion(self, messages, **kwargs):
            captured["messages"] = messages
            return iter([])

    monkeypatch.setattr(agent, "get_llm_client", lambda: StreamingClient())
    monkeypatch.setattr(
        agent,
        "retrieve",
        lambda **kwargs: [
            {
                "text": "Vector stream context",
                "filename": "doc.pdf",
                "page": 1,
                "score": 0.9,
                "confidence": 100.0,
            }
        ],
    )
    monkeypatch.setattr(
        agent,
        "get_entity_context",
        lambda **kwargs: "## Knowledge Graph Context\n- OpenAI is related to Microsoft on page 1.",
    )

    events = list(agent.generate_answer_stream("OpenAI Microsoft", "user-1", "doc-1"))

    assert events[0].startswith("data:")
    assert "Knowledge Graph Context" in captured["messages"][1]["content"]

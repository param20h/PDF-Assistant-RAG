from app.rag import graph_builder, graph_retriever


class FakeEntity:
    def __init__(self, text, label):
        self.text = text
        self.label_ = label


class FakeDoc:
    def __init__(self, entities):
        self.ents = entities


class FakeNlp:
    def __call__(self, text):
        entities = []
        for value, label in (
            ("OpenAI", "ORG"),
            ("Microsoft", "ORG"),
            ("Azure", "PRODUCT"),
        ):
            if value in text:
                entities.append(FakeEntity(value, label))
        return FakeDoc(entities)


def _save_sample_graph(tmp_path, monkeypatch, user_id="user-1", document_id="doc-1"):
    monkeypatch.setattr(graph_builder.settings, "GRAPH_PERSIST_DIR", str(tmp_path))
    monkeypatch.setattr(graph_builder, "_nlp", FakeNlp())
    graph = graph_builder.build_graph(
        [
            {
                "text": "OpenAI works with Microsoft.",
                "page": 1,
                "chunk_index": 0,
            },
            {
                "text": "Microsoft deploys Azure.",
                "page": 2,
                "chunk_index": 1,
            },
        ]
    )
    graph_builder.save_graph(graph, user_id=user_id, document_id=document_id)


def test_get_entity_context_returns_one_hop_relationships(tmp_path, monkeypatch):
    _save_sample_graph(tmp_path, monkeypatch)

    context = graph_retriever.get_entity_context(
        query="How is OpenAI related to Microsoft?",
        user_id="user-1",
        document_id="doc-1",
    )

    assert "## Knowledge Graph Context" in context
    assert "OpenAI" in context
    assert "Microsoft" in context
    assert "page 1" in context


def test_get_entity_context_returns_empty_for_no_match(tmp_path, monkeypatch):
    _save_sample_graph(tmp_path, monkeypatch)

    context = graph_retriever.get_entity_context(
        query="What about Google?",
        user_id="user-1",
        document_id="doc-1",
    )

    assert context == ""


def test_get_entity_context_returns_empty_for_missing_graph(tmp_path, monkeypatch):
    monkeypatch.setattr(graph_builder.settings, "GRAPH_PERSIST_DIR", str(tmp_path))
    monkeypatch.setattr(graph_builder, "_nlp", FakeNlp())

    context = graph_retriever.get_entity_context(
        query="OpenAI",
        user_id="user-1",
        document_id="missing",
    )

    assert context == ""


def test_get_entity_context_isolates_users(tmp_path, monkeypatch):
    _save_sample_graph(tmp_path, monkeypatch, user_id="user-1", document_id="doc-1")

    context = graph_retriever.get_entity_context(
        query="OpenAI",
        user_id="user-2",
        document_id="doc-1",
    )

    assert context == ""

import json

from app.rag import graph_builder


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
            ("Ignored Date", "DATE"),
        ):
            if value in text:
                entities.append(FakeEntity(value, label))
        return FakeDoc(entities)


def test_extract_entities_filters_configured_labels(monkeypatch):
    monkeypatch.setattr(graph_builder, "_nlp", FakeNlp())

    entities = graph_builder.extract_entities("OpenAI works with Microsoft on Ignored Date")

    assert {entity.text for entity in entities} == {"OpenAI", "Microsoft"}
    assert {entity.label for entity in entities} == {"ORG"}


def test_build_graph_tracks_entity_edges_and_weights(monkeypatch):
    monkeypatch.setattr(graph_builder, "_nlp", FakeNlp())
    chunks = [
        {
            "text": "OpenAI works with Microsoft.",
            "page": 1,
            "chunk_index": 0,
        },
        {
            "text": "OpenAI and Microsoft use Azure.",
            "page": 2,
            "chunk_index": 1,
        },
    ]

    graph = graph_builder.build_graph(chunks)

    openai_id = "ORG:openai"
    microsoft_id = "ORG:microsoft"
    azure_id = "PRODUCT:azure"
    assert graph.nodes[openai_id]["name"] == "OpenAI"
    assert graph.nodes[openai_id]["pages"] == [1, 2]
    assert graph[openai_id][microsoft_id]["weight"] == 2
    assert graph[openai_id][microsoft_id]["pages"] == [1, 2]
    assert graph.has_edge(microsoft_id, azure_id)


def test_save_load_and_delete_graph_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(graph_builder.settings, "GRAPH_PERSIST_DIR", str(tmp_path))
    graph = graph_builder.build_graph([])
    graph.add_node("ORG:openai", name="OpenAI", label="ORG", mentions=1, pages=[1], chunks=[0])

    path = graph_builder.save_graph(graph, user_id="user-1", document_id="doc-1")
    payload = json.loads(path.read_text(encoding="utf-8"))
    loaded = graph_builder.load_graph(user_id="user-1", document_id="doc-1")

    assert payload["metadata"]["document_id"] == "doc-1"
    assert loaded.nodes["ORG:openai"]["name"] == "OpenAI"

    graph_builder.delete_graph(user_id="user-1", document_id="doc-1")
    assert not path.exists()


def test_empty_chunks_produce_empty_graph(monkeypatch):
    monkeypatch.setattr(graph_builder, "_nlp", FakeNlp())

    graph = graph_builder.build_graph([])

    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0

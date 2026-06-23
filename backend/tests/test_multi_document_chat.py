from unittest.mock import MagicMock

from app.rag import retriever
from app.models import Document


# ── Retrieval: document_ids reaches both vector and BM25 (dev's direct-call retrieve) ──

def _mock_db(monkeypatch, doc_rows):
    mock_db = MagicMock()
    mock_db.__enter__.return_value = mock_db
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value.all.return_value = doc_rows
    monkeypatch.setattr("app.database.SessionLocal", lambda: mock_db)


def test_retrieve_forwards_document_ids_to_vector_and_bm25(monkeypatch):
    _mock_db(monkeypatch, [("doc-a",), ("doc-b",)])

    seen = {"vector": "unset", "bm25": "unset"}

    monkeypatch.setattr(retriever, "transform_query", lambda _q: ["q"])
    monkeypatch.setattr(retriever, "embed_query", lambda q: f"embedding:{q}")
    monkeypatch.setattr(retriever, "get_reranker", lambda: None)

    def fake_query_chunks(query_embedding, user_id, document_id=None, document_ids=None, top_k=10):
        seen["vector"] = document_ids
        return [{"id": "v1", "text": "vec", "filename": "a.pdf", "page": 1, "score": 0.5}]

    def fake_query_bm25(query, user_id, document_id=None, document_ids=None, top_k=10):
        seen["bm25"] = document_ids
        return [{"id": "b1", "text": "bm", "filename": "b.pdf", "page": 1, "score": 0.5}]

    monkeypatch.setattr(retriever, "query_chunks", fake_query_chunks)
    monkeypatch.setattr("app.rag.bm25.query_bm25", fake_query_bm25)

    retriever.retrieve("question", user_id="user-1", document_ids=["doc-a", "doc-b"])

    assert seen["vector"] == ["doc-a", "doc-b"]
    # bm25 only runs when hybrid search is enabled; if it ran, it must have received the ids
    if seen["bm25"] != "unset":
        assert seen["bm25"] == ["doc-a", "doc-b"]


def test_retrieve_single_document_leaves_document_ids_none(monkeypatch):
    _mock_db(monkeypatch, [("doc-a",)])

    seen = {"vector_id": "unset", "vector_ids": "unset"}

    monkeypatch.setattr(retriever, "transform_query", lambda _q: ["q"])
    monkeypatch.setattr(retriever, "embed_query", lambda q: f"embedding:{q}")
    monkeypatch.setattr(retriever, "get_reranker", lambda: None)

    def fake_query_chunks(query_embedding, user_id, document_id=None, document_ids=None, top_k=10):
        seen["vector_id"] = document_id
        seen["vector_ids"] = document_ids
        return [{"id": "v1", "text": "vec", "filename": "a.pdf", "page": 1, "score": 0.5}]

    monkeypatch.setattr(retriever, "query_chunks", fake_query_chunks)

    retriever.retrieve("question", user_id="user-1", document_id="doc-a")

    assert seen["vector_id"] == "doc-a"
    assert seen["vector_ids"] is None


# ── Prompt: comparison guidance only when more than one document ──

def test_comparison_guidance_present_only_for_multiple_documents(monkeypatch):
    from app.rag import agent
    from app.rag.prompts import MULTI_DOC_COMPARISON_GUIDANCE

    captured = {}

    class FakeLLM:
        def __init__(self, *a, **k):
            pass

    def capture_prompt(llm, tools, prompt):
        captured["template"] = prompt.template
        return "agent"

    monkeypatch.setattr(agent, "get_llm_client", lambda hf_token=None: FakeLLM())
    monkeypatch.setattr(agent, "create_react_agent", capture_prompt)
    monkeypatch.setattr(agent, "AgentExecutor", lambda **kwargs: kwargs)

    agent.get_agent_executor(user_id="user-1", document_ids=["doc-a", "doc-b"])
    assert MULTI_DOC_COMPARISON_GUIDANCE.strip() in captured["template"]

    captured.clear()
    agent.get_agent_executor(user_id="user-1", document_id="doc-a")
    assert MULTI_DOC_COMPARISON_GUIDANCE.strip() not in captured["template"]


# ── Route guard: ownership + readiness for document_ids ──

def test_chat_ask_multi_doc_success(client, auth_headers, ready_document, db_session, user, monkeypatch):
    second = Document(
        user_id=user.id,
        filename="second.txt",
        original_name="second.txt",
        file_size=128,
        status="ready",
    )
    db_session.add(second)
    db_session.commit()
    db_session.refresh(second)

    monkeypatch.setattr(
        "app.routes.chat.generate_answer",
        lambda question, user_id, document_id=None, document_ids=None, **kwargs: {
            "answer": "Across both docs",
            "sources": [],
        },
    )

    response = client.post(
        "/api/v1/chat/ask",
        headers=auth_headers,
        json={"question": "Compare them", "document_ids": [ready_document.id, second.id]},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Across both docs"


def test_chat_ask_multi_doc_rejects_missing_document(client, auth_headers, ready_document):
    response = client.post(
        "/api/v1/chat/ask",
        headers=auth_headers,
        json={"question": "Compare", "document_ids": [ready_document.id, "missing-doc-id"]},
    )
    assert response.status_code == 404


def test_chat_ask_multi_doc_rejects_not_ready_document(client, auth_headers, ready_document, pending_document):
    response = client.post(
        "/api/v1/chat/ask",
        headers=auth_headers,
        json={"question": "Compare", "document_ids": [ready_document.id, pending_document.id]},
    )
    assert response.status_code == 400


def test_chat_ask_multi_doc_rejects_other_users_document(client, auth_headers, ready_document, db_session, other_user):
    other_doc = Document(
        user_id=other_user.id,
        filename="other.txt",
        original_name="other.txt",
        file_size=64,
        status="ready",
    )
    db_session.add(other_doc)
    db_session.commit()
    db_session.refresh(other_doc)

    response = client.post(
        "/api/v1/chat/ask",
        headers=auth_headers,
        json={"question": "Compare", "document_ids": [ready_document.id, other_doc.id]},
    )
    # not owned -> treated as missing
    assert response.status_code == 404
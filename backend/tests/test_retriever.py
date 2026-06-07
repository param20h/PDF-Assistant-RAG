from app.rag import retriever


def test_transform_query_includes_original_and_dedupes(monkeypatch):
    monkeypatch.setattr(
        retriever,
        "_generate_query_variants",
        lambda _query: [
            "How do taxes work?",
            "how do taxes work?",
            "How does healthcare work?",
            "healthcare overview",
        ],
    )

    queries = retriever.transform_query("How do taxes and healthcare work?")

    assert queries == [
        "How do taxes and healthcare work?",
        "How do taxes work?",
        "How does healthcare work?",
        "healthcare overview",
    ]


def test_retrieve_fans_out_transformed_queries_and_merges_duplicates(monkeypatch):
    searched_queries = []

    monkeypatch.setattr(retriever, "transform_query", lambda _query: ["taxes", "healthcare"])
    monkeypatch.setattr(retriever, "embed_query", lambda query: f"embedding:{query}")
    monkeypatch.setattr(retriever, "get_reranker", lambda: None)

    # Mock SessionLocal and Document
    class MockDoc:
        id = "policy.pdf"

    class MockQuery:
        def filter(self, *args, **kwargs):
            return self
        def all(self):
            return [MockDoc()]

    class MockSession:
        def query(self, *args, **kwargs):
            return MockQuery()
        def close(self):
            pass

    monkeypatch.setattr("app.database.SessionLocal", lambda: MockSession())

    def fake_query_chunks(query_embedding, user_id, document_id=None, document_ids=None, top_k=10):
        searched_queries.append(query_embedding)
        if query_embedding == "embedding:taxes":
            return [
                {
                    "id": "shared",
                    "text": "Shared chunk",
                    "filename": "policy.pdf",
                    "page": 1,
                    "score": 0.2,
                },
                {
                    "id": "taxes",
                    "text": "Tax chunk",
                    "filename": "policy.pdf",
                    "page": 2,
                    "score": 0.7,
                },
            ]

        return [
            {
                "id": "shared",
                "text": "Shared chunk",
                "filename": "policy.pdf",
                "page": 1,
                "score": 0.9,
            },
            {
                "id": "healthcare",
                "text": "Healthcare chunk",
                "filename": "policy.pdf",
                "page": 3,
                "score": 0.8,
            },
        ]

    monkeypatch.setattr(retriever, "query_chunks", fake_query_chunks)

    chunks = retriever.retrieve("How do taxes and healthcare work?", user_id="user-1")

    assert searched_queries == ["embedding:taxes", "embedding:healthcare"]
    assert [chunk["id"] for chunk in chunks] == ["shared", "taxes", "healthcare"]
    assert chunks[0]["score"] == 1.0
    assert chunks[0]["confidence"] == 100.0


def test_retrieve_excludes_soft_deleted_documents(db_session, user, monkeypatch):
    from app.models import Document
    from app.rag import retriever

    # Create one active document and one deleted document
    active_doc = Document(
        id="active-doc-id",
        user_id=user.id,
        filename="active.pdf",
        original_name="active.pdf",
        is_deleted=False,
    )
    deleted_doc = Document(
        id="deleted-doc-id",
        user_id=user.id,
        filename="deleted.pdf",
        original_name="deleted.pdf",
        is_deleted=True,
    )
    db_session.add(active_doc)
    db_session.add(deleted_doc)
    db_session.commit()

    monkeypatch.setattr("app.database.SessionLocal", lambda: db_session)
    monkeypatch.setattr(retriever, "transform_query", lambda _query: ["query"])
    monkeypatch.setattr(retriever, "embed_query", lambda query: "embedding")
    monkeypatch.setattr(retriever, "get_reranker", lambda: None)

    captured_doc_ids = []
    def fake_query_chunks(query_embedding, user_id, document_id=None, document_ids=None, top_k=10):
        nonlocal captured_doc_ids
        captured_doc_ids = document_ids
        return []

    monkeypatch.setattr(retriever, "query_chunks", fake_query_chunks)
    monkeypatch.setattr(retriever.CustomBM25Retriever, "_get_relevant_documents", lambda *args, **kwargs: [])

    retriever.retrieve("test query", user_id=user.id)

    # Should only query for the active document ID
    assert captured_doc_ids == ["active-doc-id"]


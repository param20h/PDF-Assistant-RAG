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

    def fake_query_chunks(query_embedding, user_id, document_id=None, top_k=10):
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
    assert [chunk["id"] for chunk in chunks] == ["shared", "healthcare", "taxes"]
    assert chunks[0]["score"] == 0.9
    assert chunks[0]["confidence"] == 100.0

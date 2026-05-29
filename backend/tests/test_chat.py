def test_chat_ask_success(client, auth_headers, ready_document, monkeypatch):
    monkeypatch.setattr(
        "app.routes.chat.generate_answer",
        lambda question, user_id, document_id=None: {
            "answer": "Mocked answer",
            "sources": [
                {
                    "text": "Mock source",
                    "filename": "ready.txt",
                    "page": 1,
                    "score": 0.99,
                    "confidence": 99.0,
                }
            ],
        },
    )

    response = client.post(
        "/api/v1/chat/ask",
        headers=auth_headers,
        json={"question": "What is in the doc?", "document_id": ready_document.id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Mocked answer"
    assert payload["document_id"] == ready_document.id
    assert payload["sources"][0]["filename"] == "ready.txt"


def test_chat_ask_document_not_found(client, auth_headers):
    response = client.post(
        "/api/v1/chat/ask",
        headers=auth_headers,
        json={"question": "Missing doc?", "document_id": "missing-doc-id"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


def test_chat_ask_document_not_ready(client, auth_headers, pending_document):
    response = client.post(
        "/api/v1/chat/ask",
        headers=auth_headers,
        json={"question": "Pending doc?", "document_id": pending_document.id},
    )

    assert response.status_code == 400
    assert "Document is still pending" in response.json()["detail"]

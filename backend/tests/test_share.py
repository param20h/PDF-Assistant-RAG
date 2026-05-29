def test_share_link_creation_success(client, auth_headers, assistant_message):
    response = client.post(
        f"/api/v1/chat/share/{assistant_message.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message_id"] == assistant_message.id
    assert payload["share_url"] == f"/share?message_id={assistant_message.id}"


def test_share_link_unauthorized_for_other_users_message(client, auth_headers, other_user_assistant_message):
    response = client.post(
        f"/api/v1/chat/share/{other_user_assistant_message.id}",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Message not found"


def test_cannot_share_user_message(client, auth_headers, user_message):
    response = client.post(
        f"/api/v1/chat/share/{user_message.id}",
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only assistant messages can be shared"


def test_public_fetch_fails_before_share(client, assistant_message):
    response = client.get(f"/api/v1/chat/share/{assistant_message.id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Shared answer not found"


def test_public_fetch_shared_answer_success_after_share(client, auth_headers, assistant_message):
    share_response = client.post(
        f"/api/v1/chat/share/{assistant_message.id}",
        headers=auth_headers,
    )
    assert share_response.status_code == 200

    response = client.get(f"/api/v1/chat/share/{assistant_message.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == assistant_message.id
    assert payload["content"] == "Shared assistant answer"
    assert len(payload["sources"]) == 1
    assert payload["sources"][0]["filename"] == "file.txt"


def test_missing_message_returns_404(client):
    response = client.get("/api/v1/chat/share/missing-message-id")

    assert response.status_code == 404
    assert response.json()["detail"] == "Shared answer not found"

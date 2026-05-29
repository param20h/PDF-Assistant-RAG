def test_api_health(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["version"] == "2.0.0"


def test_protected_documents_list_requires_auth(client):
    response = client.get("/api/v1/documents/")

    assert response.status_code in (401, 403)


def test_documents_list_authenticated(client, auth_headers, ready_document):
    response = client.get("/api/v1/documents/", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == ready_document.id
    assert payload["items"][0]["original_name"] == "ready.txt"


def test_upload_rejects_unsupported_extension_before_deep_validation(client, auth_headers):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("payload.exe", b"binary-data", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "not supported" in response.json()["detail"]

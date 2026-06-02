def test_register_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["message"] == "Registration successful. Please check your email to verify your account before logging in."
    assert payload["email"] == "newuser@example.com"
    assert payload["verification_url"].startswith("/verify-email?token=")


def test_register_duplicate_email_or_username_conflict(client):
    payload = {
        "username": "dupuser",
        "email": "dup@example.com",
        "password": "password123",
    }
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    duplicate_email = client.post(
        "/api/v1/auth/register",
        json={**payload, "username": "anotheruser"},
    )
    assert duplicate_email.status_code == 409
    assert duplicate_email.json()["detail"] == "Email already registered"

    duplicate_username = client.post(
        "/api/v1/auth/register",
        json={**payload, "email": "another@example.com"},
    )
    assert duplicate_username.status_code == 409
    assert duplicate_username.json()["detail"] == "Username already taken"


def test_login_success(client, user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "password123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["user"]["username"] == user.username


def test_login_invalid_password(client, user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_auth_me_requires_auth(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code in (401, 403)


def test_refresh_token_success(client, refresh_token):
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["token_type"] == "bearer"


def test_update_hf_token_success(client, auth_headers):
    response = client.put(
        "/api/v1/auth/hf-token",
        json={"hf_token": "hf_new_token_value"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["hf_token"] == "hf_new_token_value"


def test_update_hf_token_requires_auth(client):
    response = client.put(
        "/api/v1/auth/hf-token",
        json={"hf_token": "hf_unauth"},
    )

    assert response.status_code in (401, 403)


def test_hf_token_appears_in_user_response(client, auth_headers, user, db_session):
    # First update the token
    put_resp = client.put(
        "/api/v1/auth/hf-token",
        json={"hf_token": "hf_persist_token"},
        headers=auth_headers,
    )
    assert put_resp.status_code == 200

    # Then verify it shows up in GET /me
    me_resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["hf_token"] == "hf_persist_token"

    # Verify encryption at rest in the database directly
    from sqlalchemy import text
    row = db_session.execute(text("SELECT hf_token FROM users WHERE id = :id"), {"id": user.id}).fetchone()
    stored_token = row[0]
    assert stored_token is not None
    assert stored_token != "hf_persist_token"


from unittest.mock import patch, AsyncMock, MagicMock
import urllib.parse

def test_huggingface_login(client):
    from app.config import get_settings
    settings = get_settings()
    settings.HF_CLIENT_ID = "test-client-id"
    settings.HF_REDIRECT_URI = "http://localhost:8000/api/v1/auth/callback/huggingface"

    response = client.get("/api/v1/auth/login/huggingface")
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "test-client-id" in data["url"]
    assert "oauth_state" in response.cookies


@patch("httpx.AsyncClient.post")
@patch("httpx.AsyncClient.get")
def test_huggingface_callback_success(mock_get, mock_post, client):
    from app.config import get_settings
    settings = get_settings()
    settings.HF_CLIENT_ID = "test-client-id"
    settings.HF_CLIENT_SECRET = "test-client-secret"
    settings.HF_REDIRECT_URI = "http://localhost:8000/api/v1/auth/callback/huggingface"

    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {"access_token": "hf-access-token"}
    mock_post.return_value = mock_post_resp

    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {
        "email": "hfuser@example.com",
        "preferred_username": "hfuser"
    }
    mock_get.return_value = mock_get_resp

    login_response = client.get("/api/v1/auth/login/huggingface")
    state_cookie = login_response.cookies["oauth_state"]
    url = login_response.json()["url"]
    parsed = urllib.parse.urlparse(url)
    queries = urllib.parse.parse_qs(parsed.query)
    state_param = queries["state"][0]

    client.cookies.set("oauth_state", state_cookie)
    callback_response = client.get(
        f"/api/v1/auth/callback/huggingface?code=hf-code&state={state_param}",
        follow_redirects=False
    )

    assert callback_response.status_code == 307
    assert "/dashboard" in callback_response.headers["location"]
    assert "access_token" in callback_response.cookies
    assert "refresh_token" in callback_response.cookies


def test_huggingface_callback_invalid_state(client):
    response = client.get(
        "/api/v1/auth/callback/huggingface?code=hf-code&state=invalid-state",
        cookies={"oauth_state": "actual-state"}
    )
    assert response.status_code == 400
    assert "State verification failed" in response.json()["detail"]


def test_huggingface_logout(client):
    response = client.post(
        "/api/v1/auth/logout",
        cookies={"access_token": "token-value", "refresh_token": "refresh-value"}
    )
    assert response.status_code == 200
    assert response.cookies.get("access_token") in (None, "")
    assert response.cookies.get("refresh_token") in (None, "")

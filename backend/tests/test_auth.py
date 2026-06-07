from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings


VALID_TEST_PASSWORD = "Password1!"


def test_register_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": VALID_TEST_PASSWORD,
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
        "password": VALID_TEST_PASSWORD,
    }
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    duplicate_email = client.post(
        "/api/v1/auth/register",
        json={**payload, "username": "anotheruser"},
    )
    assert duplicate_email.status_code == 409
    assert duplicate_email.json()["error"]["message"] == "Email already registered"

    duplicate_username = client.post(
        "/api/v1/auth/register",
        json={**payload, "email": "another@example.com"},
    )
    assert duplicate_username.status_code == 409
    assert duplicate_username.json()["error"]["message"] == "Username already taken"


def test_register_rejects_weak_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "weakpassuser",
            "email": "weakpass@example.com",
            "password": "123456",
        },
    )

    assert response.status_code == 422
    errors = response.json()["error"]["details"]["errors"]
    messages = " ".join(item["message"] for item in errors)
    assert "uppercase" in messages.lower() or "8 characters" in messages.lower()


def test_register_rejects_password_missing_special_character(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "specialcharuser",
            "email": "specialchar@example.com",
            "password": "Password1",
        },
    )

    assert response.status_code == 422
    errors = response.json()["error"]["details"]["errors"]
    messages = " ".join(item["message"] for item in errors).lower()
    assert "special character" in messages


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
    assert response.json()["error"]["message"] == "Invalid email or password"


def test_login_invalid_email(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "password123"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid email or password"


def test_auth_me_success(client, auth_headers, user):
    response = client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(user.id)
    assert payload["username"] == user.username
    assert payload["email"] == user.email


def test_auth_me_requires_auth(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code in (401, 403)


def test_auth_me_rejects_expired_token(client, user):
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expired_token = jwt.encode(
        {
            "sub": str(user.id),
            "type": "access",
            "exp": now - timedelta(minutes=1),
            "iat": now - timedelta(minutes=2),
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


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

def test_update_user_info_rejects_duplicate_email(client, auth_headers, other_user):
    response = client.put(
        "/api/v1/auth/update",
        json={"email": other_user.email},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Email already exists"
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
    assert "State verification failed" in response.json()["error"]["message"]


def test_huggingface_logout(client):
    response = client.post(
        "/api/v1/auth/logout",
        cookies={"access_token": "token-value", "refresh_token": "refresh-value"}
    )
    assert response.status_code == 200
    assert response.cookies.get("access_token") in (None, "")
    assert response.cookies.get("refresh_token") in (None, "")


def test_google_drive_connect_returns_auth_url(client, auth_headers, monkeypatch):
    from app.routes import auth as auth_routes

    class FakeFlow:
        def authorization_url(self, **kwargs):
            assert kwargs["access_type"] == "offline"
            assert kwargs["prompt"] == "consent"
            return "https://accounts.google.com/o/oauth2/auth?state=signed-state", "signed-state"

    monkeypatch.setattr(auth_routes.settings, "GOOGLE_CLIENT_ID", "google-client-id")
    monkeypatch.setattr(auth_routes.settings, "GOOGLE_CLIENT_SECRET", "google-client-secret")
    monkeypatch.setattr(auth_routes, "_google_drive_flow", lambda state: FakeFlow())

    response = client.get("/api/v1/auth/google-drive/connect", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["auth_url"].startswith("https://accounts.google.com")


def test_google_drive_status_reflects_stored_token(client, auth_headers, user, db_session):
    initial = client.get("/api/v1/auth/google-drive/status", headers=auth_headers)
    assert initial.status_code == 200
    assert initial.json() == {"connected": False}

    user.google_refresh_token = "google-refresh-token"
    db_session.commit()

    connected = client.get("/api/v1/auth/google-drive/status", headers=auth_headers)
    assert connected.status_code == 200
    assert connected.json() == {"connected": True}


def test_google_drive_callback_stores_encrypted_refresh_token(client, user, db_session, monkeypatch):
    from app.routes import auth as auth_routes
    from sqlalchemy import text

    class FakeCredentials:
        refresh_token = "google-refresh-token"

    class FakeFlow:
        credentials = FakeCredentials()

        def fetch_token(self, code):
            assert code == "oauth-code"

    monkeypatch.setattr(auth_routes.settings, "GOOGLE_CLIENT_ID", "google-client-id")
    monkeypatch.setattr(auth_routes.settings, "GOOGLE_CLIENT_SECRET", "google-client-secret")
    monkeypatch.setattr(auth_routes, "_google_drive_flow", lambda state: FakeFlow())

    state = auth_routes._create_google_drive_state(user.id)
    response = client.get(
        "/api/v1/auth/google-drive/callback",
        params={"code": "oauth-code", "state": state},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "Google Drive connected" in response.text

    db_session.refresh(user)
    assert user.google_refresh_token == "google-refresh-token"

    row = db_session.execute(text("SELECT google_refresh_token FROM users WHERE id = :id"), {"id": user.id}).fetchone()
    stored_token = row[0]
    assert stored_token is not None
    assert stored_token != "google-refresh-token"


def test_google_drive_disconnect_removes_token(client, auth_headers, user, db_session):
    user.google_refresh_token = "google-refresh-token"
    db_session.commit()

    response = client.delete("/api/v1/auth/google-drive/disconnect", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"connected": False}

    db_session.refresh(user)
    assert user.google_refresh_token is None

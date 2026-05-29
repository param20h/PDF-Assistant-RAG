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
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["user"]["email"] == "newuser@example.com"


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

    assert response.status_code == 403


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

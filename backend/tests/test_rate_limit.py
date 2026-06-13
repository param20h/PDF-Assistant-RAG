"""
Unit tests for rate limiting middleware and identifier resolution (#445).

Verifies key function fallback resolutions (User ID vs IP Address), route
attribute assignments, and that the global handler intercepts limit breaches
to return a 429 status code.
"""
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from app.auth import create_access_token
from app.rate_limit import CHAT_QUERY_RATE_LIMIT, rate_limit_key_func
from app.routes.chat import ask_question, ask_question_stream
from app.main import app


class DummyRequest:
    def __init__(self, headers=None):
        self.headers = headers or {}
        self.client = SimpleNamespace(host="203.0.113.10")


# ── Your Original Key Resolution & Route Tests ───────────────────────────────

def test_rate_limit_key_prefers_authenticated_user_id():
    token = create_access_token("user-123")

    key = rate_limit_key_func(
        DummyRequest(headers={"authorization": f"Bearer {token}"})
    )

    assert key == "user:user-123"


def test_rate_limit_key_falls_back_to_client_ip():
    key = rate_limit_key_func(DummyRequest())

    assert key.startswith("ip:")


def test_chat_endpoints_use_required_rate_limit():
    assert CHAT_QUERY_RATE_LIMIT == "15/minute"
    assert ask_question.__rate_limits__ == [CHAT_QUERY_RATE_LIMIT]
    assert ask_question_stream.__rate_limits__ == [CHAT_QUERY_RATE_LIMIT]


# ── Middleware 429 Response Verification ──────────────────────────────────────

def test_rate_limit_handler_returns_429(client: TestClient):
    """
    Verify that hitting an endpoint that triggers a RateLimitExceeded exception
    correctly triggers the global handler, returning a 429 status code and the
    exact JSON error layout specified in app/main.py.
    """
    # Temporarily mount a mock endpoint on the app to force a rate limit breach
    @app.get("/api/v1/test-rate-limiting-trigger-429")
    def trigger_rate_limit():
        raise RateLimitExceeded("Too Many Requests")

    response = client.get("/api/v1/test-rate-limiting-trigger-429")
    
    # Verify the 429 status code requirement
    assert response.status_code == 429
    
    # Verify the specific JSON payload structure from app/main.py
    json_data = response.json()
    assert "error" in json_data
    assert json_data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Rate limit exceeded. Please try again later." in json_data["error"]["message"]
    assert "request_id" in json_data["error"]
    assert isinstance(json_data["error"]["details"], dict)

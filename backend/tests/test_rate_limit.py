from types import SimpleNamespace

from app.auth import create_access_token
from app.rate_limit import CHAT_QUERY_RATE_LIMIT, rate_limit_key_func
from app.routes.chat import ask_question, ask_question_stream


class DummyRequest:
    def __init__(self, headers=None):
        self.headers = headers or {}
        self.client = SimpleNamespace(host="203.0.113.10")


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

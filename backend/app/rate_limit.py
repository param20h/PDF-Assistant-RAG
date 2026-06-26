"""
SlowAPI rate limiting configuration.
"""
from fastapi import Request
from limits import parse
from limits.storage import storage_from_string
from limits.strategies import FixedWindowRateLimiter
from slowapi import Limiter
from slowapi.util import get_remote_address


CHAT_QUERY_RATE_LIMIT = "15/minute"
LOGIN_RATE_LIMIT = "5/minute"
REGISTER_RATE_LIMIT = "3/minute"


def rate_limit_key_func(request: Request) -> str:
    """Use authenticated user id when available, otherwise fall back to client IP."""
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        try:
            from app.auth import decode_token

            user_id = decode_token(authorization.split(" ", 1)[1])
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=rate_limit_key_func)


# SlowAPI's @limiter.limit decorator only wraps standard HTTP route handlers
# (e.g. POST /chat/ask, /chat/ask/stream in app/routes/chat.py) — it has no
# WebSocket support, so it can't be applied to the /chat/ws endpoint. This
# dedicated strategy + in-memory storage backs a manual check that enforces
# the same CHAT_QUERY_RATE_LIMIT, keyed the same way ("user:<id>") that
# rate_limit_key_func uses for the HTTP routes.
_chat_ws_rate_limit_item = parse(CHAT_QUERY_RATE_LIMIT)
_chat_ws_storage = storage_from_string("memory://")
_chat_ws_limiter = FixedWindowRateLimiter(_chat_ws_storage)


def check_chat_ws_rate_limit(user_id: str) -> bool:
    """Consume one hit against the /chat/ws rate-limit bucket for a user.

    Mirrors CHAT_QUERY_RATE_LIMIT (15/minute), which @limiter.limit enforces
    on /chat/ask and /chat/ask/stream, for the WebSocket transport that the
    SlowAPI decorator can't reach.

   Returns True if the request is within the limit, False if the caller has
    exceeded it and the request should be rejected.
    """
    return _chat_ws_limiter.hit(_chat_ws_rate_limit_item, f"user:{user_id}")
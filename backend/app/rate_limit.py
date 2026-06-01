"""
SlowAPI rate limiting configuration.
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


CHAT_QUERY_RATE_LIMIT = "15/minute"


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

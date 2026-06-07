import asyncio
import json
from unittest.mock import Mock

import pytest

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded

from app.exceptions import (
    AppException,
    ConflictException,
    ExternalServiceException,
    ForbiddenException,
    NotFoundException,
    RateLimitException,
    UnauthorizedException,
    UnsafePromptException,
    ValidationException,
)
from app.main import (
    app_exception_handler,
    rate_limit_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)


def _mock_request(request_id="test-123"):
    request = Mock()
    request.state = Mock(request_id=request_id)
    return request


# ──────────────────────────────────────────────
# Exception class instantiation (uncovered lines)
# ──────────────────────────────────────────────


def test_app_exception_defaults():
    exc = AppException("CODE", "msg", 500)
    assert exc.code == "CODE"
    assert exc.message == "msg"
    assert exc.status_code == 500
    assert exc.details == {}


def test_app_exception_with_details():
    exc = AppException("CODE", "msg", 400, {"key": "val"})
    assert exc.details == {"key": "val"}


def test_not_found_with_identifier():
    exc = NotFoundException("document", "42")
    assert exc.code == "DOCUMENT_NOT_FOUND"
    assert "42" in exc.message
    assert exc.status_code == 404
    assert exc.details == {"document": "42"}


def test_not_found_without_identifier():
    exc = NotFoundException("user")
    assert exc.code == "USER_NOT_FOUND"
    assert exc.status_code == 404
    assert exc.details == {}


def test_unauthorized_default():
    exc = UnauthorizedException()
    assert exc.code == "UNAUTHORIZED"
    assert exc.status_code == 401


def test_forbidden_default():
    exc = ForbiddenException()
    assert exc.code == "FORBIDDEN"
    assert exc.status_code == 403


def test_conflict():
    exc = ConflictException("Username taken")
    assert exc.code == "CONFLICT"
    assert exc.status_code == 409
    assert exc.message == "Username taken"


def test_conflict_with_details():
    exc = ConflictException("Conflict", {"field": "username"})
    assert exc.details == {"field": "username"}


def test_validation():
    exc = ValidationException("bad input", {"field": "email"})
    assert exc.code == "VALIDATION_ERROR"
    assert exc.status_code == 400
    assert exc.details == {"field": "email"}


def test_rate_limit():
    exc = RateLimitException()
    assert exc.code == "RATE_LIMIT_EXCEEDED"
    assert exc.status_code == 429
    assert "Rate limit" in exc.message


def test_external_service():
    exc = ExternalServiceException("openai", "key expired")
    assert exc.code == "OPENAI_ERROR"
    assert exc.status_code == 502
    assert exc.details == {"service": "openai"}


def test_external_service_default_message():
    exc = ExternalServiceException("stripe")
    assert "stripe" in exc.message


def test_unsafe_prompt():
    exc = UnsafePromptException()
    assert exc.code == "UNSAFE_PROMPT"
    assert exc.status_code == 400
    assert "prohibited" in exc.message


def test_unsafe_prompt_custom_message():
    exc = UnsafePromptException("Custom block message")
    assert exc.message == "Custom block message"


# ──────────────────────────────────────────────
# Exception handler response format (uncovered lines)
# ──────────────────────────────────────────────


def test_app_exception_handler():
    request = _mock_request()
    exc = AppException("NOT_FOUND", "nope", 404, {"id": "1"})
    response = asyncio.run(app_exception_handler(request, exc))
    assert response.status_code == 404
    body = json.loads(response.body)
    assert body == {
        "error": {
            "code": "NOT_FOUND",
            "message": "nope",
            "details": {"id": "1"},
            "request_id": "test-123",
        }
    }


def test_app_exception_handler_no_request_id():
    request = Mock()
    response = asyncio.run(
        app_exception_handler(request, AppException("E", "e", 500))
    )
    body = json.loads(response.body)
    assert body["error"]["request_id"] is None


def test_rate_limit_handler():
    request = _mock_request()
    exc = RateLimitExceeded()
    response = asyncio.run(rate_limit_handler(request, exc))
    assert response.status_code == 429
    body = json.loads(response.body)
    assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert body["error"]["request_id"] == "test-123"


def test_validation_exception_handler():
    request = _mock_request()
    exc = RequestValidationError(
        errors=[
            {
                "loc": ("body", "email"),
                "msg": "field required",
                "type": "value_error",
            }
        ]
    )
    response = asyncio.run(validation_exception_handler(request, exc))
    assert response.status_code == 422
    body = json.loads(response.body)
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]["errors"][0]["field"] == "body -> email"


def test_unhandled_exception_handler(monkeypatch):
    monkeypatch.setattr("app.main.settings.DEBUG", False)
    request = _mock_request()
    exc = ValueError("unexpected")
    response = asyncio.run(unhandled_exception_handler(request, exc))
    assert response.status_code == 500
    body = json.loads(response.body)
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "An unexpected error occurred"


def test_unhandled_exception_handler_debug_raises(monkeypatch):
    monkeypatch.setattr("app.main.settings.DEBUG", True)
    request = _mock_request()
    with pytest.raises(ValueError, match="unexpected"):
        asyncio.run(unhandled_exception_handler(request, ValueError("unexpected")))

"""Custom exception hierarchy for standardized error handling."""


class AppException(Exception):
    """Base exception for all application-level errors."""

    def __init__(self, code: str, message: str, status_code: int = 500, details: dict = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    def __init__(self, resource: str, identifier: str = None):
        msg = f"{resource.title()} not found"
        if identifier:
            msg = f"{resource.title()} '{identifier}' not found"
        super().__init__(
            f"{resource.upper()}_NOT_FOUND",
            msg,
            404,
            {resource: identifier} if identifier else {},
        )


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__("UNAUTHORIZED", message, 401)


class ForbiddenException(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__("FORBIDDEN", message, 403)


class ConflictException(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__("CONFLICT", message, 409, details or {})


class ValidationException(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__("VALIDATION_ERROR", message, 400, details or {})


class RateLimitException(AppException):
    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__("RATE_LIMIT_EXCEEDED", message, 429)


class ExternalServiceException(AppException):
    def __init__(self, service: str, message: str = None):
        msg = message or f"External service '{service}' returned an error"
        super().__init__(f"{service.upper()}_ERROR", msg, 502, {"service": service})


class UnsafePromptException(AppException):
    def __init__(self, message: str = None):
        msg = message or "Your message contains prohibited content and was blocked."
        super().__init__("UNSAFE_PROMPT", msg, 400)

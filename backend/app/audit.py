from __future__ import annotations

from typing import Any, Optional
from loguru import logger


def audit_log(
    *,
    action: str,
    user_id: Optional[str] = None,
    result: str = "success",
    ip_address: Optional[str] = None,
    resource: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Emit a structured audit log entry.

    Args:
        action:     Dot-separated action identifier, e.g. ``user.login``,
                    ``api_key.create``, ``admin.suspend_user``.
        user_id:    ID of the acting user (may be None for unauthenticated
                    actions like failed logins).
        result:     ``"success"`` or ``"failure"``.
        ip_address: Client IP address from the request.
        resource:   Affected resource identifier (e.g. API key ID,
                    document ID, target user ID).
        details:    Any additional context (method, reason, etc.).
    """
    logger.bind(
        audit=True,
        action=action,
        actor_id=user_id or "anonymous",
        result=result,
        ip_address=ip_address or "unknown",
        resource=resource or "",
        audit_details=details or {},
    ).info(
        "AUDIT | {action} | user={actor} | result={result}",
        action=action,
        actor=user_id or "anonymous",
        result=result,
    )

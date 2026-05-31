"""
JWT authentication — register, login, and token verification.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User, UserRole

settings = get_settings()
security = HTTPBearer()


# ── Password Hashing ─────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT Token ────────────────────────────────────────

def create_access_token(user_id) -> str:
    """Create a JWT access token with user_id as the subject."""
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_EXPIRY_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id) -> str:
    """Create a JWT refresh token with user_id as the subject."""
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_EXPIRY_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, token_type: str = "access") -> Optional[str]:
    """Decode JWT and return user_id, or None if invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def create_invite_token(inviter_id: str, email: str, workspace_name: str) -> str:
    """Create a time-bound workspace invitation JWT."""
    payload: dict[str, Any] = {
        "sub": inviter_id,
        "email": email,
        "workspace_name": workspace_name,
        "type": "invite",
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.INVITE_TOKEN_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_invite_token(token: str) -> Optional[dict[str, Any]]:
    """Decode a workspace invite JWT and return its payload if valid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "invite":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ── FastAPI Dependencies ─────────────────────────────

import hashlib

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Dependency: extract and validate user from JWT bearer token or API key."""
    token = credentials.credentials

    # Check if token is an API key
    if token.startswith("rag_"):
        hashed = hashlib.sha256(token.encode("utf-8")).hexdigest()
        from app.models import ApiKey
        api_key = db.query(ApiKey).filter(ApiKey.hashed_key == hashed).first()
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        api_key.last_used = datetime.now(timezone.utc)
        db.commit()

        user = api_key.user
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found for this API key",
            )
        return user

    # Otherwise, process as JWT
    user_id = decode_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def _is_admin_user(user: User) -> bool:
    """
    Check if a user has administrative privileges.
    Supports both the modern 'role' field and the legacy 'is_admin' boolean.
    """
    if not user:
        return False
    
    # We check the role first (it can be an Enum or a plain string depending on the environment)
    role_check = (user.role == UserRole.admin) or (str(user.role) == "admin")
    
    # Fallback to the legacy is_admin flag
    return role_check or bool(user.is_admin)


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency that restricts access to administrators only.
    Raises 403 Forbidden if the user lacks sufficient permissions.
    """
    if not _is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Alias for get_admin_user to maintain compatibility with existing routes.
    Ensures the requesting user has administrative rights.
    """
    return get_admin_user(current_user)

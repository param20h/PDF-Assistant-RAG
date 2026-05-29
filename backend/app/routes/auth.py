"""
Auth API routes — register, login, and user profile.
"""
import re
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from langsmith import expect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.config import get_settings
from app.database import get_db
from app.models import User, ApiKey
from app.schemas import (
    GoogleLoginRequest,
    RefreshRequest,
    TokenResponse,
    UpdatePassword,
    UpdatePasswordResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
    UserUpdateResponse,
    ApiKeyResponse,
    ApiKeyCreateResponse,
)
from app.auth import hash_password, verify_password, create_access_token, create_refresh_token, get_current_user, decode_token

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


def _create_token_response(user: User) -> TokenResponse:
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


def _verify_google_token(id_token_value: str) -> dict:
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured",
        )

    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication dependency is not installed",
        ) from exc

    try:
        google_payload = id_token.verify_oauth2_token(
            id_token_value,
            Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credential",
        ) from exc

    email = google_payload.get("email")
    if not email or not google_payload.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account email is not verified",
        )

    return google_payload


def _unique_google_username(email: str, db: Session) -> str:
    local_part = email.split("@", 1)[0]
    base = re.sub(r"[^a-zA-Z0-9_-]+", "-", local_part).strip("-_").lower() or "google-user"
    base = base[:70]
    candidate = base
    suffix = 1

    while db.query(User).filter(User.username == candidate).first():
        suffix += 1
        suffix_text = f"-{suffix}"
        candidate = f"{base[:80 - len(suffix_text)]}{suffix_text}"

    return candidate


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user account and return authentication tokens.

    Creates a new user in the database after validating that the username and
    email are not already taken. The password is hashed before storage. On
    success, access and refresh tokens are generated and returned along with
    the user's public information.

    Args:
        payload (UserRegister): The registration details including username, email, and password.
        db (Session, optional): Database session dependency. Defaults to Depends(get_db).

    Returns:
        TokenResponse: An object containing:
            - access_token (str): jwt access token for authenticating API requests.
            - refresh_token (str): jwt refresh token for obtaining new access tokens.
            - user : UserResponse object with registered user's public information (id, username, email).

    Raises:
        HTTPException: If the username is already taken (409 Conflict).
        HTTPException: If the email is already registered (409 Conflict).
    """
    # Check existing username
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Check existing email
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _create_token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user with email and password.

    Verifies that the provided email exists in the database and that the
    plain text password matches the stored hash. Upon successful authentication,
    generates new access and refresh tokens for the user session.

    Args:
        payload (UserLogin): User login data containing email and password.
        db (Session, optional): Database session dependency. Defaults to Depends(get_db).

    Returns:
        TokenResponse: An object containing:
            - access_token: JWT access token for API authentication.
            - refresh_token: JWT refresh token for obtaining new access tokens.
            - user: UserResponse object with the authenticated user's details.
    
    Raises:
        HTTPException: 401 Unauthorized if the email is not found or the
            password does not match the stored hash.
    """
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    return _create_token_response(user)


@router.post("/google", response_model=TokenResponse)
def login_with_google(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate with a Google Identity Services ID token.

    Existing users are matched by verified email. New Google users get an
    internal username derived from the email prefix and an unusable random
    password hash so password login remains opt-in through the normal flow.
    """
    google_payload = _verify_google_token(payload.id_token)
    email = str(google_payload["email"]).lower()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            username=_unique_google_username(email, db),
            email=email,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    return _create_token_response(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    """
    Refresh both access and refresh tokens using a valid refresh token.

    Decodes the provided refresh token to extract the user ID. If the token
    is valid and the user still exists in the database, a new pair of access
    and refresh tokens is generated and returned.

    Args:
        payload (RefreshRequest): An object containing the refresh token to be used for generating new tokens
        db (Session, optional): Database session dependency. Defaults to Depends(get_db).

    Returns:
        TokenResponse: A fresh set of credentials containing:
            - access_token: New JWT access token.
            - refresh_token: New JWT refresh token.
            - user: UserResponse object with the user's public details.
    
    Raises:
        HTTPException: 401 Unauthorized if:
            - The refresh token is invalid or expired.
            - The user associated with the token no longer exists.
    """
    user_id = decode_token(payload.refresh_token, token_type="refresh")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
        
    return _create_token_response(user)


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    """Retrieve the profile of the currently authenticated user.

    Returns the user object associated with the valid access token provided
    in the request. This endpoint is useful for fetching the current user's
    information after login or token refresh.

    Args:
        user: The currently authenticated user, obtained from the `get_current_user` dependency.

    Returns:
        UserResponse: The authenticated user's public profile data, including
        id, username, email, and any other exposed fields.

    Note:
        This endpoint relies on the `get_current_user` dependency, which
        will automatically return a 401 Unauthorized response if the access
        token is missing, invalid, or expired. Therefore, this function
        itself does not need to raise any HTTP exceptions.
    """
    return UserResponse.model_validate(user)

@router.put("/update")
def update_user_info(payload:UserUpdate,
                    user: User = Depends(get_current_user),
                    db: Session = Depends(get_db))-> UserUpdateResponse:
    """Update the current user's profile information.

    Allows an authenticated user to change their username and/or email address.
    At least one of `username` or `email` must be provided. If a new value
    is supplied, it is checked for uniqueness against existing users. On
    success, the updated user record is returned.

    Args:
        payload: UserUpdate object containing optional `username` and `email` fields to update.
        user: The currently authenticated user, obtained from the `get_current_user` dependency.
        db: SQLAlchemy database session, obtained from the dependency.

    Returns:
        UserUpdateResponse: The updated user profile data (same structure as
        the database model, exposed through the response model).

    Raises:
        HTTPException: 400 if:
            - Neither `username` nor `email` is provided.
            - The new username is already taken.
            - The new email is already registered (checks both fields).
            - A database error occurs (e.g., integrity or connection issue).

    Note:
        The function commits changes to the database and refreshes the user
        instance before returning. Any `SQLAlchemyError` triggers a rollback
        and a 400 response.
    """
    if payload.username is None and payload.email is None:
        raise HTTPException(status_code=400, detail="Username and email are required")

    try:
        if payload.username:
            existing_user = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()

            if existing_user:
                raise HTTPException(status_code=400, detail="Username already exists")
            user.username = payload.username
        if payload.email:
            existing_user = db.execute(select(User).where(User.username == payload.email)).scalar_one_or_none()

            if existing_user:
                raise HTTPException(status_code=400, detail="Username already exists")
            user.email = payload.email
        db.commit()
        db.refresh(user)
        return user
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(status_code=400, detail="Database error")

@router.put("/password")
def update_password(payload:UpdatePassword,
                    user: User = Depends(get_current_user),
                    db: Session = Depends(get_db))-> UpdatePasswordResponse:
    """Update the authenticated user's password.

    Validates that both the new password and confirmation are provided and
    match each other. If valid, the password is hashed and stored. The user
    record is then committed to the database.

    Args:
        payload: UpdatePassword object containing `password` and `confirm_password` fields.
        user: The currently authenticated user, obtained from the `get_current_user` dependency.
        db: SQLAlchemy database session, obtained from the dependency.

    Returns:
        UpdatePasswordResponse: The updated user object (typically containing 
        user details excluding the password hash).

    Raises:
        HTTPException: 400 if:
            - Either `password` or `confirm_password` is missing or empty.
            - The two password fields do not match.
            - A database error (SQLAlchemyError) occurs during commit.

    Note:
        The function hashes the password using `hash_password()` before
        saving. Any `SQLAlchemyError` triggers a rollback and raises a 400
        response.
    """
    if not payload.password and not payload.confirm_password:
        raise HTTPException(status_code=400, detail="Password and confirm_password are required")
    if len(payload.password) == 0 and len(payload.confirm_password) == 0:
        raise HTTPException(status_code=400, detail="Password and confirm_password are required")
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Password and confirm_password are different")
    try:
        hashed_password = hash_password(payload.password)
        user.hashed_password = hashed_password
        db.commit()
        db.refresh(user)
        return user
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Database error")

from typing import List
import hashlib

@router.post("/api-keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new API key for the authenticated user."""
    raw_key = "rag_" + secrets.token_urlsafe(32)
    hashed_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    
    api_key = ApiKey(
        user_id=user.id,
        key_prefix=raw_key[:10],
        hashed_key=hashed_key,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return {"key": raw_key, "api_key": api_key}

@router.get("/api-keys", response_model=List[ApiKeyResponse])
def list_api_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all API keys for the authenticated user."""
    return db.query(ApiKey).filter(ApiKey.user_id == user.id).all()

@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(key_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Revoke an API key."""
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == user.id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    db.delete(api_key)
    db.commit()
    return None

@router.get("/config")
def get_auth_config():
    """Return public configuration for auth providers"""
    return {
        "google_client_id": settings.GOOGLE_CLIENT_ID
    }

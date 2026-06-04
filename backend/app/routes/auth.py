"""
Auth API routes — register, login, and user profile.
"""
import re
import secrets
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Cookie, Response, Body
from fastapi.responses import RedirectResponse
import httpx
from langsmith import expect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.config import get_settings
from app.database import get_db
from app.models import User, ApiKey, UserRole
from app.schemas import (
    GoogleLoginRequest,
    HFTokenUpdate,
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
        role=UserRole.user,
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

@router.put("/hf-token", response_model=UserResponse)
def update_hf_token(
    payload: HFTokenUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the HuggingFace token for the authenticated user.

    Stores the provided HF token in the user's profile so it can be used
    for HuggingFace API calls (e.g. InferenceClient) in place of the
    globally configured ``HF_TOKEN`` environment variable.

    Args:
        payload: HFTokenUpdate object containing the new ``hf_token`` value.
        user: The currently authenticated user, obtained from the
            ``get_current_user`` dependency.
        db: SQLAlchemy database session, obtained from the dependency.

    Returns:
        UserResponse: The updated user profile including the new ``hf_token``
        field.
    """
    user.hf_token = payload.hf_token
    db.commit()
    db.refresh(user)
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
            existing_user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()

            if existing_user:
                raise HTTPException(status_code=400, detail="Email already exists")
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
def create_api_key(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    body: dict = Body(None),
):
    """Create a new API key for the authenticated user."""
    name = (body or {}).get("name", "default")
    raw_key = "pdf_rag_" + secrets.token_hex(24)
    hashed_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    api_key = ApiKey(
        user_id=user.id,
        name=name,
        key_prefix=raw_key[:15],
        hashed_key=hashed_key,
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return ApiKeyCreateResponse(
        id=str(api_key.id),
        name=api_key.name,
        key_preview=api_key.key_prefix,
        created_at=api_key.created_at,
        raw_key=raw_key,
    )

@router.get("/api-keys", response_model=List[ApiKeyResponse])
def list_api_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all API keys for the authenticated user."""
    keys = db.query(ApiKey).filter(ApiKey.user_id == user.id, ApiKey.is_active == True).all()
    return [
        ApiKeyResponse(
            id=str(k.id),
            name=k.name,
            key_preview=k.key_prefix,
            created_at=k.created_at,
        )
        for k in keys
    ]

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


def _unique_google_username(email: str, db: Session) -> str:
    """
    Generate a unique username based on the email.
    """
    base = email.split("@")[0]
    base = re.sub(r"[^a-zA-Z0-9_-]", "", base)
    base = base[:70]
    candidate = base
    suffix = 1

    while db.query(User).filter(User.username == candidate).first():
        suffix += 1
        suffix_text = f"-{suffix}"
        candidate = f"{base[:80 - len(suffix_text)]}{suffix_text}"

    return candidate


@router.get("/login/huggingface")
def huggingface_login(response: Response):
    """
    Generates a secure state, stores it in an HttpOnly cookie,
    and returns the Hugging Face OAuth authorization URL.
    """
    if not settings.HF_CLIENT_ID or not settings.HF_REDIRECT_URI:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hugging Face OAuth is not configured",
        )

    # Generate CSRF state
    state = secrets.token_urlsafe(32)

    # Store state in cookie (valid for 10 minutes)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=600,  # 10 minutes
    )

    # Build Hugging Face authorize URL
    scope = "openid profile email"
    auth_url = (
        f"https://huggingface.co/oauth/authorize?"
        f"client_id={settings.HF_CLIENT_ID}&"
        f"redirect_uri={settings.HF_REDIRECT_URI}&"
        f"scope={scope}&"
        f"state={state}&"
        f"response_type=code"
    )

    return {"url": auth_url}


@router.get("/callback/huggingface")
async def huggingface_callback(
    code: str,
    state: str,
    response: Response,
    oauth_state: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
):
    """
    Verifies state, exchanges code for access token,
    gets user info, upserts user, sets HttpOnly JWT cookies,
    and redirects to the frontend dashboard.
    """
    # 1. Verify CSRF State
    if not oauth_state or state != oauth_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State verification failed. Possible CSRF attack.",
        )

    # 2. Exchange code for access_token via Hugging Face API
    token_url = "https://huggingface.co/oauth/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.HF_REDIRECT_URI,
        "client_id": settings.HF_CLIENT_ID,
        "client_secret": settings.HF_CLIENT_SECRET,
    }

    async with httpx.AsyncClient() as client:
        try:
            token_response = await client.post(token_url, headers=headers, data=data)
            token_response.raise_for_status()
            token_data = token_response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to exchange code: {e.response.text}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Token exchange error: {str(e)}",
            )

    hf_access_token = token_data.get("access_token")
    if not hf_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No access token returned from Hugging Face",
        )

    # 3. Fetch user profile data via /oauth/userinfo
    userinfo_url = "https://huggingface.co/oauth/userinfo"
    userinfo_headers = {"Authorization": f"Bearer {hf_access_token}"}

    async with httpx.AsyncClient() as client:
        try:
            userinfo_response = await client.get(userinfo_url, headers=userinfo_headers)
            userinfo_response.raise_for_status()
            user_data = userinfo_response.json()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve Hugging Face user info: {str(e)}",
            )

    email = user_data.get("email")
    username = user_data.get("preferred_username") or user_data.get("username") or user_data.get("name")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hugging Face account email is required but not provided",
        )

    email = email.lower()
    if not username:
        username = email.split("@")[0]

    # 4. Upsert user in the DB
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Check if username is already taken
        username = _unique_google_username(email, db)
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    user.hf_token = hf_access_token
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    # 5. Generate secure session JWT tokens for our app
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # 6. Set tokens as HttpOnly cookies and Redirect
    redirect_dest = f"{settings.FRONTEND_URL}/dashboard" if settings.ENVIRONMENT == "development" else "/dashboard"
    response = RedirectResponse(
        url=redirect_dest,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.JWT_ACCESS_EXPIRY_MINUTES * 60,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.JWT_REFRESH_EXPIRY_DAYS * 24 * 60 * 60,
    )

    # Delete the oauth_state cookie
    response.delete_cookie(key="oauth_state")

    return response


@router.post("/logout")
def logout(response: Response):
    """
    Logs out the user by clearing the secure session cookies.
    """
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    return {"message": "Successfully logged out"}

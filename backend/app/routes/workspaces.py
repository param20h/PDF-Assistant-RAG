"""Workspace invitation routes for admin-managed workspace access."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_invite_token, get_admin_user
from app.config import get_settings
from app.database import get_db
from app.email_service import send_email
from app.models import User, WorkspaceInvitation
from app.schemas import WorkspaceInviteRequest, WorkspaceInviteResponse

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post("/invite", response_model=WorkspaceInviteResponse, status_code=status.HTTP_200_OK)
def invite_workspace(
    payload: WorkspaceInviteRequest,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Invite a user by email to join a workspace via a secure time-bound token."""
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    token = create_invite_token(admin_user.id, payload.email, payload.workspace_name)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.INVITE_TOKEN_EXPIRY_HOURS)

    invitation = WorkspaceInvitation(
        email=payload.email,
        inviter_id=admin_user.id,
        token_hash=token_hash,
        workspace_name=payload.workspace_name,
        expires_at=expires_at,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    join_link = f"{settings.APP_URL.rstrip('/')}/invite?token={quote(token, safe='')}"
    subject = f"Invitation to join workspace '{payload.workspace_name}'"
    body_lines = [
        f"Hello,",
        "",
        f"You have been invited to join the workspace '{payload.workspace_name}'.",
        "Click the link below to accept the invitation:",
        join_link,
    ]
    if payload.message:
        body_lines.insert(3, payload.message)
        body_lines.insert(4, "")
    body = "\n".join(body_lines)

    send_email(payload.email, subject, body)

    return WorkspaceInviteResponse(
        email=payload.email,
        workspace_name=payload.workspace_name,
        invite_link=join_link,
        expires_in_hours=settings.INVITE_TOKEN_EXPIRY_HOURS,
    )

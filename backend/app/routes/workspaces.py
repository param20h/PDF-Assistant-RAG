"""Workspace invitation routes for admin-managed workspace access."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_invite_token, get_current_user, decode_invite_token
from app.config import get_settings
from app.database import get_db
from app.email_service import send_email
from app.models import User, Workspace, WorkspaceMembership, WorkspaceInvitation
from app.schemas import (
    WorkspaceInviteRequest,
    WorkspaceInviteResponse,
    WorkspaceInviteVerifyResponse,
    WorkspaceInviteAcceptResponse,
)

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post("/invite", response_model=WorkspaceInviteResponse, status_code=status.HTTP_200_OK)
def invite_workspace(
    payload: WorkspaceInviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Invite a user by email to join a workspace via a secure time-bound token."""
    # 1. Lookup or create the Workspace
    workspace = db.query(Workspace).filter(Workspace.name == payload.workspace_name).first()
    if not workspace:
        workspace = Workspace(name=payload.workspace_name)
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
        
        # Add the inviter as the admin of this workspace
        membership = WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=current_user.id,
            role="admin",
        )
        db.add(membership)
        db.commit()
    else:
        # Verify if current_user is a member of this workspace
        user_membership = db.query(WorkspaceMembership).filter(
            WorkspaceMembership.workspace_id == workspace.id,
            WorkspaceMembership.user_id == current_user.id,
        ).first()
        if not user_membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to invite users to this workspace.",
            )

    # 2. Check if the invited user is already a member of this workspace
    invited_user = db.query(User).filter(User.email == payload.email).first()
    if invited_user:
        existing_membership = db.query(WorkspaceMembership).filter(
            WorkspaceMembership.workspace_id == workspace.id,
            WorkspaceMembership.user_id == invited_user.id,
        ).first()
        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The user is already a member of this workspace.",
            )

    # 3. Create invitation
    token = create_invite_token(current_user.id, payload.email, payload.workspace_name)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.INVITE_TOKEN_EXPIRY_HOURS)

    invitation = WorkspaceInvitation(
        email=payload.email,
        inviter_id=current_user.id,
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


@router.get("/invite/verify", response_model=WorkspaceInviteVerifyResponse, status_code=status.HTTP_200_OK)
def verify_workspace_invite(
    token: str,
    db: Session = Depends(get_db),
):
    """Verify an invitation token and return workspace details."""
    payload = decode_invite_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation token.",
        )

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    invitation = db.query(WorkspaceInvitation).filter(
        WorkspaceInvitation.token_hash == token_hash
    ).first()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found.",
        )

    inviter = db.query(User).filter(User.id == invitation.inviter_id).first()
    inviter_email = inviter.email if inviter else "unknown"
    inviter_username = inviter.username if inviter else "unknown"

    is_expired = invitation.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)

    return WorkspaceInviteVerifyResponse(
        workspace_name=invitation.workspace_name,
        inviter_email=inviter_email,
        inviter_username=inviter_username,
        email=invitation.email,
        expires_at=invitation.expires_at,
        is_expired=is_expired,
        is_accepted=invitation.accepted_at is not None,
    )


@router.post("/invite/accept", response_model=WorkspaceInviteAcceptResponse, status_code=status.HTTP_200_OK)
def accept_workspace_invite(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Accept a workspace invitation using the time-bound token."""
    payload = decode_invite_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation token.",
        )

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    invitation = db.query(WorkspaceInvitation).filter(
        WorkspaceInvitation.token_hash == token_hash
    ).first()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found.",
        )

    if invitation.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has already been accepted.",
        )

    if invitation.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has expired.",
        )

    # Lookup or create the workspace
    workspace = db.query(Workspace).filter(
        Workspace.name == invitation.workspace_name
    ).first()
    if not workspace:
        workspace = Workspace(name=invitation.workspace_name)
        db.add(workspace)
        db.commit()
        db.refresh(workspace)

    # Check if the user is already a member
    membership = db.query(WorkspaceMembership).filter(
        WorkspaceMembership.workspace_id == workspace.id,
        WorkspaceMembership.user_id == current_user.id,
    ).first()

    if not membership:
        membership = WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=current_user.id,
            role="member",
        )
        db.add(membership)

    invitation.accepted_at = datetime.now(timezone.utc)
    db.commit()

    return WorkspaceInviteAcceptResponse(
        message="Invitation accepted successfully.",
        workspace_name=workspace.name,
    )

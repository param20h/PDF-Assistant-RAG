"""Workspace invitation and management routes."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List

from app.auth import create_invite_token, get_admin_user, get_current_user
from app.config import get_settings
from app.database import get_db
from app.email_service import send_workspace_invite_email
from app.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.models import User, Workspace, WorkspaceInvitation, WorkspaceMember, WorkspaceRole
from app.schemas import (
    WorkspaceCreate,
    WorkspaceDetailResponse,
    WorkspaceInviteRequest,
    WorkspaceInviteResponse,
    WorkspaceMemberAdd,
    WorkspaceMemberResponse,
    WorkspaceMemberRoleUpdate,
    WorkspaceResponse,
)

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])
settings = get_settings()
logger = logging.getLogger(__name__)


# ── Private helpers ───────────────────────────────────────────────────────────

def _get_workspace_or_404(workspace_id: str, db: Session) -> Workspace:
    ws = db.get(Workspace, workspace_id)
    if not ws:
        raise NotFoundException("Workspace")
    return ws


def _get_membership_or_403(workspace: Workspace, user: User, db: Session) -> WorkspaceMember:
    """Return the caller's WorkspaceMember row, or raise 403."""
    membership = db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
        )
    ).scalar_one_or_none()
    if not membership:
        raise ForbiddenException("You are not a member of this workspace")
    return membership


def _require_workspace_admin(membership: WorkspaceMember) -> None:
    if membership.role != WorkspaceRole.admin:
        raise ForbiddenException("Only workspace admins can perform this action")


def _count_admins(workspace_id: str, db: Session) -> int:
    return len(
        db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == WorkspaceRole.admin,
            )
        ).scalars().all()
    )


# ── Invitation (existing) ─────────────────────────────────────────────────────

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
    send_workspace_invite_email(
        to=payload.email,
        workspace_name=payload.workspace_name,
        invite_link=join_link,
        expires_in_hours=settings.INVITE_TOKEN_EXPIRY_HOURS,
        personal_message=payload.message or None,
    )

    return WorkspaceInviteResponse(
        email=payload.email,
        workspace_name=payload.workspace_name,
        invite_link=join_link,
        expires_in_hours=settings.INVITE_TOKEN_EXPIRY_HOURS,
    )


# ── Workspace CRUD ────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=WorkspaceDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workspace",
)
def create_workspace(
    payload: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new workspace.

    The authenticated user is automatically added as the first member with
    the ``admin`` role.
    """
    workspace = Workspace(
        name=payload.name,
        created_by=current_user.id,
    )
    db.add(workspace)
    db.flush()  # populate workspace.id before creating the membership row

    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role=WorkspaceRole.admin,
    )
    db.add(membership)
    db.commit()
    db.refresh(workspace)

    logger.info(
        "Workspace '%s' (%s) created by user %s",
        workspace.name,
        workspace.id,
        current_user.id,
    )
    return workspace


@router.get(
    "",
    response_model=List[WorkspaceResponse],
    summary="List my workspaces",
)
def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return every workspace the authenticated user is a member of."""
    memberships = db.execute(
        select(WorkspaceMember).where(WorkspaceMember.user_id == current_user.id)
    ).scalars().all()

    workspace_ids = [m.workspace_id for m in memberships]
    if not workspace_ids:
        return []

    return db.execute(
        select(Workspace).where(Workspace.id.in_(workspace_ids))
    ).scalars().all()


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceDetailResponse,
    summary="Get workspace detail",
)
def get_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return workspace details including the full member list.

    Only workspace members may access this endpoint.
    """
    workspace = _get_workspace_or_404(workspace_id, db)
    _get_membership_or_403(workspace, current_user, db)
    return workspace


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workspace",
)
def delete_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently delete a workspace and all its members.

    Requires the caller to hold the workspace ``admin`` role.
    """
    workspace = _get_workspace_or_404(workspace_id, db)
    membership = _get_membership_or_403(workspace, current_user, db)
    _require_workspace_admin(membership)

    db.delete(workspace)
    db.commit()

    logger.info(
        "Workspace '%s' (%s) deleted by user %s",
        workspace.name,
        workspace_id,
        current_user.id,
    )
    return None


# ── Member management ─────────────────────────────────────────────────────────

@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member to a workspace",
)
def add_member(
    workspace_id: str,
    payload: WorkspaceMemberAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add an existing user to a workspace.

    * Requires the caller to be a workspace ``admin``.
    * The target user must already exist in the system (looked up by ``user_id``).
    * Adding an existing member raises ``409 Conflict``.
    * Defaults to the ``viewer`` role when no role is supplied.
    """
    workspace = _get_workspace_or_404(workspace_id, db)
    caller_membership = _get_membership_or_403(workspace, current_user, db)
    _require_workspace_admin(caller_membership)

    target_user = db.get(User, payload.user_id)
    if not target_user:
        raise NotFoundException("User")

    existing = db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == payload.user_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictException("User is already a member of this workspace")

    new_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=payload.user_id,
        role=payload.role,
    )
    db.add(new_membership)
    db.commit()
    db.refresh(new_membership)

    logger.info(
        "User %s added to workspace %s as '%s' by %s",
        payload.user_id,
        workspace_id,
        payload.role,
        current_user.id,
    )
    return new_membership


@router.get(
    "/{workspace_id}/members",
    response_model=List[WorkspaceMemberResponse],
    summary="List workspace members",
)
def list_members(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return all members of a workspace.

    Only workspace members may call this endpoint.
    """
    workspace = _get_workspace_or_404(workspace_id, db)
    _get_membership_or_403(workspace, current_user, db)

    return db.execute(
        select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
    ).scalars().all()


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=WorkspaceMemberResponse,
    summary="Change a member's role",
)
def update_member_role(
    workspace_id: str,
    user_id: str,
    payload: WorkspaceMemberRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change a member's role within the workspace.

    * Requires the caller to be a workspace ``admin``.
    * Demoting the last ``admin`` is rejected to prevent lockout.
    """
    workspace = _get_workspace_or_404(workspace_id, db)
    caller_membership = _get_membership_or_403(workspace, current_user, db)
    _require_workspace_admin(caller_membership)

    target_membership = db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    ).scalar_one_or_none()
    if not target_membership:
        raise NotFoundException("Workspace member")

    if (
        target_membership.role == WorkspaceRole.admin
        and payload.role != WorkspaceRole.admin
        and _count_admins(workspace_id, db) <= 1
    ):
        raise ValidationException(
            "Cannot demote the last admin. Promote another member to admin first."
        )

    target_membership.role = payload.role
    db.commit()
    db.refresh(target_membership)

    logger.info(
        "User %s role in workspace %s changed to '%s' by %s",
        user_id,
        workspace_id,
        payload.role,
        current_user.id,
    )
    return target_membership


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from a workspace",
)
def remove_member(
    workspace_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a member from a workspace.

    * A workspace ``admin`` may remove any member.
    * Any member may remove themselves (leave the workspace).
    * Removing the last ``admin`` is rejected to prevent lockout.
    """
    workspace = _get_workspace_or_404(workspace_id, db)
    caller_membership = _get_membership_or_403(workspace, current_user, db)

    is_self = str(current_user.id) == str(user_id)
    if not is_self:
        _require_workspace_admin(caller_membership)

    target_membership = db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    ).scalar_one_or_none()
    if not target_membership:
        raise NotFoundException("Workspace member")

    if (
        target_membership.role == WorkspaceRole.admin
        and _count_admins(workspace_id, db) <= 1
    ):
        raise ValidationException(
            "Cannot remove the last admin. Promote another member to admin first."
        )

    db.delete(target_membership)
    db.commit()

    logger.info(
        "User %s removed from workspace %s by %s",
        user_id,
        workspace_id,
        current_user.id,
    )
    return None

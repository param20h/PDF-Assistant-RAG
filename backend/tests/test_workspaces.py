import hashlib
from datetime import datetime, timedelta, timezone

from app.auth import create_access_token, hash_password, create_invite_token
from app.models import User, Workspace, WorkspaceMembership, WorkspaceInvitation


def test_workspace_invite_creates_workspace_and_membership_for_user(client, db_session, user, monkeypatch):
    sent = {}

    def fake_send_email(to, subject, body, html=None):
        sent["to"] = to
        sent["subject"] = subject
        sent["body"] = body

    monkeypatch.setattr("app.routes.workspaces.send_email", fake_send_email)

    token = create_access_token(user.id)
    response = client.post(
        "/api/v1/workspaces/invite",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "invitee@example.com", "workspace_name": "Engineering"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "invitee@example.com"
    assert payload["workspace_name"] == "Engineering"
    assert "invite_link" in payload

    # Verify workspace and membership were created
    workspace = db_session.query(Workspace).filter_by(name="Engineering").first()
    assert workspace is not None

    membership = db_session.query(WorkspaceMembership).filter_by(
        workspace_id=workspace.id, user_id=user.id
    ).first()
    assert membership is not None
    assert membership.role == "admin"


def test_workspace_invite_existing_member_fails(client, db_session, user, monkeypatch):
    # Setup workspace and membership
    workspace = Workspace(name="Marketing")
    db_session.add(workspace)
    db_session.commit()

    member = User(
        username="member",
        email="member@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add(member)
    db_session.commit()

    membership1 = WorkspaceMembership(workspace_id=workspace.id, user_id=user.id, role="admin")
    membership2 = WorkspaceMembership(workspace_id=workspace.id, user_id=member.id, role="member")
    db_session.add(membership1)
    db_session.add(membership2)
    db_session.commit()

    token = create_access_token(user.id)
    response = client.post(
        "/api/v1/workspaces/invite",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "member@example.com", "workspace_name": "Marketing"},
    )

    assert response.status_code == 400
    assert "already a member" in response.json()["detail"]


def test_workspace_invite_verify(client, db_session, user):
    invite_token = create_invite_token(user.id, "invitee@example.com", "Sales")
    token_hash = hashlib.sha256(invite_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    invitation = WorkspaceInvitation(
        email="invitee@example.com",
        inviter_id=user.id,
        token_hash=token_hash,
        workspace_name="Sales",
        expires_at=expires_at,
    )
    db_session.add(invitation)
    db_session.commit()

    response = client.get(
        f"/api/v1/workspaces/invite/verify?token={invite_token}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_name"] == "Sales"
    assert payload["email"] == "invitee@example.com"
    assert payload["inviter_email"] == user.email
    assert payload["is_expired"] is False
    assert payload["is_accepted"] is False


def test_workspace_invite_accept(client, db_session, user):
    invitee = User(
        username="invitee",
        email="invitee@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add(invitee)
    db_session.commit()

    invite_token = create_invite_token(user.id, "invitee@example.com", "Support")
    token_hash = hashlib.sha256(invite_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    invitation = WorkspaceInvitation(
        email="invitee@example.com",
        inviter_id=user.id,
        token_hash=token_hash,
        workspace_name="Support",
        expires_at=expires_at,
    )
    db_session.add(invitation)
    db_session.commit()

    # Pre-create workspace to map
    workspace = Workspace(name="Support")
    db_session.add(workspace)
    db_session.commit()

    token = create_access_token(invitee.id)
    response = client.post(
        f"/api/v1/workspaces/invite/accept?token={invite_token}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["workspace_name"] == "Support"

    # Verify membership and invitation status
    membership = db_session.query(WorkspaceMembership).filter_by(
        workspace_id=workspace.id, user_id=invitee.id
    ).first()
    assert membership is not None
    assert membership.role == "member"

    db_session.refresh(invitation)
    assert invitation.accepted_at is not None

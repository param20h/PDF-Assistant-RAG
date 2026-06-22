from app.auth import create_access_token, hash_password
from app.models import User, WorkspaceInvitation


def test_workspace_invite_requires_admin(client, db_session, user):
    token = create_access_token(user.id)
    response = client.post(
        "/api/v1/workspaces/invite",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "invitee@example.com", "workspace_name": "Engineering"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Admin access required"


def test_workspace_invite_creates_invitation_and_sends_email(client, db_session, monkeypatch):
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=hash_password("password123"),
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    sent = {}

    def fake_send_workspace_invite_email(to, workspace_name, invite_link, expires_in_hours, personal_message=None):
        sent["to"] = to
        sent["workspace_name"] = workspace_name
        sent["invite_link"] = invite_link

    monkeypatch.setattr("app.routes.workspaces.send_workspace_invite_email", fake_send_workspace_invite_email)

    token = create_access_token(admin.id)
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
    assert payload["invite_link"].startswith("http")
    assert "token=" in payload["invite_link"]
    assert sent["to"] == "invitee@example.com"
    assert sent["workspace_name"] == payload["workspace_name"]
    assert token in sent["invite_link"]

    invitation = db_session.query(WorkspaceInvitation).filter_by(email="invitee@example.com").first()
    assert invitation is not None
    assert invitation.workspace_name == "Engineering"

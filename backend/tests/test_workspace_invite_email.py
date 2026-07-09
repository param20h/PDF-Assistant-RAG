"""
Tests for send_workspace_invite_email — issue #442.
"""
from unittest.mock import call, patch

import pytest

from app.email_service import send_workspace_invite_email


WORKSPACE = "Research Team"
INVITE_LINK = "http://localhost:3000/invite?token=abc123"
EXPIRES = 72
RECIPIENT = "newuser@example.com"


class TestSendWorkspaceInviteEmail:
    def test_delegates_to_send_email(self):
        """send_workspace_invite_email must call send_email exactly once."""
        with patch("app.email_service.send_email") as mock_send:
            send_workspace_invite_email(
                to=RECIPIENT,
                workspace_name=WORKSPACE,
                invite_link=INVITE_LINK,
                expires_in_hours=EXPIRES,
            )
        mock_send.assert_called_once()

    def test_subject_contains_workspace_name(self):
        with patch("app.email_service.send_email") as mock_send:
            send_workspace_invite_email(
                to=RECIPIENT,
                workspace_name=WORKSPACE,
                invite_link=INVITE_LINK,
                expires_in_hours=EXPIRES,
            )
        _to, subject, _body = mock_send.call_args.args
        assert WORKSPACE in subject

    def test_html_body_contains_invite_link(self):
        with patch("app.email_service.send_email") as mock_send:
            send_workspace_invite_email(
                to=RECIPIENT,
                workspace_name=WORKSPACE,
                invite_link=INVITE_LINK,
                expires_in_hours=EXPIRES,
            )
        html = mock_send.call_args.kwargs.get("html") or ""
        assert INVITE_LINK in html

    def test_html_body_contains_workspace_name(self):
        with patch("app.email_service.send_email") as mock_send:
            send_workspace_invite_email(
                to=RECIPIENT,
                workspace_name=WORKSPACE,
                invite_link=INVITE_LINK,
                expires_in_hours=EXPIRES,
            )
        html = mock_send.call_args.kwargs.get("html") or ""
        assert WORKSPACE in html

    def test_html_body_contains_expiry(self):
        with patch("app.email_service.send_email") as mock_send:
            send_workspace_invite_email(
                to=RECIPIENT,
                workspace_name=WORKSPACE,
                invite_link=INVITE_LINK,
                expires_in_hours=EXPIRES,
            )
        html = mock_send.call_args.kwargs.get("html") or ""
        assert str(EXPIRES) in html

    def test_personal_message_included_in_html(self):
        message = "Looking forward to working with you!"
        with patch("app.email_service.send_email") as mock_send:
            send_workspace_invite_email(
                to=RECIPIENT,
                workspace_name=WORKSPACE,
                invite_link=INVITE_LINK,
                expires_in_hours=EXPIRES,
                personal_message=message,
            )
        html = mock_send.call_args.kwargs.get("html") or ""
        assert message in html

    def test_no_personal_message_omits_block(self):
        """Without a personal_message the optional block must not appear."""
        with patch("app.email_service.send_email") as mock_send:
            send_workspace_invite_email(
                to=RECIPIENT,
                workspace_name=WORKSPACE,
                invite_link=INVITE_LINK,
                expires_in_hours=EXPIRES,
                personal_message=None,
            )
        html = mock_send.call_args.kwargs.get("html") or ""
        # The placeholder block rendered for None should be empty / absent
        assert "border-left:4px solid #4f46e5" not in html

    def test_plain_text_body_contains_invite_link(self):
        with patch("app.email_service.send_email") as mock_send:
            send_workspace_invite_email(
                to=RECIPIENT,
                workspace_name=WORKSPACE,
                invite_link=INVITE_LINK,
                expires_in_hours=EXPIRES,
            )
        _to, _subject, plain_body = mock_send.call_args.args
        assert INVITE_LINK in plain_body

    def test_recipient_passed_to_send_email(self):
        with patch("app.email_service.send_email") as mock_send:
            send_workspace_invite_email(
                to=RECIPIENT,
                workspace_name=WORKSPACE,
                invite_link=INVITE_LINK,
                expires_in_hours=EXPIRES,
            )
        to_arg = mock_send.call_args.args[0]
        assert to_arg == RECIPIENT

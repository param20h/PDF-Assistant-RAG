"""Email utilities for backend notification and invitation delivery."""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def send_email(to: str, subject: str, body: str, html: str | None = None) -> None:
    """Send an email using SMTP if configured, otherwise log a mock dispatch."""
    if settings.SMTP_HOST and settings.SMTP_PORT:
        try:
            message = EmailMessage()
            message["Subject"] = subject
            message["From"] = settings.EMAIL_FROM
            message["To"] = to
            message.set_content(body)
            if html:
                message.add_alternative(html, subtype="html")

            context = ssl.create_default_context()
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    smtp.starttls(context=context)
                    smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                smtp.send_message(message)

            logger.info("Email sent to %s via SMTP host %s", to, settings.SMTP_HOST)
            return
        except Exception as exc:
            logger.warning("SMTP email delivery failed, falling back to mock send: %s", exc)

    logger.info(
        "Mock email dispatch: to=%s subject=%s body=%s",
        to,
        subject,
        body,
    )


def send_workspace_invite_email(
    to: str,
    workspace_name: str,
    invite_link: str,
    expires_in_hours: int,
    personal_message: str | None = None,
) -> None:
    """Send a workspace invitation email with an HTML body.

    Builds a branded HTML email containing the workspace name, an optional
    personal message from the inviter, a prominent call-to-action button with
    the acceptance link, and an expiry notice. Falls back to plain-text if HTML
    is not supported by the client. Delegates delivery to :func:`send_email`.

    Args:
        to: Recipient email address.
        workspace_name: Name of the workspace the recipient is invited to.
        invite_link: Fully-qualified URL the recipient must visit to accept.
        expires_in_hours: How many hours until the invite token expires.
        personal_message: Optional personal note from the inviting admin.
    """
    subject = f"You're invited to join workspace '{workspace_name}'"

    # ── Plain-text fallback ───────────────────────────────────────────────
    plain_lines = [
        f"Hello,",
        "",
        f"You have been invited to join the workspace '{workspace_name}'.",
    ]
    if personal_message:
        plain_lines += ["", personal_message]
    plain_lines += [
        "",
        "Accept your invitation by visiting the link below:",
        invite_link,
        "",
        f"This invitation expires in {expires_in_hours} hours.",
        "",
        "If you did not expect this email, you can safely ignore it.",
    ]
    plain_body = "\n".join(plain_lines)

    # ── HTML body ─────────────────────────────────────────────────────────
    personal_block = ""
    if personal_message:
        personal_block = f"""
        <tr>
          <td style="padding:0 32px 20px;">
            <p style="margin:0;padding:16px;background:#f0f4ff;border-left:4px solid #4f46e5;
                       border-radius:4px;font-size:14px;color:#374151;line-height:1.6;">
              {personal_message}
            </p>
          </td>
        </tr>"""

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:12px;
                      box-shadow:0 4px 24px rgba(0,0,0,0.08);overflow:hidden;max-width:600px;">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);
                        padding:36px 32px;text-align:center;">
              <h1 style="margin:0;font-size:24px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;">
                📄 PDF Assistant
              </h1>
              <p style="margin:8px 0 0;font-size:13px;color:#c7d2fe;">
                Workspace Invitation
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 32px 20px;">
              <h2 style="margin:0 0 12px;font-size:20px;font-weight:600;color:#111827;">
                You've been invited!
              </h2>
              <p style="margin:0;font-size:15px;color:#6b7280;line-height:1.6;">
                You have been invited to join the workspace
                <strong style="color:#111827;">'{workspace_name}'</strong>
                on PDF Assistant. Accept below to start collaborating.
              </p>
            </td>
          </tr>

          {personal_block}

          <!-- CTA Button -->
          <tr>
            <td style="padding:8px 32px 32px;text-align:center;">
              <a href="{invite_link}"
                 style="display:inline-block;padding:14px 36px;
                        background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);
                        color:#ffffff;font-size:15px;font-weight:600;
                        text-decoration:none;border-radius:8px;
                        box-shadow:0 4px 12px rgba(79,70,229,0.4);">
                Accept Invitation →
              </a>
              <p style="margin:16px 0 0;font-size:12px;color:#9ca3af;">
                Or copy this link into your browser:<br/>
                <span style="color:#4f46e5;word-break:break-all;">{invite_link}</span>
              </p>
            </td>
          </tr>

          <!-- Expiry notice -->
          <tr>
            <td style="padding:0 32px 24px;">
              <p style="margin:0;padding:12px 16px;background:#fef3c7;border-radius:6px;
                         font-size:13px;color:#92400e;text-align:center;">
                ⏳ This invitation expires in <strong>{expires_in_hours} hours</strong>.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f9fafb;padding:20px 32px;border-top:1px solid #e5e7eb;
                        text-align:center;">
              <p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.6;">
                If you did not expect this invitation, you can safely ignore this email.<br/>
                This email was sent by PDF Assistant · No reply
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    send_email(to, subject, plain_body, html=html_body)
    logger.info(
        "Workspace invite email dispatched to %s for workspace '%s'",
        to,
        workspace_name,
    )

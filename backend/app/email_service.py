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

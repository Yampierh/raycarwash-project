# app/services/email_service.py  —  Sprint 5
#
# Transactional email via SMTP (smtplib wrapped in asyncio.to_thread).
# No new dependency required — smtplib ships with CPython.
#
# Dev mode (SMTP_ENABLED=False): emails are logged to stdout only.
# Production: set SMTP_ENABLED=True + configure SMTP_* settings.
#
# Future upgrade path: replace _send_via_smtp() with SendGrid/SES HTTP API
# for higher deliverability and delivery webhooks without changing callers.

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    """
    Minimal transactional email service.

    Usage:
        await EmailService.send_password_reset(email="user@example.com", reset_url="https://...")
    """

    @staticmethod
    async def send_password_reset(email: str, reset_url: str, full_name: str = "") -> None:
        """
        Send a password-reset email with a single-click link.

        The link is valid for 1 hour (enforced by the JWT expiry in AuthService).
        """
        subject = "Reset your RayCarwash password"
        greeting = f"Hi {full_name}," if full_name else "Hi,"
        body_html = f"""
        <html><body style="font-family: sans-serif; max-width: 480px; margin: 40px auto;">
          <h2 style="color: #1a1a2e;">Password Reset</h2>
          <p>{greeting}</p>
          <p>We received a request to reset your password. Click the button below.
             This link expires in <strong>1 hour</strong>.</p>
          <p style="margin: 32px 0;">
            <a href="{reset_url}"
               style="background:#4f46e5;color:#fff;padding:12px 24px;
                      border-radius:6px;text-decoration:none;font-weight:600;">
              Reset Password
            </a>
          </p>
          <p style="color:#888;font-size:13px;">
            If you didn't request this, you can safely ignore this email.
          </p>
          <hr style="border:none;border-top:1px solid #eee;margin:32px 0;">
          <p style="color:#aaa;font-size:12px;">RayCarwash — Fort Wayne, IN</p>
        </body></html>
        """
        body_text = (
            f"{greeting}\n\n"
            "We received a request to reset your RayCarwash password.\n\n"
            f"Reset link (valid 1 hour): {reset_url}\n\n"
            "If you didn't request this, ignore this email.\n\n"
            "— RayCarwash"
        )

        await EmailService._send(
            to_email=email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
        )

    # ---------------------------------------------------------------- #
    #  Internal                                                         #
    # ---------------------------------------------------------------- #

    @staticmethod
    async def _send(
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str,
    ) -> None:
        if not settings.SMTP_ENABLED:
            logger.warning(
                "EMAIL NOT SENT (SMTP_ENABLED=False) | to=%s subject=%r\n"
                "  Set SMTP_ENABLED=True + SMTP_* vars to send real emails.\n"
                "  Body preview: %s",
                to_email, subject, body_text[:200],
            )
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"]      = to_email

        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        # Run blocking smtplib in a thread pool to avoid blocking the event loop.
        await asyncio.to_thread(EmailService._smtp_send, msg, to_email)

    @staticmethod
    def _smtp_send(msg: MIMEMultipart, to_email: str) -> None:
        """Blocking SMTP send — called via asyncio.to_thread."""
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())
            logger.info("Email sent | to=%s subject=%r", to_email, msg["Subject"])
        except smtplib.SMTPException as exc:
            # Log but don't crash the request — email failure is non-fatal
            # for the password reset flow (user sees success; engineer is alerted).
            logger.error("SMTP send failed | to=%s error=%s", to_email, exc)

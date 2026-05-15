"""
domains/users/contact_change_schemas.py — Request bodies + responses for
/users/me/email/* and /users/me/phone/*.

The flow has two halves:
  1. *change-request*  — caller submits the new value + current password,
     receives a generic 202 ack (per ADR-001 anti-enumeration).
  2. *change-confirm/verify* — caller proves possession of the new
     contact (token from email, OTP from SMS). On success the User row
     is updated, token_version is bumped, and all sessions invalidate.
"""
from __future__ import annotations

from pydantic import EmailStr, Field

from shared.schemas import _BaseRequestSchema, _BaseSchema


# ─── Email ────────────────────────────────────────────────────────────────────


class EmailChangeRequest(_BaseRequestSchema):
    new_email: EmailStr = Field(..., examples=["new@example.com"])
    current_password: str = Field(..., min_length=1, max_length=128)


class EmailChangeConfirm(_BaseRequestSchema):
    token: str = Field(..., min_length=20, max_length=128)


# ─── Phone ────────────────────────────────────────────────────────────────────


class PhoneChangeRequest(_BaseRequestSchema):
    # E.164 — same constraint applied across the codebase to keep phone_hash
    # deterministic.
    new_phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    current_password: str = Field(..., min_length=1, max_length=128)


class PhoneChangeVerify(_BaseRequestSchema):
    otp: str = Field(..., pattern=r"^\d{6}$")


# ─── Responses ────────────────────────────────────────────────────────────────


class ContactChangeAck(_BaseSchema):
    """Generic 202 ack body for the *request* endpoints. Same message for
    every email — even when the new value collides with another account —
    so the response never reveals account existence."""
    accepted: bool = True
    message: str = "If the contact is valid, we sent a verification message."
    # Dev-only — when RAYCARWASH_ENV=development, the contact-change service
    # echoes the OTP / token back so the mobile test harness can pick it up
    # without scraping logs. Always None in prod.
    dev_token: str | None = None


class ContactChangeSuccess(_BaseSchema):
    """Body for the *confirm/verify* endpoints. The frontend uses this as a
    signal to force re-authentication (token_version has been bumped on
    the server)."""
    new_value_masked: str = Field(..., description="Masked new email/phone for UI confirmation.")
    sessions_invalidated: bool = True

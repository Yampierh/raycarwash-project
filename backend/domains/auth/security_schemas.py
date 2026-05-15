"""
domains/auth/security_schemas.py — Request/response shapes for /auth/two-fa,
/auth/security, /auth/history, and /auth/passkeys (admin).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from shared.schemas import _BaseRequestSchema, _BaseSchema


# ─── /auth/two-fa ─────────────────────────────────────────────────────────────


class TotpEnrollResponse(_BaseSchema):
    """Returned ONCE during enrollment. The client must show the QR (from
    otpauth_uri) and persist the backup_codes somewhere safe — neither is
    retrievable again from the server."""
    secret: str
    otpauth_uri: str
    backup_codes: list[str]


class TotpVerifyRequest(_BaseRequestSchema):
    code: str = Field(..., min_length=6, max_length=20)


class TotpBackupCodesResponse(_BaseSchema):
    backup_codes: list[str]


# ─── /auth/security (Hub-style summary) ──────────────────────────────────────


class SecuritySummaryResponse(_BaseSchema):
    has_password: bool
    two_factor_enabled: bool
    passkeys_count: int
    last_password_change: datetime | None = None
    last_login_at: datetime | None = None
    step_up_recent: bool
    active_sessions_count: int
    recent_failed_attempts: int


# ─── /auth/history ────────────────────────────────────────────────────────────


class SecurityHistoryItem(_BaseSchema):
    """Unified shape covering both UserLoginHistory rows and AuditLog
    rows filtered to security actions. `type` discriminates the source."""
    id: uuid.UUID
    type: str  # "login" | "audit"
    occurred_at: datetime
    summary: str
    ip_address: str | None = None
    user_agent: str | None = None
    device_name: str | None = None
    was_successful: bool | None = None
    failure_reason: str | None = None
    details: dict | None = None


# ─── /auth/passkeys admin ─────────────────────────────────────────────────────


class PasskeySummary(_BaseSchema):
    id: uuid.UUID
    device_name: str | None = None
    created_at: datetime
    last_used_at: datetime | None = None


class PasskeyRenameRequest(_BaseRequestSchema):
    device_name: str = Field(..., min_length=1, max_length=80)

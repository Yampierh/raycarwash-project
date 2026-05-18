"""
domains/users/provider_verification_schemas.py — shapes for
`/api/v1/users/me/provider-verification` and `/me/provider-achievements`
(Phase 5 chunk Y5).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from shared.schemas import _BaseSchema


# ─── Verification ────────────────────────────────────────────────────────────


class VerificationStartResponse(_BaseSchema):
    """What the mobile SDK needs to launch the Stripe Identity sheet.

    `is_dev_bypass=True` means STRIPE_SECRET_KEY is a placeholder OR
    DEBUG=True — the frontend skips Stripe.js and the existing
    `/api/v1/detailers/verification/submit` flow handles dev auto-
    approval. Phase 5 doesn't ship a /users/me equivalent of /submit
    because the data already flows cleanly through the legacy path."""
    is_dev_bypass: bool
    client_secret: str | None = None
    session_id: str | None = None
    stripe_publishable_key: str | None = None


class VerificationStatusResponse(_BaseSchema):
    """Read-only mirror of the verification columns on ProviderProfile.
    The webhook in domains/payments/webhook_router.py drives these
    fields from Stripe Identity events; we just surface them."""
    verification_status: str  # not_submitted | pending | approved | rejected
    legal_full_name: str | None = None
    verification_submitted_at: datetime | None = None
    verification_reviewed_at: datetime | None = None
    rejection_reason: str | None = None
    has_active_session: bool = False


# ─── Achievements ────────────────────────────────────────────────────────────


class AchievementResponse(_BaseSchema):
    id: uuid.UUID
    achievement_type: str
    metadata_: dict | None = None
    awarded_at: datetime

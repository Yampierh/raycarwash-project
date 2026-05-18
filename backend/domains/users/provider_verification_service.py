"""
domains/users/provider_verification_service.py — orchestration for
`/api/v1/users/me/provider-verification` and `/me/provider-achievements`
(Phase 5 chunk Y5).

The actual Stripe Identity session creation is deliberately re-
implemented here (not delegated to the legacy /detailers/verification
router) because:
  1. The legacy router is a FastAPI handler — calling it would require
     manufacturing a Request, which is uglier than 30 lines of duplicated
     Stripe SDK calls.
  2. The dev-bypass branch is shared with the legacy path via the same
     STRIPE_SECRET_KEY check, so behaviour stays consistent.
  3. The webhook (`identity.verification_session.{verified,
     requires_input}`) in `domains/payments/webhook_router.py` already
     updates the ProviderProfile columns we surface here — no second
     side-effect path needed.

`has_active_session` on the status response tells the frontend whether
the stored session_id is still in-flight (vs. terminal). Stripe doesn't
expose a status-lookup endpoint we can hit cheaply, so we infer from
verification_status: "pending" → active, anything else → not active.
"""
from __future__ import annotations

import logging
from typing import Sequence

import stripe
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.middleware.audit_context import AuditContext, get_audit_context
from domains.providers.achievement import ProviderAchievement
from domains.providers.models import ProviderProfile
from domains.users.models import User
from domains.users.provider_verification_schemas import (
    VerificationStartResponse,
    VerificationStatusResponse,
)

logger = logging.getLogger(__name__)


def _is_stripe_placeholder() -> bool:
    return get_settings().STRIPE_SECRET_KEY in (
        "sk_test_placeholder", "sk_live_placeholder", "",
    )


class ProviderVerificationService:
    def __init__(self, db: AsyncSession, audit_ctx: AuditContext) -> None:
        self.db = db
        self.audit_ctx = audit_ctx

    async def _require_provider(self, user: User) -> ProviderProfile:
        pp = (await self.db.execute(
            select(ProviderProfile).where(ProviderProfile.user_id == user.id)
        )).scalar_one_or_none()
        if pp is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "conflict",
                    "message": "Activate provider mode before starting verification.",
                },
            )
        return pp

    # ─── POST /me/provider-verification ─────────────────────────────────────

    async def start(self, user: User) -> VerificationStartResponse:
        """Create a Stripe Identity session and stamp the row.

        Mirrors `domains/providers/verification_router.verification_start`:
          - DEBUG=True OR placeholder Stripe key → dev bypass.
          - Otherwise → real Stripe SDK call. The session metadata
            carries `user_id` so the webhook can look us back up.
        """
        pp = await self._require_provider(user)

        settings = get_settings()
        is_dev_bypass = settings.DEBUG or _is_stripe_placeholder()

        if is_dev_bypass:
            logger.info(
                "Verification dev bypass | user_id=%s (DEBUG=%s placeholder=%s)",
                user.id, settings.DEBUG, _is_stripe_placeholder(),
            )
            return VerificationStartResponse(is_dev_bypass=True)

        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            session = stripe.identity.VerificationSession.create(
                type="document",
                metadata={"user_id": str(user.id)},
                options={"document": {"require_matching_selfie": True}},
            )
        except stripe.error.StripeError as exc:
            logger.error("Stripe Identity session creation failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "service_unavailable",
                    "message": "Could not start verification. Please try again.",
                },
            )

        # Persist the session id immediately so the GET status path can
        # surface has_active_session before the webhook lands.
        pp.stripe_verification_session_id = session.id
        if pp.verification_status == "not_submitted":
            pp.verification_status = "pending"
        await self.db.flush()

        return VerificationStartResponse(
            is_dev_bypass=False,
            client_secret=session.client_secret,
            session_id=session.id,
            stripe_publishable_key=settings.STRIPE_PUBLISHABLE_KEY,
        )

    # ─── GET /me/provider-verification ──────────────────────────────────────

    async def status(self, user: User) -> VerificationStatusResponse:
        pp = await self._require_provider(user)
        return VerificationStatusResponse(
            verification_status=pp.verification_status or "not_submitted",
            legal_full_name=pp.legal_full_name,
            verification_submitted_at=pp.verification_submitted_at,
            verification_reviewed_at=pp.verification_reviewed_at,
            rejection_reason=pp.rejection_reason,
            # "pending" means we minted a session that hasn't gone
            # terminal yet — frontend should re-render the resume CTA.
            has_active_session=(
                pp.verification_status == "pending"
                and pp.stripe_verification_session_id is not None
            ),
        )

    # ─── GET /me/provider-achievements ──────────────────────────────────────

    async def list_achievements(
        self, user: User,
    ) -> Sequence[ProviderAchievement]:
        # Achievements are surfaced regardless of activation state — a
        # legacy user could have earned badges, then deactivated. No
        # _require_provider call here.
        rows = (await self.db.scalars(
            select(ProviderAchievement)
            .where(ProviderAchievement.provider_user_id == user.id)
            .order_by(ProviderAchievement.awarded_at.desc())
        )).all()
        return rows


def get_provider_verification_service(
    db: AsyncSession, request,
) -> ProviderVerificationService:
    return ProviderVerificationService(
        db=db, audit_ctx=get_audit_context(request),
    )

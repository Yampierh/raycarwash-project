"""
domains/users/provider_verification_router.py — verification + achievements
endpoints under /api/v1/users/me (Phase 5 chunk Y5).

Endpoints per plan §2.12:
  POST /me/provider-verification    initiate Stripe Identity session
  GET  /me/provider-verification    current status + has_active_session
  GET  /me/provider-achievements    read-only list of badges

The /submit half of the legacy verification flow stays under
`/api/v1/detailers/verification/submit` — it captures personal info
that doesn't map cleanly to the resource-oriented /users/me surface.
Phase 5 only exposes the start + status pair, which is what the
mobile ProviderHubScreen needs.
"""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from domains.auth.service import get_current_user
from domains.users.models import User
from domains.users.provider_verification_schemas import (
    AchievementResponse,
    VerificationStartResponse,
    VerificationStatusResponse,
)
from domains.users.provider_verification_service import (
    get_provider_verification_service,
)
from infrastructure.db.session import get_db
from shared.schemas import Envelope

router = EnvelopeRouter(
    prefix="/api/v1/users/me",
    tags=["User Provider Verification"],
)


# ─── Verification: start ────────────────────────────────────────────────────


@router.post(
    "/provider-verification",
    response_model=Envelope[VerificationStartResponse],
    summary="Create a Stripe Identity verification session. Returns "
            "is_dev_bypass=true when DEBUG or the Stripe key is a "
            "placeholder; the frontend then skips Stripe.js and uses "
            "the dev auto-approve path on /detailers/verification/submit.",
    responses={
        409: {"description": "Provider mode not active — activate first."},
        502: {"description": "Stripe is currently unavailable."},
    },
)
async def start_verification(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[VerificationStartResponse]:
    service = get_provider_verification_service(db, request)
    result = await service.start(current_user)
    await db.commit()
    return Envelope[VerificationStartResponse](data=result)


# ─── Verification: status ───────────────────────────────────────────────────


@router.get(
    "/provider-verification",
    response_model=Envelope[VerificationStatusResponse],
    summary="Read current verification state. Mirrors the columns the "
            "identity.verification_session.{verified,requires_input} "
            "webhook drives, plus has_active_session for the UI's "
            "'Resume verification' CTA.",
    responses={
        409: {"description": "Provider mode not active — activate first."},
    },
)
async def get_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[VerificationStatusResponse]:
    service = get_provider_verification_service(db, request)
    return Envelope[VerificationStatusResponse](
        data=await service.status(current_user)
    )


# ─── Achievements ───────────────────────────────────────────────────────────


@router.get(
    "/provider-achievements",
    response_model=Envelope[list[AchievementResponse]],
    summary="List the caller's earned badges (newest first). Read-only "
            "from this endpoint — grants happen via the daily "
            "achievement_evaluator worker (Phase 5 chunk Y6) or admin "
            "intervention.",
)
async def list_achievements(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[AchievementResponse]]:
    service = get_provider_verification_service(db, request)
    rows = await service.list_achievements(current_user)
    return Envelope[list[AchievementResponse]](
        data=[
            AchievementResponse(
                id=row.id,
                achievement_type=row.achievement_type,
                metadata_=row.metadata_,
                awarded_at=row.awarded_at,
            )
            for row in rows
        ]
    )

# app/routers/verification_router.py
#
# Detailer identity verification via Stripe Identity.
#
# Endpoints:
#   POST /api/v1/detailers/verification/start   — create VerificationSession (or dev bypass)
#   POST /api/v1/detailers/verification/submit  — save personal info + consent
#   GET  /api/v1/detailers/verification/status  — get current verification state
#
# DEV BYPASS:
#   When DEBUG=True, /start returns { "is_dev_bypass": true } instead of a real
#   Stripe client_secret. The frontend skips the Stripe Identity sheet and calls
#   /submit directly. The backend sets verification_status = "approved" immediately.
#   This lets the entire onboarding flow work end-to-end without a Stripe account.

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from domains.auth.service import get_current_user
from infrastructure.db.session import get_db
from domains.providers.models import ProviderProfile
from domains.users.models import User

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(
    prefix="/api/v1/detailers/verification",
    tags=["Detailer Verification"],
)


# ------------------------------------------------------------------ #
#  Schemas                                                            #
# ------------------------------------------------------------------ #

class VerificationStartResponse(BaseModel):
    is_dev_bypass: bool
    client_secret: str | None = None
    session_id: str | None = None
    stripe_publishable_key: str | None = None


class VerificationSubmitRequest(BaseModel):
    legal_full_name: str = Field(..., min_length=2, max_length=200)
    date_of_birth: date
    address_line1: str = Field(..., min_length=3, max_length=200)
    city: str = Field(..., min_length=2, max_length=120)
    state: str = Field(..., min_length=2, max_length=60)
    zip_code: str = Field(..., min_length=3, max_length=20)
    background_check_consent: bool
    session_id: str | None = None          # None for dev bypass


class VerificationStatusResponse(BaseModel):
    verification_status: str              # not_submitted | pending | approved | rejected
    legal_full_name: str | None
    verification_submitted_at: datetime | None
    verification_reviewed_at: datetime | None
    rejection_reason: str | None


# ------------------------------------------------------------------ #
#  Helpers                                                            #
# ------------------------------------------------------------------ #

async def _get_or_create_profile(user: User, db: AsyncSession) -> ProviderProfile:
    """Return the detailer's ProviderProfile, creating a skeleton if missing."""
    result = await db.execute(
        select(ProviderProfile).where(ProviderProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = ProviderProfile(user_id=user.id)
        db.add(profile)
        await db.flush()
    return profile


# ------------------------------------------------------------------ #
#  POST /detailers/verification/start                                 #
# ------------------------------------------------------------------ #

@router.post(
    "/start",
    response_model=VerificationStartResponse,
    status_code=status.HTTP_200_OK,
    summary="Start a Stripe Identity verification session.",
    description=(
        "Creates a Stripe Identity VerificationSession and returns the client_secret "
        "for the mobile SDK. In dev mode (DEBUG=True or placeholder Stripe key), "
        "returns `is_dev_bypass: true` so the frontend skips the Stripe sheet."
    ),
)
async def verification_start(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VerificationStartResponse:
    is_placeholder = settings.STRIPE_SECRET_KEY in (
        "sk_test_placeholder", "sk_live_placeholder", ""
    )
    is_dev_bypass = settings.DEBUG or is_placeholder

    if is_dev_bypass:
        logger.info(
            "Verification dev bypass | user_id=%s (DEBUG=%s placeholder=%s)",
            current_user.id, settings.DEBUG, is_placeholder,
        )
        return VerificationStartResponse(is_dev_bypass=True)

    # --- Real Stripe Identity session ---
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        session = stripe.identity.VerificationSession.create(
            type="document",
            metadata={"user_id": str(current_user.id)},
            options={"document": {"require_matching_selfie": True}},
        )
    except stripe.error.StripeError as exc:
        logger.error("Stripe Identity session creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not create verification session. Please try again.",
        )

    return VerificationStartResponse(
        is_dev_bypass=False,
        client_secret=session.client_secret,
        session_id=session.id,
        stripe_publishable_key=settings.STRIPE_PUBLISHABLE_KEY,
    )


# ------------------------------------------------------------------ #
#  POST /detailers/verification/submit                                #
# ------------------------------------------------------------------ #

@router.post(
    "/submit",
    status_code=status.HTTP_200_OK,
    summary="Submit detailer personal info and consent.",
    description=(
        "Saves the detailer's legal info and background-check consent. "
        "Links the Stripe VerificationSession if provided. "
        "In dev bypass mode (session_id=None), immediately approves the profile."
    ),
)
async def verification_submit(
    body: VerificationSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not body.background_check_consent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Background check consent is required to become a detailer.",
        )

    profile = await _get_or_create_profile(current_user, db)

    now = datetime.now(timezone.utc)
    profile.legal_full_name = body.legal_full_name
    profile.date_of_birth = body.date_of_birth
    profile.address_line1 = body.address_line1
    profile.city = body.city
    profile.state = body.state
    profile.zip_code = body.zip_code
    profile.background_check_consent = True
    profile.background_check_consent_at = now
    profile.verification_submitted_at = now

    is_dev_bypass = body.session_id is None
    if is_dev_bypass:
        # Dev mode: approve immediately so onboarding can proceed end-to-end
        profile.verification_status = "approved"
        profile.verification_reviewed_at = now
        profile.is_accepting_bookings = True
        logger.info("Verification auto-approved (dev bypass) | user_id=%s", current_user.id)
    else:
        profile.stripe_verification_session_id = body.session_id
        profile.verification_status = "pending"
        profile.is_accepting_bookings = False
        logger.info(
            "Verification submitted | user_id=%s session=%s",
            current_user.id, body.session_id,
        )

    await db.commit()

    return {
        "verification_status": profile.verification_status,
        "message": (
            "Profile approved — you can now accept bookings."
            if is_dev_bypass
            else "Your application is under review. We'll notify you within 24–48 hours."
        ),
    }


# ------------------------------------------------------------------ #
#  GET /detailers/verification/status                                 #
# ------------------------------------------------------------------ #

@router.get(
    "/status",
    response_model=VerificationStatusResponse,
    summary="Get the current verification status for the authenticated detailer.",
)
async def verification_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VerificationStatusResponse:
    result = await db.execute(
        select(ProviderProfile).where(ProviderProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        return VerificationStatusResponse(
            verification_status="not_submitted",
            legal_full_name=None,
            verification_submitted_at=None,
            verification_reviewed_at=None,
            rejection_reason=None,
        )

    return VerificationStatusResponse(
        verification_status=profile.verification_status,
        legal_full_name=profile.legal_full_name,
        verification_submitted_at=profile.verification_submitted_at,
        verification_reviewed_at=profile.verification_reviewed_at,
        rejection_reason=profile.rejection_reason,
    )

"""
domains/users/provider_profile_router.py — /api/v1/users/me/provider-profile*
and /api/v1/users/me/provider-status (Phase 5 chunk Y2).

Endpoints per plan §2.12:
  POST   /me/provider-profile             activate provider mode
  GET    /me/provider-profile             read own profile
  PATCH  /me/provider-profile             partial update
  POST   /me/provider-profile/deactivate  pause without losing data
  PATCH  /me/provider-status              toggle accepting_bookings
                                           (403 kyc_required if status != approved)

Reads / updates delegate to ProviderProfileService, which wraps the
existing ProviderRepository — no logic duplicated from the legacy
`/api/v1/detailers/me` endpoints (those keep working unchanged).

Activate, deactivate, and the accepting-true side of /provider-status
are step-up gated. Listing your own profile is not — it's read-mostly
UX surfaced on the Hub.
"""
from __future__ import annotations

from fastapi import Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from app.core.step_up import require_step_up
from domains.auth.service import get_current_user
from domains.users.models import User
from domains.users.provider_profile_schemas import (
    ProviderProfileActivateRequest,
    ProviderProfileResponse,
    ProviderProfileUpdateRequest,
    ProviderStatusUpdateRequest,
)
from domains.users.provider_profile_service import get_provider_profile_service
from infrastructure.db.session import get_db
from shared.schemas import Envelope

router = EnvelopeRouter(
    prefix="/api/v1/users/me",
    tags=["User Provider Profile"],
)


# ─── Activate ────────────────────────────────────────────────────────────────


@router.post(
    "/provider-profile",
    response_model=Envelope[ProviderProfileResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Activate provider mode. Creates ProviderProfile + grants the "
            "`detailer` role + bumps token_version. Idempotent — re-calling "
            "on an existing profile updates business name / display name / "
            "radius instead of 409-ing.",
    responses={
        401: {"description": "Step-up auth required (no recent re-auth)."},
    },
)
async def activate_provider(
    request: Request,
    body: ProviderProfileActivateRequest,
    current_user: User = Depends(require_step_up),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ProviderProfileResponse]:
    service = get_provider_profile_service(db, request)
    profile = await service.activate(current_user, body)
    await db.commit()
    return Envelope[ProviderProfileResponse](data=service.to_response(profile))


# ─── Read ────────────────────────────────────────────────────────────────────


@router.get(
    "/provider-profile",
    response_model=Envelope[ProviderProfileResponse],
    summary="Read the caller's own provider profile.",
    responses={
        404: {"description": "Caller hasn't activated provider mode yet."},
    },
)
async def get_provider(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ProviderProfileResponse]:
    service = get_provider_profile_service(db, request)
    profile = await service.get_or_404(current_user)
    return Envelope[ProviderProfileResponse](data=service.to_response(profile))


# ─── Update ──────────────────────────────────────────────────────────────────


@router.patch(
    "/provider-profile",
    response_model=Envelope[ProviderProfileResponse],
    summary="Partial update of the caller's provider profile. "
            "Verification + accepting-bookings have dedicated endpoints.",
    responses={404: {"description": "Caller hasn't activated provider mode."}},
)
async def update_provider(
    request: Request,
    body: ProviderProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ProviderProfileResponse]:
    service = get_provider_profile_service(db, request)
    profile = await service.update(current_user, body)
    await db.commit()
    return Envelope[ProviderProfileResponse](data=service.to_response(profile))


# ─── Deactivate ──────────────────────────────────────────────────────────────


@router.post(
    "/provider-profile/deactivate",
    response_model=Envelope[ProviderProfileResponse],
    summary="Pause provider mode. Flips is_accepting_bookings=False; the "
            "row + KYC state survive so the user can re-activate later.",
    responses={
        401: {"description": "Step-up auth required."},
        404: {"description": "Caller hasn't activated provider mode."},
    },
)
async def deactivate_provider(
    request: Request,
    current_user: User = Depends(require_step_up),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ProviderProfileResponse]:
    service = get_provider_profile_service(db, request)
    profile = await service.deactivate(current_user)
    await db.commit()
    return Envelope[ProviderProfileResponse](data=service.to_response(profile))


# ─── Status toggle ───────────────────────────────────────────────────────────


@router.patch(
    "/provider-status",
    response_model=Envelope[ProviderProfileResponse],
    summary="Toggle accepting_bookings. Rejects with 403 kyc_required if "
            "the caller's verification_status is not 'approved'.",
    responses={
        403: {"description": "kyc_required: complete identity verification first."},
        404: {"description": "Caller hasn't activated provider mode."},
    },
)
async def set_status(
    request: Request,
    body: ProviderStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ProviderProfileResponse]:
    service = get_provider_profile_service(db, request)
    profile = await service.set_accepting_bookings(
        current_user, body.is_accepting_bookings,
    )
    await db.commit()
    return Envelope[ProviderProfileResponse](data=service.to_response(profile))

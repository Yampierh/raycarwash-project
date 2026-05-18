"""
domains/providers/profiles_router.py — /api/v1/providers/profiles
(Integration plan E1 chunk C).

Multi-profile self-service endpoints. Distinct from the legacy
`/api/v1/users/me/provider-profile*` (Phase 5 chunk Y2) which always
operates on DETAILER. The new endpoints accept `provider_type`
explicitly so the same contract serves DETAILER and MECHANIC.

  POST   /api/v1/providers/profiles          create profile of given type
                                              (step-up gated)
  GET    /api/v1/providers/profiles          list caller's profiles
  GET    /api/v1/providers/profiles/{id}     read a specific profile
  PATCH  /api/v1/providers/profiles/{id}     partial update
                                              (step-up gated)
  DELETE /api/v1/providers/profiles/{id}     soft delete
                                              (step-up gated)
"""
from __future__ import annotations

import uuid

from fastapi import Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from app.core.step_up import require_step_up
from app.middleware.audit_context import get_audit_context
from domains.auth.service import get_current_user
from domains.providers.profiles_schemas import (
    ProviderProfileCreateRequest,
    ProviderProfilePatchRequest,
    ProviderProfileSummary,
)
from domains.providers.profiles_service import ProviderProfilesService
from domains.users.models import User
from infrastructure.db.session import get_db
from shared.schemas import Envelope

router = EnvelopeRouter(
    prefix="/api/v1/providers",
    tags=["Provider Profiles"],
)


def _get_service(db: AsyncSession, request: Request) -> ProviderProfilesService:
    return ProviderProfilesService(db=db, audit_ctx=get_audit_context(request))


# ─── Create ──────────────────────────────────────────────────────────────────


@router.post(
    "/profiles",
    response_model=Envelope[ProviderProfileSummary],
    status_code=status.HTTP_201_CREATED,
    summary=(
        "Create a ProviderProfile of the given vertical. Grants the matching "
        "RBAC role (`detailer` or `mechanic`) if missing. 409 if the caller "
        "already holds a non-deleted profile of that type."
    ),
    responses={
        401: {"description": "Step-up auth required."},
        409: {"description": "Profile of that type already exists."},
    },
)
async def create_profile(
    request: Request,
    body: ProviderProfileCreateRequest,
    current_user: User = Depends(require_step_up),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ProviderProfileSummary]:
    service = _get_service(db, request)
    profile = await service.create_profile(current_user, body)
    await db.commit()
    return Envelope[ProviderProfileSummary](data=service.to_response(profile))


# ─── List ────────────────────────────────────────────────────────────────────


@router.get(
    "/profiles",
    response_model=Envelope[list[ProviderProfileSummary]],
    summary="List the caller's provider profiles (all verticals).",
)
async def list_profiles(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[ProviderProfileSummary]]:
    service = _get_service(db, request)
    profiles = await service.list_profiles(current_user)
    return Envelope[list[ProviderProfileSummary]](
        data=[service.to_response(p) for p in profiles],
    )


# ─── Read one ────────────────────────────────────────────────────────────────


@router.get(
    "/profiles/{profile_id}",
    response_model=Envelope[ProviderProfileSummary],
    summary="Read a specific provider profile by id. 404 if not owned by caller.",
    responses={404: {"description": "Profile not found or not owned by caller."}},
)
async def get_profile(
    request: Request,
    profile_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ProviderProfileSummary]:
    service = _get_service(db, request)
    profile = await service.get_profile(current_user, profile_id)
    return Envelope[ProviderProfileSummary](data=service.to_response(profile))


# ─── Update ──────────────────────────────────────────────────────────────────


@router.patch(
    "/profiles/{profile_id}",
    response_model=Envelope[ProviderProfileSummary],
    summary=(
        "Partial update of a provider profile. Step-up gated. KYC-gated when "
        "flipping is_active=True (403 kyc_required if verification_status != "
        "'approved')."
    ),
    responses={
        401: {"description": "Step-up auth required."},
        403: {"description": "KYC required to activate this profile."},
        404: {"description": "Profile not found or not owned by caller."},
    },
)
async def patch_profile(
    request: Request,
    profile_id: uuid.UUID,
    body: ProviderProfilePatchRequest,
    current_user: User = Depends(require_step_up),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ProviderProfileSummary]:
    service = _get_service(db, request)
    profile = await service.update_profile(current_user, profile_id, body)
    await db.commit()
    return Envelope[ProviderProfileSummary](data=service.to_response(profile))


# ─── Delete ──────────────────────────────────────────────────────────────────


@router.delete(
    "/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary=(
        "Soft-delete a provider profile. Step-up gated. Role assignment "
        "is intentionally retained so the user keeps access to historical "
        "appointments and audit logs from this vertical."
    ),
    responses={
        401: {"description": "Step-up auth required."},
        404: {"description": "Profile not found or not owned by caller."},
    },
)
async def delete_profile(
    request: Request,
    profile_id: uuid.UUID,
    current_user: User = Depends(require_step_up),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = _get_service(db, request)
    await service.delete_profile(current_user, profile_id)
    await db.commit()

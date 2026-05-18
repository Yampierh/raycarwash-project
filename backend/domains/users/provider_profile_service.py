"""
domains/users/provider_profile_service.py — orchestration for
`/api/v1/users/me/provider-profile*` (Phase 5 chunk Y2).

Owns the activation flow (creates ProviderProfile + grants the
`detailer` role + audit log + bumps token_version so next refresh
picks up the new role) and the partial-update / status-toggle
operations. Reads existing ProviderProfile via the existing
ProviderRepository — no logic duplicated from the legacy
`/api/v1/detailers/me` endpoints.

KYC enforcement: PATCH /provider-status with is_accepting_bookings=True
is rejected 403 `kyc_required` unless verification_status == "approved".
The activate endpoint deliberately does NOT auto-set accepting=True
either; the detailer goes through Stripe Identity in Y5 first.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.audit_context import AuditContext, get_audit_context
from domains.audit.models import AuditAction
from domains.audit.repository import AuditRepository
from domains.auth.models import Role, UserRoleAssociation
from domains.providers.models import ProviderProfile
from domains.providers.repository import ProviderRepository
from domains.users.models import User
from domains.users.provider_profile_schemas import (
    ProviderProfileActivateRequest,
    ProviderProfileResponse,
    ProviderProfileUpdateRequest,
)

logger = logging.getLogger(__name__)


_DEFAULT_WORKING_HOURS: dict = {
    "monday":    {"start": "08:00", "end": "18:00", "enabled": True},
    "tuesday":   {"start": "08:00", "end": "18:00", "enabled": True},
    "wednesday": {"start": "08:00", "end": "18:00", "enabled": True},
    "thursday":  {"start": "08:00", "end": "18:00", "enabled": True},
    "friday":    {"start": "08:00", "end": "18:00", "enabled": True},
    "saturday":  {"start": "09:00", "end": "16:00", "enabled": True},
    "sunday":    {"start": None,    "end": None,    "enabled": False},
}


class ProviderProfileService:
    def __init__(self, db: AsyncSession, audit_ctx: AuditContext) -> None:
        self.db = db
        self.audit_ctx = audit_ctx
        self.repo = ProviderRepository(db)
        self.audit_repo = AuditRepository(db)

    # ─── Reads ──────────────────────────────────────────────────────────────

    async def get_or_404(self, user: User) -> ProviderProfile:
        profile = await self.repo.get_profile(user.id)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "resource_not_found",
                    "message": "Provider profile not found. Activate via POST /users/me/provider-profile.",
                },
            )
        return profile

    def to_response(self, profile: ProviderProfile) -> ProviderProfileResponse:
        return ProviderProfileResponse(
            user_id=profile.user_id,
            business_name=profile.business_name,
            display_name=profile.display_name,
            tagline=profile.tagline,
            bio=profile.bio,
            years_of_experience=profile.years_of_experience,
            is_accepting_bookings=profile.is_accepting_bookings,
            service_radius_miles=profile.service_radius_miles,
            average_rating=(
                float(profile.average_rating)
                if profile.average_rating is not None else None
            ),
            total_reviews=profile.total_reviews,
            total_services_completed=getattr(profile, "total_services_completed", 0) or 0,
            earnings_lifetime_cents=getattr(profile, "earnings_lifetime_cents", 0) or 0,
            verification_status=profile.verification_status or "not_submitted",
            background_check_consent=profile.background_check_consent,
            social_links=profile.social_links,
            cover_photo_s3_key=profile.cover_photo_s3_key,
            # TODO(phase 5): wire `cover_url` via the public storage signer
            # once Phase 2's avatar URL builder is generalized for arbitrary
            # bucket keys. For now we surface the raw key.
            cover_url=None,
            working_hours=profile.working_hours,
            timezone=getattr(profile, "timezone", None),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    # ─── Activate ───────────────────────────────────────────────────────────

    async def activate(
        self, user: User, body: ProviderProfileActivateRequest
    ) -> ProviderProfile:
        """Promote a user to detailer mode.

        Idempotent at the row level: if a ProviderProfile already exists
        for the user we update the business/display name + radius from
        the body (the user effectively "edits" their activation) rather
        than 409-ing. The role assignment is also idempotent."""
        # 1. Ensure the detailer role exists; assign if missing.
        role = (await self.db.execute(
            select(Role).where(Role.name == "detailer")
        )).scalar_one_or_none()
        if role is None:
            # RBAC seed missing — environment misconfiguration. Surface
            # as 500 because the user can't recover from this client-side.
            logger.error("activate: detailer role missing from RBAC seed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"code": "internal_error", "message": "RBAC misconfiguration."},
            )

        already_has_role = any(
            ur.role_id == role.id for ur in (user.user_roles or [])
        )
        if not already_has_role:
            self.db.add(UserRoleAssociation(user_id=user.id, role_id=role.id))

        # 2. Upsert ProviderProfile.
        profile = await self.repo.get_profile(user.id)
        new_profile = profile is None
        if profile is None:
            profile = ProviderProfile(
                user_id=user.id,
                business_name=body.business_name,
                display_name=body.display_name,
                service_radius_miles=body.service_radius_miles,
                is_accepting_bookings=False,  # gated on KYC
                verification_status="not_submitted",
                working_hours=_DEFAULT_WORKING_HOURS,
            )
            self.db.add(profile)
        else:
            profile.business_name = body.business_name
            if body.display_name is not None:
                profile.display_name = body.display_name
            profile.service_radius_miles = body.service_radius_miles

        # NOTE: we deliberately do NOT bump token_version here.
        # `require_role` (used by `/api/v1/detailers/*`) reads
        # user.user_roles from DB on every request, so the new role
        # takes effect on the next call without invalidating the
        # caller's current access token. Bumping would log the user
        # out mid-onboarding, which is the opposite of what we want.
        # Phase 6's PATCH /active-role is different — it rotates the
        # refresh because the active_role lives IN the JWT claim and
        # a stolen refresh could otherwise emit stale tokens.

        await self.db.flush()

        await self.audit_repo.log(
            action=AuditAction.PROVIDER_MODE_SWITCHED,
            entity_type="provider_profile",
            entity_id=str(profile.id),
            actor_id=user.id,
            new_value={
                "business_name": profile.business_name,
                "activated": new_profile,
                "role_granted": not already_has_role,
            },
            audit_ctx=self.audit_ctx,
        )
        return profile

    # ─── Update ─────────────────────────────────────────────────────────────

    async def update(
        self, user: User, body: ProviderProfileUpdateRequest
    ) -> ProviderProfile:
        profile = await self.get_or_404(user)

        old = {
            "business_name": profile.business_name,
            "display_name": profile.display_name,
            "tagline": profile.tagline,
            "service_radius_miles": profile.service_radius_miles,
        }

        for field in (
            "business_name", "display_name", "tagline", "bio",
            "years_of_experience", "service_radius_miles",
            "social_links", "working_hours",
        ):
            value = getattr(body, field)
            if value is not None:
                setattr(profile, field, value)

        await self.db.flush()
        await self.audit_repo.log(
            action=AuditAction.PROVIDER_PROFILE_UPDATED,
            entity_type="provider_profile",
            entity_id=str(profile.id),
            actor_id=user.id,
            old_value=old,
            new_value={
                "business_name": profile.business_name,
                "display_name": profile.display_name,
                "tagline": profile.tagline,
                "service_radius_miles": profile.service_radius_miles,
            },
            audit_ctx=self.audit_ctx,
        )
        return profile

    # ─── Deactivate ─────────────────────────────────────────────────────────

    async def deactivate(self, user: User) -> ProviderProfile:
        """Pause detailer mode without losing data. Flips
        is_accepting_bookings=False; the row + KYC state survive so the
        user can re-activate later."""
        profile = await self.get_or_404(user)
        profile.is_accepting_bookings = False
        await self.db.flush()
        await self.audit_repo.log(
            action=AuditAction.PROVIDER_STATUS_CHANGED,
            entity_type="provider_profile",
            entity_id=str(profile.id),
            actor_id=user.id,
            new_value={"is_accepting_bookings": False, "via": "deactivate"},
            audit_ctx=self.audit_ctx,
        )
        return profile

    # ─── Status toggle ──────────────────────────────────────────────────────

    async def set_accepting_bookings(
        self, user: User, accepting: bool
    ) -> ProviderProfile:
        profile = await self.get_or_404(user)

        if accepting and profile.verification_status != "approved":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "kyc_required",
                    "message": (
                        "Complete identity verification before accepting "
                        "bookings."
                    ),
                },
            )

        if profile.is_accepting_bookings == accepting:
            # Idempotent — no audit row for a no-op.
            return profile

        profile.is_accepting_bookings = accepting
        await self.db.flush()
        await self.audit_repo.log(
            action=AuditAction.PROVIDER_STATUS_CHANGED,
            entity_type="provider_profile",
            entity_id=str(profile.id),
            actor_id=user.id,
            new_value={"is_accepting_bookings": accepting},
            audit_ctx=self.audit_ctx,
        )
        return profile


def get_provider_profile_service(
    db: AsyncSession, request
) -> ProviderProfileService:
    return ProviderProfileService(db=db, audit_ctx=get_audit_context(request))

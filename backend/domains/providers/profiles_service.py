"""
domains/providers/profiles_service.py — Integration plan E1 chunk C.

Orchestration for `/api/v1/providers/profiles` — the multi-profile
self-service endpoints. Distinct from the legacy
`/api/v1/users/me/provider-profile*` (Phase 5 chunk Y2) which always
operates on the DETAILER row; this service is provider-type agnostic
and is the only place that can mint MECHANIC profiles today.

Responsibilities:
  - create_profile: enforce composite unique (user_id, provider_type),
    grant the matching role if missing, audit log.
  - list_profiles / get_profile: simple reads scoped to the caller.
  - update_profile: partial update with ownership check.
  - delete_profile: soft delete + ownership check.
"""
from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.audit_context import AuditContext
from domains.audit.models import AuditAction
from domains.audit.repository import AuditRepository
from domains.auth.models import Role, UserRoleAssociation
from domains.providers.models import ProviderProfile, ProviderType
from domains.providers.profiles_schemas import (
    ProviderProfileCreateRequest,
    ProviderProfilePatchRequest,
    ProviderProfileSummary,
)
from domains.providers.repository import ProviderRepository
from domains.users.models import User

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


# ─── Role mapping ────────────────────────────────────────────────────────────


# E1.C: provider_type -> RBAC role name. Kept here rather than on the enum
# itself so the seed_rbac module stays the single source of truth for role
# names. Adding a new vertical lands here + in ROLE_DATA/ROLE_PERMISSIONS.
_ROLE_BY_TYPE: dict[str, str] = {
    ProviderType.DETAILER.value: "detailer",
    ProviderType.MECHANIC.value: "mechanic",
}


class ProviderProfilesService:
    def __init__(self, db: AsyncSession, audit_ctx: AuditContext) -> None:
        self.db = db
        self.audit_ctx = audit_ctx
        self.repo = ProviderRepository(db)
        self.audit_repo = AuditRepository(db)

    # ─── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def to_response(profile: ProviderProfile) -> ProviderProfileSummary:
        return ProviderProfileSummary(
            id=profile.id,
            user_id=profile.user_id,
            provider_type=profile.provider_type,
            business_name=profile.business_name,
            display_name=profile.display_name,
            tagline=profile.tagline,
            bio=profile.bio,
            is_active=profile.is_active,
            is_accepting_bookings=profile.is_accepting_bookings,
            verification_status=profile.verification_status or "not_submitted",
            service_radius_miles=profile.service_radius_miles,
            average_rating=(
                float(profile.average_rating)
                if profile.average_rating is not None else None
            ),
            total_reviews=profile.total_reviews or 0,
            total_services_completed=getattr(profile, "total_services_completed", 0) or 0,
            created_at=profile.created_at,
        )

    async def _grant_role_if_missing(self, user: User, provider_type: str) -> bool:
        """
        Assign the role that matches `provider_type` to the user if it's
        not already there. Returns True when the assignment was new
        (used for audit metadata).
        """
        role_name = _ROLE_BY_TYPE.get(provider_type)
        if role_name is None:
            return False
        role = (await self.db.execute(
            select(Role).where(Role.name == role_name)
        )).scalar_one_or_none()
        if role is None:
            # RBAC seed missing — environment misconfiguration, fail loudly.
            logger.error("create_profile: %s role missing from RBAC seed", role_name)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"code": "internal_error", "message": "RBAC misconfiguration."},
            )
        already_has = any(
            ur.role_id == role.id for ur in (user.user_roles or [])
        )
        if not already_has:
            self.db.add(UserRoleAssociation(user_id=user.id, role_id=role.id))
        return not already_has

    async def _load_owned_or_404(
        self, user: User, profile_id,
    ) -> ProviderProfile:
        """Fetch a profile and verify the caller owns it. 404 otherwise so
        we never leak existence to non-owners."""
        profile = await self.repo.get_by_id(profile_id)
        if profile is None or profile.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "resource_not_found",
                    "message": "Provider profile not found.",
                },
            )
        return profile

    # ─── Create ─────────────────────────────────────────────────────────────

    async def create_profile(
        self, user: User, body: ProviderProfileCreateRequest,
    ) -> ProviderProfile:
        """
        Create a ProviderProfile of `provider_type` for the caller. 409
        when the `(user_id, provider_type)` slot is already taken — by
        an active row OR by a soft-deleted one, because the composite
        unique on provider_profiles is plain (not partial). Once
        E1.C-phase2 swaps to a partial unique that ignores soft-deleted
        rows, the pre-check can be relaxed to only block live rows.
        """
        # Slot probe: counts soft-deleted rows on purpose — they still
        # occupy the composite unique slot under the current schema.
        # Without this we'd hit IntegrityError on flush, and an in-flight
        # rollback() corrupts the FastAPI request session.
        if await self.repo.slot_taken(user.id, body.provider_type):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "already_exists",
                    "message": (
                        f"A {body.provider_type} provider profile already "
                        "exists for this user."
                    ),
                },
            )

        # 1. Grant the matching RBAC role if missing.
        role_granted = await self._grant_role_if_missing(user, body.provider_type)

        # 2. Insert the row. is_active starts False because the user still
        #    needs to complete onboarding (Stripe Identity for detailers,
        #    TBD for mechanics) before they show up in search results.
        profile = ProviderProfile(
            user_id=user.id,
            provider_type=body.provider_type,
            business_name=body.business_name,
            display_name=body.display_name,
            tagline=body.tagline,
            bio=body.bio,
            service_radius_miles=body.service_radius_miles,
            is_active=False,
            is_accepting_bookings=False,
            verification_status="not_submitted",
            working_hours=_DEFAULT_WORKING_HOURS,
        )
        self.db.add(profile)
        # Any race that bypasses the slot_taken check (two requests
        # hitting at the same instant) lands on the DB unique and
        # surfaces as 500 from FastAPI's default handler. That's an
        # acceptable trade — the alternative is a manual rollback() in
        # the catch handler, which on the test fixture's session-per-
        # test pattern wipes the seed data and corrupts later tests.
        await self.db.flush()

        await self.audit_repo.log(
            action=AuditAction.PROVIDER_MODE_SWITCHED,
            entity_type="provider_profile",
            entity_id=str(profile.id),
            actor_id=user.id,
            new_value={
                "provider_type": body.provider_type,
                "business_name": profile.business_name,
                "role_granted": role_granted,
                "via": "providers/profiles",
            },
            audit_ctx=self.audit_ctx,
        )
        return profile

    # ─── Read ───────────────────────────────────────────────────────────────

    async def list_profiles(self, user: User) -> list[ProviderProfile]:
        return await self.repo.list_for_user(user.id)

    async def get_profile(self, user: User, profile_id) -> ProviderProfile:
        return await self._load_owned_or_404(user, profile_id)

    # ─── Update ─────────────────────────────────────────────────────────────

    async def update_profile(
        self, user: User, profile_id, body: ProviderProfilePatchRequest,
    ) -> ProviderProfile:
        profile = await self._load_owned_or_404(user, profile_id)
        old = {
            "business_name": profile.business_name,
            "display_name": profile.display_name,
            "tagline": profile.tagline,
            "bio": profile.bio,
            "service_radius_miles": profile.service_radius_miles,
            "is_active": profile.is_active,
        }

        for field in (
            "business_name", "display_name", "tagline", "bio",
            "service_radius_miles",
        ):
            value = getattr(body, field, None)
            if value is not None:
                setattr(profile, field, value)

        if body.is_active is not None:
            # E1.E: setting is_active also covers is_accepting_bookings —
            # that name is now a Python @property forwarding to is_active.
            # KYC gating still applies when flipping to True.
            if body.is_active and profile.verification_status != "approved":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "kyc_required",
                        "message": (
                            "Complete identity verification before activating "
                            "this provider profile."
                        ),
                    },
                )
            profile.is_active = body.is_active

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
                "bio": profile.bio,
                "service_radius_miles": profile.service_radius_miles,
                "is_active": profile.is_active,
            },
            audit_ctx=self.audit_ctx,
        )
        return profile

    # ─── Delete ─────────────────────────────────────────────────────────────

    async def delete_profile(self, user: User, profile_id) -> None:
        """
        Soft delete. Once deleted the user can re-enroll in the same
        vertical (the composite unique only excludes is_deleted=False
        rows) — see Phase 5 docs §soft-delete contract.

        Note: the role is intentionally NOT revoked here. Removing the
        role would also revoke access to historical appointments and
        audit logs that the user might still legitimately query. The
        role can be revoked manually by an admin if desired.
        """
        profile = await self._load_owned_or_404(user, profile_id)
        provider_type = profile.provider_type
        profile.is_deleted = True
        await self.db.flush()
        await self.audit_repo.log(
            action=AuditAction.PROVIDER_MODE_SWITCHED,
            entity_type="provider_profile",
            entity_id=str(profile.id),
            actor_id=user.id,
            new_value={
                "provider_type": provider_type,
                "action": "soft_delete",
                "via": "providers/profiles",
            },
            audit_ctx=self.audit_ctx,
        )

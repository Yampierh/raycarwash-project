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
from domains.locations.models import City, CityStatus
from domains.providers.models import ProviderProfile, ProviderType
from domains.providers.repository import ProviderRepository
from domains.users.models import User
from domains.users.provider_profile_schemas import (
    ProviderApplicationSubmitResponse,
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
            # Plan 24 Wave 1 — signup metadata. `ssn_last_4_encrypted` is
            # intentionally never read back; it's write-only.
            home_city_code=profile.home_city_code,
            water_tank_gallons=profile.water_tank_gallons,
            services_offered=profile.services_offered,
            application_status=getattr(profile, "application_status", "draft"),
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

        # 2. Upsert ProviderProfile. E1.B: this service activates the
        # DETAILER vertical specifically (legacy endpoint contract). The
        # MECHANIC profile lands via the new /api/v1/providers/profiles
        # endpoint in E1.C, which lets the user pick the type.
        profile = await self.repo.get_profile(user.id, ProviderType.DETAILER)
        new_profile = profile is None
        if profile is None:
            profile = ProviderProfile(
                user_id=user.id,
                provider_type=ProviderType.DETAILER.value,
                business_name=body.business_name,
                display_name=body.display_name,
                service_radius_miles=body.service_radius_miles,
                is_accepting_bookings=False,  # gated on KYC
                is_active=False,  # mirrors is_accepting_bookings (E1.A) until KYC flips it
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

        # Plan 24 Wave 1 — server-side validation for fields with
        # constraints Pydantic alone can't enforce.
        if body.home_city_code is not None:
            await self._assert_city_active(body.home_city_code)

        old = {
            "business_name": profile.business_name,
            "display_name": profile.display_name,
            "tagline": profile.tagline,
            "service_radius_miles": profile.service_radius_miles,
            "home_city_code": profile.home_city_code,
            "water_tank_gallons": profile.water_tank_gallons,
            "services_offered": profile.services_offered,
        }

        for field in (
            "business_name", "display_name", "tagline", "bio",
            "years_of_experience", "service_radius_miles",
            "social_links", "working_hours",
            # Plan 24 Wave 1 — signup multi-step fields
            "home_city_code", "water_tank_gallons", "services_offered",
        ):
            value = getattr(body, field)
            if value is not None:
                setattr(profile, field, value)

        # `ssn_last_4` (raw) → `ssn_last_4_encrypted` (storage column).
        # EncryptedType handles the at-rest encryption transparently;
        # we just need to remap the API field name to the column name.
        if body.ssn_last_4 is not None:
            profile.ssn_last_4_encrypted = body.ssn_last_4

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
                "home_city_code": profile.home_city_code,
                "water_tank_gallons": profile.water_tank_gallons,
                "services_offered": profile.services_offered,
                # SSN intentionally NOT in audit metadata — even encrypted,
                # the only legitimate consumer is the bg-check adapter.
                "ssn_last_4_updated": body.ssn_last_4 is not None,
            },
            audit_ctx=self.audit_ctx,
        )
        return profile

    async def _assert_city_active(self, code: str) -> None:
        """Reject PATCH if `home_city_code` doesn't reference an
        active or pilot city. Soft-deleted cities are also rejected."""
        city = (await self.db.execute(
            select(City).where(
                City.code == code,
                City.is_deleted.is_(False),
            )
        )).scalar_one_or_none()
        if city is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "city_not_found",
                    "message": (
                        f"Unknown city code '{code}'. "
                        "See GET /api/v1/cities for valid options."
                    ),
                },
            )
        if city.status not in (CityStatus.ACTIVE.value, CityStatus.PILOT.value):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "city_not_accepting_providers",
                    "message": (
                        f"City '{code}' is not currently accepting new "
                        f"provider applications (status: {city.status})."
                    ),
                },
            )

    # ─── Deactivate ─────────────────────────────────────────────────────────

    async def deactivate(self, user: User) -> ProviderProfile:
        """Pause detailer mode without losing data. Flips
        is_accepting_bookings=False; the row + KYC state survive so the
        user can re-activate later. E1.E: the column was dropped — the
        attribute now forwards to is_active via @property."""
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

        # E1.E: is_accepting_bookings is now a @property that forwards
        # to is_active. The single assignment below sets the underlying
        # column.
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

    # ─── Submit application (Plan 24 §3 P-7) ────────────────────────────────

    # Field-name → human-readable label. Order matches the design's
    # multi-step signup so the missing-fields list mirrors what the
    # user just walked through (Step 2 first, Step 7 last).
    _REQUIRED_SUBMIT_FIELDS: tuple[tuple[str, str], ...] = (
        ("legal_full_name",          "Legal full name"),
        ("date_of_birth",            "Date of birth"),
        ("ssn_last_4_encrypted",     "SSN last 4"),
        ("home_city_code",           "Home city"),
        ("service_radius_miles",     "Travel radius"),
        ("water_tank_gallons",       "Water tank size"),
        ("services_offered",         "Services you can offer"),
        ("background_check_consent", "Background-check consent"),
    )

    async def submit_application(
        self, user: User,
    ) -> ProviderApplicationSubmitResponse:
        """Transition application_status `draft → submitted`.

        Plan 24 §3 P-7. Validates that every required signup field is
        populated; if not, returns 422 with the list of missing fields
        so the frontend can deep-link the user back to the right step.

        Subsequent transitions (`submitted → bg_check_pending →
        docs_review → approved | rejected`) are driven by external
        events (Checkr webhook, admin approval) — not exposed via
        the customer-facing API.
        """
        profile = await self.get_or_404(user)

        current = getattr(profile, "application_status", "draft")
        if current != "draft":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "application_not_in_draft",
                    "message": (
                        f"Application is in '{current}' state and cannot be "
                        f"re-submitted. Contact support if you need to amend it."
                    ),
                },
            )

        missing = [
            label
            for field, label in self._REQUIRED_SUBMIT_FIELDS
            if not getattr(profile, field, None)
        ]
        # `background_check_consent` is a Boolean — the falsy check above
        # treats `False` as "missing" which is correct (the user must
        # explicitly tick the consent box).
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "application_incomplete",
                    "message": (
                        "Some required fields are missing — finish them "
                        "before submitting."
                    ),
                    "details": [{"field": label} for label in missing],
                },
            )

        now = datetime.now(timezone.utc)
        profile.application_status = "submitted"
        # Reuse the existing verification timestamp so the design's
        # PStep8 timeline can show "Submitted at" without a new column.
        if profile.verification_submitted_at is None:
            profile.verification_submitted_at = now

        await self.db.flush()
        await self.audit_repo.log(
            action=AuditAction.PROVIDER_PROFILE_UPDATED,
            entity_type="provider_profile",
            entity_id=str(profile.id),
            actor_id=user.id,
            old_value={"application_status": "draft"},
            new_value={
                "application_status": "submitted",
                "via": "POST /me/provider-profile/submit",
            },
            audit_ctx=self.audit_ctx,
        )

        return ProviderApplicationSubmitResponse(
            application_status="submitted",
            submitted_at=now,
            next_steps=[
                "Background check running — 24–48h",
                "Document review by compliance team",
                "Identity verification — usually instant",
            ],
        )


def get_provider_profile_service(
    db: AsyncSession, request
) -> ProviderProfileService:
    return ProviderProfileService(db=db, audit_ctx=get_audit_context(request))

"""
domains/users/provider_profile_schemas.py — request/response shapes for
`/api/v1/users/me/provider-profile` (Phase 5 chunk Y2).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from shared.schemas import _BaseRequestSchema, _BaseSchema


class ProviderProfileResponse(_BaseSchema):
    """The provider's own view — includes private fields the public
    detailer-search response intentionally hides."""
    user_id: uuid.UUID
    business_name: str | None = None
    display_name: str | None = None
    tagline: str | None = None
    bio: str | None = None
    years_of_experience: int | None = None

    is_accepting_bookings: bool
    service_radius_miles: int
    average_rating: float | None = None
    total_reviews: int
    total_services_completed: int = 0
    earnings_lifetime_cents: int = 0

    verification_status: str
    background_check_consent: bool

    social_links: dict | None = None
    cover_photo_s3_key: str | None = None
    cover_url: str | None = None

    working_hours: dict | None = None
    timezone: str | None = None

    # Plan 24 Wave 1 — provider signup metadata exposed on read.
    # `ssn_last_4_encrypted` is INTENTIONALLY NOT exposed (write-only;
    # consumed once by Checkr and then dormant).
    home_city_code: str | None = None
    water_tank_gallons: int | None = None
    services_offered: list[str] | None = None
    application_status: str = "draft"

    created_at: datetime
    updated_at: datetime


class ProviderProfileActivateRequest(_BaseRequestSchema):
    """Body for POST /me/provider-profile.

    Minimal at activation — the user is just opting INTO detailer mode;
    they fill the rest via PATCH and the dedicated portfolio/docs flows.
    `business_name` is the only required field so the public profile
    has something to show during the brief window before KYC completes.
    """
    business_name: str = Field(..., min_length=2, max_length=120)
    display_name: str | None = Field(default=None, max_length=80)
    service_radius_miles: int = Field(default=25, ge=1, le=200)


class ProviderProfileUpdateRequest(_BaseRequestSchema):
    """PATCH body — every field optional. Excludes verification +
    accepting_bookings (those have dedicated endpoints with stricter
    guards)."""
    business_name: str | None = Field(default=None, min_length=2, max_length=120)
    display_name: str | None = Field(default=None, max_length=80)
    tagline: str | None = Field(default=None, max_length=140)
    bio: str | None = None
    years_of_experience: int | None = Field(default=None, ge=0, le=80)
    service_radius_miles: int | None = Field(default=None, ge=1, le=200)
    social_links: dict | None = None
    working_hours: dict | None = None

    # Plan 24 Wave 1 — provider signup multi-step fields. All optional
    # on PATCH so signup can save partial drafts step-by-step.
    # `application_status` transitions are NOT exposed here — they go
    # through dedicated endpoints (submit, admin approve/reject) to
    # avoid accidental state changes via routine profile edits.
    ssn_last_4: str | None = Field(
        default=None, min_length=4, max_length=4, pattern=r"^\d{4}$",
        description=(
            "Last 4 of SSN. Encrypted at rest. Surfaced never — "
            "consumed once by the background-check adapter."
        ),
    )
    home_city_code: str | None = Field(
        default=None, min_length=2, max_length=8,
        description=(
            "City code (e.g. fwa, ind). Must reference an active row in "
            "the `cities` table; validated server-side."
        ),
    )
    water_tank_gallons: int | None = Field(
        default=None, ge=0, le=200,
        description="0 = use customer water; 20/40/60+ = own tank.",
    )
    services_offered: list[Literal["soap", "vacuum", "polish", "ceramic"]] | None = Field(
        default=None,
        description=(
            "Granular skill list. `soap` + `vacuum` are baseline; "
            "`polish` and `ceramic` are paid upsell tiers."
        ),
    )


class ProviderStatusUpdateRequest(_BaseRequestSchema):
    """Body for PATCH /me/provider-status. Toggles accepting_bookings.
    Rejected with 403 kyc_required if verification_status != approved."""
    is_accepting_bookings: bool

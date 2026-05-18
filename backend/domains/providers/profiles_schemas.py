"""
domains/providers/profiles_schemas.py — Integration plan E1 chunk C.

Wire shapes for `/api/v1/providers/profiles` — the multi-profile
endpoints that let a single user hold a DETAILER and a MECHANIC
ProviderProfile side by side.

Distinct from the legacy `/api/v1/users/me/provider-profile*` family
(Phase 5 chunk Y2), which always operates on the DETAILER profile.
The new endpoints accept `provider_type` explicitly so the same
contract serves both verticals.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from domains.providers.models import ProviderType
from shared.schemas import _BaseSchema, _BaseRequestSchema


_VALID_TYPE_VALUES = {pt.value for pt in ProviderType}
_TypeLiteral = Literal["detailer", "mechanic"]


# ─── Create ──────────────────────────────────────────────────────────────────


class ProviderProfileCreateRequest(_BaseRequestSchema):
    """
    Body for POST /api/v1/providers/profiles.

    `provider_type` is mandatory — the caller decides which vertical
    they're enrolling in. Everything else is optional so the user can
    expand the profile incrementally via PATCH after creation.
    """
    provider_type: _TypeLiteral = Field(
        ..., description="Vertical the profile represents: 'detailer' or 'mechanic'.",
    )
    business_name: str | None = Field(default=None, min_length=2, max_length=120)
    display_name: str | None = Field(default=None, max_length=80)
    tagline: str | None = Field(default=None, max_length=140)
    bio: str | None = Field(default=None, max_length=1000)
    service_radius_miles: int = Field(default=25, ge=1, le=100)


# ─── Patch ───────────────────────────────────────────────────────────────────


class ProviderProfilePatchRequest(_BaseRequestSchema):
    """
    Body for PATCH /api/v1/providers/profiles/{id}. All fields optional
    — only fields that are explicitly present in the JSON body are
    applied. `provider_type` is intentionally NOT patchable; to switch
    verticals the caller deletes the old profile and creates a new one,
    which keeps the audit story clean.
    """
    business_name: str | None = Field(default=None, min_length=2, max_length=120)
    display_name: str | None = Field(default=None, max_length=80)
    tagline: str | None = Field(default=None, max_length=140)
    bio: str | None = Field(default=None, max_length=1000)
    service_radius_miles: int | None = Field(default=None, ge=1, le=100)
    is_active: bool | None = None


# ─── Read ────────────────────────────────────────────────────────────────────


class ProviderProfileSummary(_BaseSchema):
    """
    Shape returned by both GET /providers/profiles (list) and the
    single-profile responses (POST/GET/PATCH).
    """
    id: uuid.UUID
    user_id: uuid.UUID
    provider_type: _TypeLiteral
    business_name: str | None = None
    display_name: str | None = None
    tagline: str | None = None
    bio: str | None = None
    is_active: bool
    is_accepting_bookings: bool
    verification_status: str = "not_submitted"
    service_radius_miles: int
    average_rating: float | None = None
    total_reviews: int = 0
    total_services_completed: int = 0
    created_at: datetime

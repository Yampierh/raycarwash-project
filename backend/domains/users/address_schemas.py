"""
domains/users/address_schemas.py — request/response shapes for
`/api/v1/users/me/addresses` (Phase 4 chunk T).

The detailed `AddressResponse` is what the dedicated endpoints return.
The Profile Hub's compact `AddressSummary` (defined in hub_schemas) is
what `?include=addresses` returns — same FK, smaller wire shape, so
list rendering on the home screen doesn't pull the H3 cell or lat/lng.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator

from shared.schemas import _BaseRequestSchema, _BaseSchema


# ─── Detailed response ───────────────────────────────────────────────────────


class AddressResponse(_BaseSchema):
    """Full address as returned by GET/POST/PATCH /me/addresses[/{id}]."""
    id: uuid.UUID
    label: str | None = None
    line1: str
    line2: str | None = None
    city: str
    state: str
    zip_code: str
    country: str = "US"
    notes: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    h3_index_r9: str | None = None
    is_default: bool = False
    created_at: datetime
    updated_at: datetime


# ─── Request payloads ────────────────────────────────────────────────────────


class AddressCreateRequest(_BaseRequestSchema):
    label: str | None = Field(default=None, max_length=40)
    line1: str = Field(..., min_length=1, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str = Field(..., min_length=1, max_length=120)
    state: str = Field(..., min_length=1, max_length=60)
    zip_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(default="US", min_length=2, max_length=60)
    notes: str | None = None
    is_default: bool = False
    # Plan 24 §3 C-3 — opt-in coverage gate. When True (used by the
    # customer-signup Step 4 form), the service rejects ZIPs that
    # aren't in the `coverage_zips` table. False (default) preserves
    # the pre-Plan-24 contract so admin-side address edits + existing
    # callers continue to accept any US ZIP.
    enforce_coverage_check: bool = False

    @field_validator("country")
    @classmethod
    def uppercase_country(cls, v: str) -> str:
        return v.upper()

    @field_validator("state")
    @classmethod
    def uppercase_state_when_two_letter(cls, v: str) -> str:
        # US-style two-letter codes get uppercased; international leaves as-is.
        return v.upper() if len(v) == 2 else v


class AddressUpdateRequest(_BaseRequestSchema):
    """PATCH body. All fields optional — unset means "leave alone"."""
    label: str | None = Field(default=None, max_length=40)
    line1: str | None = Field(default=None, min_length=1, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    state: str | None = Field(default=None, min_length=1, max_length=60)
    zip_code: str | None = Field(default=None, min_length=1, max_length=20)
    country: str | None = Field(default=None, min_length=2, max_length=60)
    notes: str | None = None

    @field_validator("country")
    @classmethod
    def uppercase_country(cls, v: str | None) -> str | None:
        return v.upper() if v else v

    @field_validator("state")
    @classmethod
    def uppercase_state_when_two_letter(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.upper() if len(v) == 2 else v

    def has_geocodable_change(self) -> bool:
        """True iff any field that affects the geocoded coordinates is set.
        Used by the service to decide whether to call the geocoding adapter
        again on update — re-geocoding a notes-only edit is wasted work."""
        return any(
            getattr(self, f) is not None
            for f in ("line1", "line2", "city", "state", "zip_code", "country")
        )

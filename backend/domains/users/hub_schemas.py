"""
domains/users/hub_schemas.py — Pydantic shapes for the Profile Hub
(ADR-002b).

`HubResponse` is the wire shape returned by `GET /api/v1/users/me`. `user`
and `verification_badges` are always present; the remaining 11 blocks are
opt-in via `?include=`. Each block is `None` when not requested, mirroring
the optional behavior so consumers can `if data.profile is None: ...`.

Conventions:
- IDs serialize as plain UUID strings.
- Timestamps as ISO-8601 UTC.
- All optional fields default to `None` and are omitted when null thanks
  to `Envelope[T].model_dump_json(exclude_none=True)` in the router.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time

from pydantic import EmailStr, Field

from shared.schemas import _BaseSchema, _BaseRequestSchema


# ─── User core ───────────────────────────────────────────────────────────────


class UserCoreBlock(_BaseSchema):
    """Identity-shaped fields. Always present in HubResponse."""
    id: uuid.UUID
    email: EmailStr
    email_verified: bool
    phone: str | None = None
    phone_verified: bool = False
    role: str | None = Field(default=None, description="Active role for dual-role users.")
    available_roles: list[str] = Field(default_factory=list)
    created_at: datetime


class VerificationBadgesBlock(_BaseSchema):
    """Derived booleans. Always present, cheap to compute."""
    email: bool
    phone: bool
    identity: bool
    background_check: bool


# ─── Profile block ───────────────────────────────────────────────────────────


class ProfileBlock(_BaseSchema):
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    pronouns: str | None = None
    avatar_url: str | None = None
    cover_url: str | None = None
    language: str = "en"
    timezone: str = "America/Indiana/Indianapolis"


# ─── Stats block ─────────────────────────────────────────────────────────────


class StatsBlock(_BaseSchema):
    total_bookings: int = 0
    total_spent_cents: int = 0
    favorite_provider_id: uuid.UUID | None = None
    vehicles_total: int = 0
    favorites_total: int = 0
    member_since: date | None = None


# ─── Security block ──────────────────────────────────────────────────────────


class SecurityBlock(_BaseSchema):
    has_password: bool
    two_factor_enabled: bool
    passkeys_count: int
    last_password_change: datetime | None = None
    last_login_at: datetime | None = None
    step_up_required: bool = False
    active_sessions_count: int = 0
    recent_failed_attempts: int = 0


# ─── Sessions block ──────────────────────────────────────────────────────────


class SessionItem(_BaseSchema):
    id: uuid.UUID
    device_name: str | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    ip_location: str | None = None
    is_current: bool = False
    created_at: datetime
    last_seen_at: datetime | None = None


# ─── Provider block ──────────────────────────────────────────────────────────


class ProviderBlock(_BaseSchema):
    business_name: str | None = None
    display_name: str | None = None
    tagline: str | None = None
    bio: str | None = None
    verification_status: str = "not_submitted"
    rating: float | None = None
    total_jobs: int = 0
    is_accepting_bookings: bool = True


# ─── Client resources (vehicles / addresses / payment_methods / favorites) ──


class VehicleSummary(_BaseSchema):
    id: uuid.UUID
    make: str
    model: str
    year: int
    color: str | None = None
    license_plate: str | None = None
    photo_url: str | None = None
    is_default: bool = False


class AddressSummary(_BaseSchema):
    id: uuid.UUID
    label: str | None = None
    line1: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    is_default: bool = False


class PaymentMethodSummary(_BaseSchema):
    id: uuid.UUID
    brand: str | None = None
    last4: str | None = None
    exp_month: int | None = None
    exp_year: int | None = None
    is_default: bool = False


class FavoriteProviderSummary(_BaseSchema):
    provider_user_id: uuid.UUID
    display_name: str | None = None
    avatar_url: str | None = None
    rating: float | None = None


# ─── Preferences ─────────────────────────────────────────────────────────────


class PreferencesBlock(_BaseSchema):
    default_vehicle_id: uuid.UUID | None = None
    default_address_id: uuid.UUID | None = None
    marketing_opt_in: bool = False
    frequency_preference: str | None = None


# ─── Notifications ───────────────────────────────────────────────────────────


class NotificationsBlock(_BaseSchema):
    preferences: dict = Field(default_factory=dict)
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None


# ─── Hub response ────────────────────────────────────────────────────────────


class HubResponse(_BaseSchema):
    """
    Composite `data` shape returned by `GET /api/v1/users/me`.

    Only `user` and `verification_badges` are guaranteed present. All other
    fields are populated solely when the matching `include=` token was
    requested AND the caller's role allows it. `meta.includes` echoes the
    tokens that were actually returned so the client can cache deterministically.
    """
    user: UserCoreBlock
    verification_badges: VerificationBadgesBlock

    profile: ProfileBlock | None = None
    stats: StatsBlock | None = None
    security: SecurityBlock | None = None
    sessions: list[SessionItem] | None = None
    provider: ProviderBlock | None = None
    vehicles: list[VehicleSummary] | None = None
    addresses: list[AddressSummary] | None = None
    payment_methods: list[PaymentMethodSummary] | None = None
    favorites: list[FavoriteProviderSummary] | None = None
    preferences: PreferencesBlock | None = None
    notifications: NotificationsBlock | None = None


# ─── PATCH /users/me body ────────────────────────────────────────────────────


class HubProfilePatch(_BaseRequestSchema):
    """
    Body for `PATCH /api/v1/users/me`. Only fields that live in the `profile`
    block are mutable here — email/phone changes go through `/me/email/*` and
    `/me/phone/*` (Phase 3), and security toggles live under `/auth/*`.
    """
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    pronouns: str | None = Field(default=None, max_length=20)
    language: str | None = Field(default=None, pattern=r"^[a-z]{2}(-[A-Z]{2})?$")
    timezone: str | None = Field(default=None, max_length=64)

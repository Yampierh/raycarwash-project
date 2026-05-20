from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils import EncryptedType

from app.core.config import get_settings
from infrastructure.db.base import Base, TimestampMixin


def _provider_encryption_key() -> bytes:
    """Reuse the User-level ENCRYPTION_KEY for provider PII (insurance, tax_id)."""
    import base64
    return base64.b64decode(get_settings().ENCRYPTION_KEY)


class ProviderType(str, enum.Enum):
    """
    Vertical that a ProviderProfile represents. A user holds one
    ProviderProfile per type (composite unique on (user_id, provider_type)).

    E1.A only adds the column with default DETAILER — the relationship on
    User is still 1:1. E1.B flips that to 1:N once all call-sites have
    been migrated.
    """
    DETAILER = "detailer"
    MECHANIC = "mechanic"


class ProviderProfile(TimestampMixin, Base):
    __tablename__ = "provider_profiles"
    __table_args__ = (
        # E1.A: composite unique replaces the single-column unique on
        # user_id. Until E1.B all existing rows have provider_type=DETAILER
        # (backfilled by the migration), so each user still maps to ≤1 row
        # in practice.
        UniqueConstraint(
            "user_id", "provider_type",
            name="uq_provider_profiles_user_type",
        ),
        Index(
            "ix_provider_profiles_type_active",
            "provider_type", "is_active",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # E1.A: vertical that this profile represents. Stored as VARCHAR (no
    # PostgreSQL enum type) so adding a new vertical later is a code-only
    # change — see plan 01-profiles.md §2.2. The application layer treats
    # this as a `ProviderType` enum; the column itself stays string so
    # extending the enum doesn't require a migration. Use
    # `ProviderType(profile.provider_type)` to recover the typed value.
    provider_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ProviderType.DETAILER.value,
        server_default=ProviderType.DETAILER.value,
    )
    # E1.A: forward-compatible name for the master toggle. While
    # is_accepting_bookings is still the canonical column (E1.E renames it),
    # is_active mirrors it via the migration backfill so new code can read
    # either consistently. Dual-write is handled at the service layer in
    # E1.B; in E1.A the column simply starts as a copy.
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true",
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    years_of_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # E1.E: column dropped in m_017. `is_accepting_bookings` survives as a
    # Python @property (defined below) that forwards to is_active so the
    # legacy wire contract and existing callers don't have to move in
    # lockstep with the rename. Remove the property once the codebase has
    # fully migrated to is_active.
    service_radius_miles: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    working_hours: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
        default=lambda: {
            "monday":    {"start": "08:00", "end": "18:00", "enabled": True},
            "tuesday":   {"start": "08:00", "end": "18:00", "enabled": True},
            "wednesday": {"start": "08:00", "end": "18:00", "enabled": True},
            "thursday":  {"start": "08:00", "end": "18:00", "enabled": True},
            "friday":    {"start": "08:00", "end": "18:00", "enabled": True},
            "saturday":  {"start": "09:00", "end": "16:00", "enabled": True},
            "sunday":    {"start": None,     "end": None,    "enabled": False},
        },
    )
    timezone: Mapped[str] = mapped_column(
        String(60), nullable=False, default="America/Indiana/Indianapolis",
    )
    # E1.D: scalar service_category_id replaced by m2m `service_categories_rel`
    # (table provider_service_categories) so a profile can offer multiple
    # categories simultaneously. The migration backfills the existing scalar
    # value into the junction before dropping the column.
    average_rating: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    total_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    specialties_rel: Mapped[list[Specialty]] = relationship(
        "Specialty", secondary="provider_specialties",
        back_populates="providers", lazy="selectin",
    )

    @property
    def specialties(self) -> list[str]:
        return [s.slug for s in (self.specialties_rel or [])]

    # Location
    current_lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    current_lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    last_location_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Stripe Identity verification
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_submitted")
    legal_full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    address_line1: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(60), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stripe_verification_session_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True,
    )
    background_check_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    background_check_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # H3 geospatial index
    h3_index_r7: Mapped[str | None] = mapped_column(String(20), nullable=True)
    h3_index_r9: Mapped[str | None] = mapped_column(String(20), nullable=True)
    response_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0"), server_default="0",
    )

    # ── Profile Hub `provider` block (Phase 1) ──
    # Public-facing fields distinct from KYC legal data above. `display_name`
    # and `business_name` are what other users see; `legal_full_name` stays
    # internal to verification.
    display_name: Mapped[str | None]  = mapped_column(String(80), nullable=True)
    business_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tagline: Mapped[str | None]       = mapped_column(String(140), nullable=True)
    social_links: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cover_photo_s3_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # PII — encrypted at rest with the same ENCRYPTION_KEY as User.full_name.
    insurance_policy_number_encrypted: Mapped[str | None] = mapped_column(
        EncryptedType(String(120), _provider_encryption_key), nullable=True,
    )
    tax_id_encrypted: Mapped[str | None] = mapped_column(
        EncryptedType(String(60), _provider_encryption_key), nullable=True,
    )

    # Stripe Connect / payout target — Phase 5+.
    payout_method_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Stripe Connect onboarding state (Plan 20 §17 + audit H10).
    # See alembic m_019_provider_profiles_stripe_connect for the migration.
    #
    # Lifecycle:
    #   not_started → pending → completed (happy path)
    #             ╲→ pending → expired (no completion within 24h)
    #             ╲→ rejected (Stripe rejects KYC)
    #
    # `payouts_enabled` / `charges_enabled` are mirrored from Stripe's
    # account.updated webhook so the GET /me/connect-account/status
    # endpoint can answer without a Stripe round-trip per request.
    stripe_account_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, unique=True,
    )
    stripe_onboarding_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_started",
        server_default="not_started",
    )
    stripe_onboarding_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    stripe_payouts_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    stripe_charges_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )

    # ── Plan 24 Wave 1 — provider signup multi-step fields ──
    # See alembic m_024 + Plan 24 §3 (P-1 to P-3, P-7).

    # P-1: encrypted SSN last 4 — captured at signup step 2 for the
    # Checkr background check. Stored encrypted, NEVER returned via
    # any API; the value is consumed once by the bg-check adapter
    # and not needed thereafter (consider purging post-approval).
    ssn_last_4_encrypted: Mapped[str | None] = mapped_column(
        EncryptedType(String(8), _provider_encryption_key), nullable=True,
    )

    # P-2: market code — points at `cities.code`. Plain VARCHAR (no FK)
    # because we want soft-references that don't cascade on city
    # deletion, and the validation lives at the app layer (a city must
    # exist + be active when set).
    home_city_code: Mapped[str | None] = mapped_column(
        String(8), nullable=True, index=True,
    )

    # P-3: equipment metadata from signup step 4. Used by matching
    # (e.g. don't route a job to a detailer without ceramic experience)
    # and surfaced in the provider profile UI.
    water_tank_gallons: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    # JSONB list of service-slug strings the provider can perform
    # (e.g. ["soap", "vacuum", "polish", "ceramic"]). NOT the same as
    # `service_categories_rel` below — that's the high-level category
    # bucket; this is the granular skill list.
    services_offered: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
    )

    # P-7: signup lifecycle state machine (complementary to the existing
    # `verification_status` which only tracks Stripe Identity). The
    # state transitions:
    #
    #   draft → submitted → bg_check_pending → docs_review → approved
    #                                                      ╲→ rejected
    #
    # Defaults to "draft" so partial signups can be saved + resumed.
    application_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default="draft",
    )

    # Denormalized counters maintained by the m_020 trigger (Phase 9).
    total_services_completed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    earnings_lifetime_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0",
    )

    user: Mapped[User] = relationship("User", back_populates="provider_profiles")
    # E1.D: renamed from detailer_services. Service class is now ProviderService
    # (alias DetailerService preserved for back-compat in services_catalog).
    provider_services: Mapped[list[ProviderService]] = relationship(
        "ProviderService", back_populates="provider",
        lazy="selectin", cascade="all, delete-orphan",
    )
    # E1.D back-compat: any code still walking `pp.detailer_services` keeps
    # working. Remove once the rename has propagated through frontend +
    # documentation.
    @property
    def detailer_services(self) -> list[ProviderService]:
        return self.provider_services

    # E1.D: m2m service categories. A profile can cover multiple categories
    # (basic_wash + interior_detail + full_detail) simultaneously.
    service_categories_rel: Mapped[list["ServiceCategoryTable"]] = relationship(
        "ServiceCategoryTable",
        secondary="provider_service_categories",
        lazy="selectin",
    )

    # E1.E back-compat: the column dropped in m_017 lives on as a property
    # that forwards reads and writes to `is_active`. Existing services
    # (Phase 5 set_accepting_bookings, schemas exposing the legacy field
    # name in JSON, etc.) continue to compile and behave the same; the
    # mobile/web/marketing JSON contract still surfaces
    # `is_accepting_bookings: bool` because Pydantic serializes whatever
    # attribute matches the field name. Remove this property once every
    # caller and every wire contract has migrated to is_active.
    @property
    def is_accepting_bookings(self) -> bool:
        return self.is_active

    @is_accepting_bookings.setter
    def is_accepting_bookings(self, value: bool) -> None:
        self.is_active = bool(value)

    def __repr__(self) -> str:
        return f"<ProviderProfile user_id={self.user_id}>"


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from domains.users.models import User
    from domains.services_catalog.models import (
        Specialty, ProviderService, ServiceCategoryTable,
    )

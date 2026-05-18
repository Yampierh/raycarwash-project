from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils import EncryptedType

from infrastructure.db.base import Base, TimestampMixin, _get_encryption_key


class OnboardingStatus(str, enum.Enum):
    PENDING_PROFILE      = "pending_profile"
    PENDING_VERIFICATION = "pending_verification"
    COMPLETED            = "completed"


class ClientProfile(TimestampMixin, Base):
    __tablename__ = "client_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    # Deprecated since Phase 4 — migrating to UserAddress. Kept for backwards
    # compat during the transition window.
    service_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    marketing_preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Profile Hub `preferences` block (Phase 1) ──
    default_vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True,
    )
    # FK to user_addresses lands in Phase 4 (m_010); column is nullable UUID
    # without constraint for now.
    default_address_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )

    # ── Stats block — denormalized counters maintained by triggers (Phase 9
    # m_020). Phase 1 reads them as 0 for legacy rows. ──
    total_appointments_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    total_spent_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0",
    )
    marketing_email_opt_in: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    frequency_preference: Mapped[str | None] = mapped_column(String(20), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="client_profile")

    def __repr__(self) -> str:
        return f"<ClientProfile user_id={self.user_id}>"


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), nullable=False, index=True)

    # PII encrypted at rest with ENCRYPTION_KEY
    full_name: Mapped[str] = mapped_column(
        EncryptedType(String(120), _get_encryption_key), nullable=True,
    )
    phone_number: Mapped[str | None] = mapped_column(
        EncryptedType(String(20), _get_encryption_key), nullable=True,
    )

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    onboarding_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=OnboardingStatus.PENDING_PROFILE,
        server_default=OnboardingStatus.PENDING_PROFILE,
    )

    @property
    def onboarding_completed(self) -> bool:
        return self.onboarding_status == OnboardingStatus.COMPLETED

    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    phone_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    last_step_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Last successful auth event timestamp (UTC). DB fallback for Redis step-up cache.",
    )

    # ── Profile system (Phase 1, ADR-002b) ──
    # avatar_s3_key / cover_s3_key live behind FileStorageAdapter — URLs are
    # signed at read time, not stored. Phase 2 wires the upload endpoints.
    avatar_s3_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cover_s3_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pronouns: Mapped[str | None] = mapped_column(String(20), nullable=True)
    preferred_language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="en", server_default="en",
    )
    preferred_timezone: Mapped[str] = mapped_column(
        String(64), nullable=False,
        default="America/Indiana/Indianapolis",
        server_default="America/Indiana/Indianapolis",
    )
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    # active_role is the role currently selected by a dual-role user. Phase 6
    # adds the PATCH /users/me/active-role endpoint that rotates refresh and
    # re-issues access with this claim. None = legacy single-role users.
    active_role: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Integration plan E0 (00-user.md): coarse location hint captured at
    # signup. NOT a substitute for UserAddress — purely a quick-onboarding
    # signal for matching radius defaults. Indexed because future matching
    # heuristics may filter providers by user zip cohort.
    zip_code: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)

    # Relationships — all cross-domain references use string names
    # user_roles and profiles use selectin (required on every authenticated request).
    # All other relationships use lazy="select" so they are only loaded when accessed.
    user_roles: Mapped[list[UserRoleAssociation]] = relationship(
        "UserRoleAssociation",
        foreign_keys="UserRoleAssociation.user_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    @property
    def roles(self) -> list[str]:
        return [ur.role.name for ur in self.user_roles]

    client_profile: Mapped[ClientProfile | None] = relationship(
        "ClientProfile", back_populates="user",
        uselist=False, lazy="selectin", cascade="all, delete-orphan",
    )
    # E1.B (01-profiles.md): 1:N — a user can hold a DETAILER profile and a
    # MECHANIC profile side by side. Composite unique (user_id, provider_type)
    # caps the list at one per vertical. Use `provider_profile_for(type)` to
    # fetch a specific vertical; the legacy `@property provider_profile`
    # below returns the DETAILER row for back-compat.
    provider_profiles: Mapped[list[ProviderProfile]] = relationship(
        "ProviderProfile", back_populates="user",
        lazy="selectin", cascade="all, delete-orphan",
    )
    vehicles: Mapped[list[Vehicle]] = relationship(
        "Vehicle", back_populates="owner", lazy="select",
    )
    client_appointments: Mapped[list[Appointment]] = relationship(
        "Appointment", foreign_keys="Appointment.client_id",
        back_populates="client", lazy="select",
    )
    detailer_appointments: Mapped[list[Appointment]] = relationship(
        "Appointment", foreign_keys="Appointment.detailer_id",
        back_populates="detailer", lazy="select",
    )
    reviews_given: Mapped[list[Review]] = relationship(
        "Review", foreign_keys="Review.reviewer_id",
        back_populates="reviewer", lazy="select",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog", back_populates="actor", lazy="select",
    )
    webauthn_credentials: Mapped[list[WebAuthnCredential]] = relationship(
        "WebAuthnCredential", back_populates="user",
        lazy="select", cascade="all, delete-orphan",
    )
    auth_providers: Mapped[list[AuthProvider]] = relationship(
        "AuthProvider", back_populates="user",
        lazy="select", cascade="all, delete-orphan",
    )
    login_history: Mapped[list["UserLoginHistory"]] = relationship(
        "UserLoginHistory", back_populates="user",
        lazy="select", cascade="all, delete-orphan",
    )
    # Phase 3 — Profile system contact verification + 2FA.
    pending_contact_changes: Mapped[list["PendingContactChange"]] = relationship(
        "PendingContactChange", back_populates="user",
        lazy="select", cascade="all, delete-orphan",
    )
    totp_credential: Mapped["TotpCredential | None"] = relationship(
        "TotpCredential", back_populates="user",
        uselist=False, lazy="select", cascade="all, delete-orphan",
    )
    # Phase 4 — addresses / payment methods / favorites.
    addresses: Mapped[list["UserAddress"]] = relationship(
        "UserAddress", back_populates="user",
        lazy="select", cascade="all, delete-orphan",
    )
    payment_methods: Mapped[list["PaymentMethod"]] = relationship(
        "PaymentMethod", back_populates="user",
        lazy="select", cascade="all, delete-orphan",
    )
    favorites: Mapped[list["ClientFavorite"]] = relationship(
        "ClientFavorite",
        foreign_keys="ClientFavorite.user_id",
        back_populates="user",
        lazy="select", cascade="all, delete-orphan",
    )
    # Phase 5 — provider documents / portfolio / achievements.
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="user",
        lazy="select", cascade="all, delete-orphan",
    )
    portfolio_photos: Mapped[list["ProviderPortfolioPhoto"]] = relationship(
        "ProviderPortfolioPhoto", back_populates="provider",
        lazy="select", cascade="all, delete-orphan",
    )
    achievements: Mapped[list["ProviderAchievement"]] = relationship(
        "ProviderAchievement", back_populates="provider",
        lazy="select", cascade="all, delete-orphan",
    )

    def has_permission(self, permission_name: str) -> bool:
        for user_role in self.user_roles:
            for perm in user_role.role.permissions:
                if perm.name == permission_name:
                    return True
        return False

    def get_all_permissions(self) -> set[str]:
        permissions: set[str] = set()
        for user_role in self.user_roles:
            for perm in user_role.role.permissions:
                permissions.add(perm.name)
        return permissions

    def has_role(self, role_name: str) -> bool:
        return any(ur.role.name == role_name for ur in self.user_roles)

    def is_admin(self) -> bool:
        return self.has_role("admin")

    def is_client(self) -> bool:
        return self.has_role("client")

    def is_provider(self) -> bool:
        # E0/E1: a "provider" is any user that earns money on the platform.
        # Today that is detailer; integration plan 01-profiles introduces
        # mechanic as a second provider_type. is_detailer() / is_mechanic()
        # remain available for vertical-specific gates.
        return self.has_role("detailer") or self.has_role("mechanic")

    def provider_profile_for(self, provider_type) -> ProviderProfile | None:
        """
        Return the (active, non-deleted) ProviderProfile of `provider_type`
        if it exists, else None. Accepts a `ProviderType` enum or the raw
        string value so callers don't have to import the enum.
        """
        # Local import to avoid the cross-domain runtime cycle.
        from domains.providers.models import ProviderType

        wanted = provider_type.value if isinstance(provider_type, ProviderType) else str(provider_type)
        for pp in (self.provider_profiles or []):
            if pp.is_deleted:
                continue
            if pp.provider_type == wanted:
                return pp
        return None

    @property
    def provider_profile(self) -> ProviderProfile | None:
        """
        Back-compat shim — returns the DETAILER ProviderProfile if any.
        Removed once every call-site has migrated to
        `provider_profile_for(ProviderType.X)` or iterates
        `provider_profiles` directly.
        """
        from domains.providers.models import ProviderType
        return self.provider_profile_for(ProviderType.DETAILER)

    def is_detailer(self) -> bool:
        return self.has_role("detailer")

    def is_mechanic(self) -> bool:
        return self.has_role("mechanic")

    @property
    def primary_role(self) -> str | None:
        if self.user_roles:
            return self.user_roles[0].role.name
        return None

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


# TYPE_CHECKING-only cross-domain aliases — SQLAlchemy resolves by string at runtime
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from domains.auth.models import (
        UserRoleAssociation, WebAuthnCredential, AuthProvider, UserLoginHistory,
    )
    from domains.auth.totp_credential import TotpCredential
    from domains.providers.models import ProviderProfile
    from domains.users.pending_contact_change import PendingContactChange
    from domains.users.user_address import UserAddress
    from domains.users.payment_method import PaymentMethod
    from domains.users.client_favorite import ClientFavorite
    from domains.users.document import Document
    from domains.providers.portfolio_photo import ProviderPortfolioPhoto
    from domains.providers.achievement import ProviderAchievement
    from domains.vehicles.models import Vehicle
    from domains.appointments.models import Appointment
    from domains.reviews.models import Review
    from domains.audit.models import AuditLog

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
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
    service_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    marketing_preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

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

    # Relationships — all cross-domain references use string names
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
    provider_profile: Mapped[ProviderProfile | None] = relationship(
        "ProviderProfile", back_populates="user",
        uselist=False, lazy="selectin", cascade="all, delete-orphan",
    )
    vehicles: Mapped[list[Vehicle]] = relationship(
        "Vehicle", back_populates="owner", lazy="selectin",
    )
    client_appointments: Mapped[list[Appointment]] = relationship(
        "Appointment", foreign_keys="Appointment.client_id",
        back_populates="client", lazy="selectin",
    )
    detailer_appointments: Mapped[list[Appointment]] = relationship(
        "Appointment", foreign_keys="Appointment.detailer_id",
        back_populates="detailer", lazy="selectin",
    )
    reviews_given: Mapped[list[Review]] = relationship(
        "Review", foreign_keys="Review.reviewer_id",
        back_populates="reviewer", lazy="selectin",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog", back_populates="actor", lazy="selectin",
    )
    webauthn_credentials: Mapped[list[WebAuthnCredential]] = relationship(
        "WebAuthnCredential", back_populates="user",
        lazy="selectin", cascade="all, delete-orphan",
    )
    auth_providers: Mapped[list[AuthProvider]] = relationship(
        "AuthProvider", back_populates="user",
        lazy="selectin", cascade="all, delete-orphan",
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
        return self.has_role("detailer")

    def is_detailer(self) -> bool:
        return self.is_provider()

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
        UserRoleAssociation, WebAuthnCredential, AuthProvider,
    )
    from domains.providers.models import ProviderProfile
    from domains.vehicles.models import Vehicle
    from domains.appointments.models import Appointment
    from domains.reviews.models import Review
    from domains.audit.models import AuditLog

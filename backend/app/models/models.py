# app/models/models.py

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text as sa_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy_utils import EncryptedType

from app.core.config import get_settings


# ------------------------------------------------------------------ #
#  Settings for PII encryption                                       #
# ------------------------------------------------------------------ #
# SECURITY FIX (2026-04-24): Changed from _get_secret_key() to _get_encryption_key().
# Before: Used JWT_SECRET_KEY (single key) for both signing and encryption.
# After: Uses dedicated ENCRYPTION_KEY for PII via EncryptedType.
#        JWT_SECRET_KEY is used ONLY for JWT signing in auth.py.

def _get_encryption_key() -> bytes:
    # Returns the dedicated ENCRYPTION_KEY (32-byte key for Fernet)
    # SEPARATE from JWT_SECRET_KEY to prevent PII exposure on JWT compromise
    key = get_settings().ENCRYPTION_KEY
    # Ensure it's valid base64 (32 bytes when decoded)
    import base64
    return base64.b64decode(key)


# ------------------------------------------------------------------ #
#  Enumerations                                                       #
# ------------------------------------------------------------------ #

class OnboardingStatus(str, enum.Enum):
    """
    State machine for the user registration flow.

    PENDING_PROFILE     — just registered, full_name / role not yet set.
    PENDING_VERIFICATION — provider submitted documents, waiting for approval.
    COMPLETED           — all required steps done; full API access granted.

    Stored as VARCHAR(30) so new states require no DB schema migration.
    The old onboarding_completed boolean is now a computed property on User.
    """
    PENDING_PROFILE      = "pending_profile"
    PENDING_VERIFICATION = "pending_verification"
    COMPLETED            = "completed"


class VehicleSize(str, enum.Enum):
    SMALL  = "small"
    MEDIUM = "medium"
    LARGE  = "large"
    XL     = "xl"


class AppointmentStatus(str, enum.Enum):
    PENDING              = "pending"
    CONFIRMED            = "confirmed"
    ARRIVED              = "arrived"           # Detailer has reached the client location
    IN_PROGRESS          = "in_progress"
    COMPLETED            = "completed"
    CANCELLED_BY_CLIENT  = "cancelled_by_client"
    CANCELLED_BY_DETAILER= "cancelled_by_detailer"
    NO_SHOW              = "no_show"
    SEARCHING            = "searching"          # v2: looking for a detailer
    NO_DETAILER_FOUND    = "no_detailer_found"  # v2: all candidates timed out


class AssignmentStatus(str, enum.Enum):
    OFFERED  = "offered"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    TIMEOUT  = "timeout"


# Terminal statuses: no longer occupy a detailer's schedule slot.
TERMINAL_STATUSES: frozenset[AppointmentStatus] = frozenset({
    AppointmentStatus.CANCELLED_BY_CLIENT,
    AppointmentStatus.CANCELLED_BY_DETAILER,
    AppointmentStatus.NO_SHOW,
    AppointmentStatus.NO_DETAILER_FOUND,
})

# ---- State machine: allowed forward transitions per role ----
# Structure:  {current_status: {new_status: {role_names_that_can_trigger}}}
VALID_TRANSITIONS: dict[
    AppointmentStatus,
    dict[AppointmentStatus, frozenset[str]]
] = {
    AppointmentStatus.PENDING: {
        AppointmentStatus.CONFIRMED:
            frozenset({"detailer", "admin"}),
        AppointmentStatus.CANCELLED_BY_CLIENT:
            frozenset({"client",   "admin"}),
        AppointmentStatus.CANCELLED_BY_DETAILER:
            frozenset({"detailer", "admin"}),
    },
    AppointmentStatus.CONFIRMED: {
        AppointmentStatus.ARRIVED:
            frozenset({"detailer", "admin"}),
        AppointmentStatus.IN_PROGRESS:
            frozenset({"detailer", "admin"}),
        AppointmentStatus.CANCELLED_BY_CLIENT:
            frozenset({"client",   "admin"}),
        AppointmentStatus.CANCELLED_BY_DETAILER:
            frozenset({"detailer", "admin"}),
    },
    AppointmentStatus.ARRIVED: {
        AppointmentStatus.IN_PROGRESS:
            frozenset({"detailer", "admin"}),
        AppointmentStatus.CANCELLED_BY_CLIENT:
            frozenset({"client",   "admin"}),
        AppointmentStatus.CANCELLED_BY_DETAILER:
            frozenset({"detailer", "admin"}),
    },
    AppointmentStatus.IN_PROGRESS: {
        AppointmentStatus.COMPLETED:
            frozenset({"detailer", "admin"}),
        AppointmentStatus.NO_SHOW:
            frozenset({"detailer", "admin"}),
    },
    # Terminal states — no outbound transitions
    AppointmentStatus.COMPLETED:              {},
    AppointmentStatus.CANCELLED_BY_CLIENT:    {},
    AppointmentStatus.CANCELLED_BY_DETAILER:  {},
    AppointmentStatus.NO_SHOW:                {},
}


class ServiceCategory(str, enum.Enum):
    BASIC_WASH      = "basic_wash"
    INTERIOR_DETAIL = "interior_detail"
    FULL_DETAIL     = "full_detail"
    CERAMIC_COATING = "ceramic_coating"
    PAINT_CORRECTION= "paint_correction"


class AuditAction(str, enum.Enum):
    # Appointment lifecycle
    APPOINTMENT_CREATED  = "appointment_created"
    APPOINTMENT_STATUS_CHANGED = "appointment_status_changed"
    APPOINTMENT_DELETED  = "appointment_deleted"
    # Payment events
    PAYMENT_INTENT_CREATED = "payment_intent_created"
    PAYMENT_CAPTURED       = "payment_captured"
    PAYMENT_REFUNDED       = "payment_refunded"
    # Auth events
    USER_REGISTERED          = "user_registered"
    USER_LOGIN               = "user_login"
    USER_SOCIAL_LOGIN        = "user_social_login"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    # Review events
    REVIEW_CREATED  = "review_created"
    # Detailer profile events (Sprint 4)
    DETAILER_PROFILE_CREATED = "provider_profile_created"
    DETAILER_PROFILE_UPDATED = "provider_profile_updated"


# ------------------------------------------------------------------ #
#  Base                                                               #
# ------------------------------------------------------------------ #

class Base(AsyncAttrs, DeclarativeBase):
    """AsyncAttrs enables awaitable attribute access — required for async ORM."""
    pass


# ------------------------------------------------------------------ #
#  Mixin: timestamps + soft-delete                                    #
# ------------------------------------------------------------------ #

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


# ------------------------------------------------------------------ #
#  Model: Permission  (RBAC)                                         #
# ------------------------------------------------------------------ #

class Permission(Base):
    """
    Granular permission entity for RBAC.
    
    Each permission defines an action on a resource.
    Examples:
        - "read:appointments"
        - "write:users"
        - "delete:vehicles"
        - "manage:payments"
    """

    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("name", name="uq_permission_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True,
        comment="Format: action:resource (e.g., 'read:appointments')",
    )
    resource: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="The resource being protected (e.g., 'appointments', 'users')",
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="The action allowed (e.g., 'read', 'write', 'delete', 'manage')",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Human-readable description of this permission",
    )

    roles: Mapped[list[Role]] = relationship(
        "Role", 
        secondary="role_permissions", 
        back_populates="permissions",
        overlaps="role_permissions"
    )
    role_permissions: Mapped[list[RolePermission]] = relationship(
        "RolePermission", back_populates="permission", lazy="selectin",
        overlaps="roles"
    )

    def __repr__(self) -> str:
        return f"<Permission {self.name}>"


# ------------------------------------------------------------------ #
#  Association: Role <-> Permission                                  #
# ------------------------------------------------------------------ #

class RolePermission(Base):
    """Many-to-many association between Role and Permission."""

    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False, primary_key=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False, primary_key=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    role: Mapped[Role] = relationship("Role", back_populates="role_permissions")
    permission: Mapped[Permission] = relationship("Permission", back_populates="role_permissions")


# ------------------------------------------------------------------ #
#  Model: Role  (RBAC)                                               #
# ------------------------------------------------------------------ #

class Role(TimestampMixin, Base):
    """
    Dynamic role entity for RBAC.
    
    Replaces the static UserRole Enum with a flexible, many-to-many
    relationship to both Users and Permissions.
    
    System roles (is_system=True) cannot be deleted:
        - admin: Full system access
        - detailer: Can manage appointments, services, reviews
        - client: Can book appointments, manage own vehicles
    """

    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("name", name="uq_role_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True,
        comment="Unique role identifier (e.g., 'admin', 'detailer', 'client')",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Human-readable description of this role",
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="System roles cannot be deleted via API",
    )

    permissions: Mapped[list[Permission]] = relationship(
        "Permission", secondary="role_permissions", back_populates="roles",
        overlaps="role_permissions"
    )
    role_permissions: Mapped[list[RolePermission]] = relationship(
        "RolePermission", back_populates="role", lazy="selectin",
        overlaps="permissions"
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


# ------------------------------------------------------------------ #
#  Association: User <-> Role                                        #
# ------------------------------------------------------------------ #

class UserRoleAssociation(Base):
    """
    Many-to-many association between User and Role.
    
    Tracks role assignments with timestamp for audit purposes.
    """

    __tablename__ = "user_roles"
    __table_args__ = (
        # Speeds up "all users assigned role Y" — the PK (user_id, role_id) only
        # helps leading-column (user_id) lookups; role_id-only needs its own index.
        Index("ix_user_roles_role_id", "role_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, primary_key=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False, primary_key=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who assigned this role (NULL if system-assigned)",
    )

    user: Mapped[User] = relationship(
        "User",
        foreign_keys="UserRoleAssociation.user_id",
    )
    role: Mapped[Role] = relationship("Role", lazy="selectin")


# ------------------------------------------------------------------ #
#  Model: ClientProfile                                              #
# ------------------------------------------------------------------ #

class ClientProfile(TimestampMixin, Base):
    """
    One-to-one extension of User for CLIENT-specific configuration.
    
    WHY a separate table instead of more columns on User?
    - Client-specific fields (service_address, marketing_preferences) are
      irrelevant for DETAILER/ADMIN users.
    - Keeps the User table lean and focused on identity/auth.
    - Supports future expansion of client-specific features without
      schema migrations.
    """

    __tablename__ = "client_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )

    # ---- Service address ----
    service_address: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Default service address for appointments",
    )

    # ---- Marketing preferences ----
    marketing_preferences: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment=(
            "User's marketing opt-ins. Structure: "
            '{"email_sms": true, "push_notifications": false, "newsletter": true}'
        ),
    )

    # Payment methods are queried live from Stripe, never cached locally:
    #   stripe.PaymentMethod.list(customer=user.stripe_customer_id, type="card")
    # Storing them here created stale-data risk — cards expire or are removed
    # in Stripe without the DB knowing. Column removed in migration f6a7b8c9d0e1.

    user: Mapped[User] = relationship("User", back_populates="client_profile")

    def __repr__(self) -> str:
        return f"<ClientProfile user_id={self.user_id}>"


# ------------------------------------------------------------------ #
#  Model: User                                                        #
# ------------------------------------------------------------------ #

class User(TimestampMixin, Base):
    """
    Central identity table. One row per person regardless of role.

    Identity: email, full_name (encrypted), phone_number (encrypted), password_hash.
    Roles: many-to-many via user_roles. A user can hold multiple roles (client + detailer).
    Profiles: ClientProfile and ProviderProfile extend the user for role-specific data.
    onboarding_status: state machine (pending_profile | pending_verification | completed).
                       onboarding_completed is a read-only property (= status == COMPLETED).
    PII (full_name, phone_number) is encrypted at rest via SECRET_KEY.
    Social login identities live in AuthProvider rows linked to this user.
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(254), nullable=False, index=True,
        comment="Stored lowercase. RFC 5321 max length. Unique.",
    )

    # ---- PII: Encrypted at rest ----
    # NOTE: Uses ENCRYPTION_KEY (separate from JWT_SECRET_KEY).
    # If you rotate JWT_SECRET_KEY, PII remains secure.
    full_name: Mapped[str] = mapped_column(
        EncryptedType(String(120), _get_encryption_key),
        nullable=True,
        comment="Full name, encrypted at rest using ENCRYPTION_KEY",
    )
    phone_number: Mapped[str | None] = mapped_column(
        EncryptedType(String(20), _get_encryption_key),
        nullable=True,
        comment="Phone number, encrypted at rest using ENCRYPTION_KEY",
    )

    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="bcrypt digest. NEVER expose.",
    )
    # TODO: HIGH - Failed login tracking for brute force protection.
    # BUG: No counter for failed attempts - can't detect or prevent brute force.
    # Add to User model after password_hash:
    # failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    # locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # On failed login: increment counter, set locked_until if >= 5
    # On successful login: reset counter
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # TODO: MEDIUM - Email verification not enforced.
    # BUG: is_verified exists but not required for login - users can login unverified.
    # Risk: Spam accounts, fake profiles.
    # FIX: Require email verification before allowing login or actions.
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ---- Onboarding state machine ----
    # Replaces the old onboarding_completed: bool field (migration b8c9d0e1f2a3).
    # Stored as VARCHAR(30) — new statuses require no DB migration.
    onboarding_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=OnboardingStatus.PENDING_PROFILE,
        server_default=OnboardingStatus.PENDING_PROFILE,
        comment=(
            "Onboarding state machine. "
            "Values: pending_profile | pending_verification | completed. "
            "See OnboardingStatus enum."
        ),
    )

    @property
    def onboarding_completed(self) -> bool:
        """Backward-compat alias — True when onboarding_status == 'completed'."""
        return self.onboarding_status == OnboardingStatus.COMPLETED

    # --- Token version for instant revocation ---
    # FEATURE ADDED (2026-04-24): token_version field for instant session invalidation.
    # Before: Role changes only take effect after JWT expires (30 min max).
    # After: Increment token_version to immediately invalidate all sessions.
    # Usage: UPDATE users SET token_version = token_version + 1 WHERE id = X
    #        Then validate in JWT or endpoint-level checks.
    # NOTE: Currently stored in DB but NOT yet included in JWT payload - FIX needed in auth.py!
    token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
        comment="Increment to invalidate all active sessions.",
    )

    # --- Phone hash for efficient lookup ---
    # FEATURE ADDED (2026-04-24): phone_hash for O(1) phone lookup.
    # Before: Phone lookup required decrypting every row (O(n) full table scan).
    # After: HMAC-SHA256 hash enables index-based lookup.
    #        Hash: HMAC-SHA256(normalize(phone_e164), PHONE_LOOKUP_KEY)
    #        Separate key prevents rainbow table attacks.
    # NOTE: Field added but UserRepository.get_by_phone() needs update!
    phone_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True,
        comment="HMAC-SHA256 of phone_number for lookup.",
    )

    # ---- Stripe (Sprint 3) ----
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True,
        comment="Stripe cus_xxx. Set on first payment intent creation.",
    )

    # NOTE: roles relationship removed due to FK ambiguity in user_roles table
    # (has user_id AND assigned_by both pointing to users)
    # Use UserRoleAssociation queries to access user roles
    user_roles: Mapped[list[UserRoleAssociation]] = relationship(
        "UserRoleAssociation",
        foreign_keys="UserRoleAssociation.user_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    @property
    def roles(self) -> list[str]:
        """Get role names from user_roles for serialization."""
        return [ur.role.name for ur in self.user_roles]
    client_profile: Mapped[ClientProfile | None] = relationship(
        "ClientProfile",
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    provider_profile: Mapped[ProviderProfile | None] = relationship(
        "ProviderProfile",
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    vehicles: Mapped[list[Vehicle]] = relationship(
        "Vehicle", back_populates="owner", lazy="selectin"
    )
    client_appointments: Mapped[list[Appointment]] = relationship(
        "Appointment",
        foreign_keys="Appointment.client_id",
        back_populates="client",
        lazy="selectin",
    )
    detailer_appointments: Mapped[list[Appointment]] = relationship(
        "Appointment",
        foreign_keys="Appointment.detailer_id",
        back_populates="detailer",
        lazy="selectin",
    )
    reviews_given: Mapped[list[Review]] = relationship(
        "Review",foreign_keys="Review.reviewer_id", back_populates="reviewer", lazy="selectin"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog", back_populates="actor", lazy="selectin"
    )
    webauthn_credentials: Mapped[list["WebAuthnCredential"]] = relationship(
        "WebAuthnCredential",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    auth_providers: Mapped[list["AuthProvider"]] = relationship(
        "AuthProvider",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def has_permission(self, permission_name: str) -> bool:
        """
        Check if the user has a specific permission through any of their roles.
        
        Args:
            permission_name: The permission to check (e.g., 'read:appointments')
            
        Returns:
            True if the user has the permission via any role, False otherwise.
        """
        for user_role in self.user_roles:
            role = user_role.role
            for perm in role.permissions:
                if perm.name == permission_name:
                    return True
        return False

    def get_all_permissions(self) -> set[str]:
        """
        Get all permissions granted to the user through all their roles.
        
        Returns:
            Set of permission names (e.g., {'read:appointments', 'write:users'})
        """
        permissions: set[str] = set()
        for user_role in self.user_roles:
            role = user_role.role
            for perm in role.permissions:
                permissions.add(perm.name)
        return permissions

    def has_role(self, role_name: str) -> bool:
        """
        Check if the user has a specific role by name.
        
        Args:
            role_name: The role name to check (e.g., 'admin', 'detailer', 'client')
            
        Returns:
            True if the user has the role, False otherwise.
        """
        return any(user_role.role.name == role_name for user_role in self.user_roles)

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.has_role("admin")

    def is_client(self) -> bool:
        """Check if user has client role."""
        return self.has_role("client")

    def is_provider(self) -> bool:
        """Check if user is a service provider (role='detailer')."""
        return self.has_role("detailer")

    def is_detailer(self) -> bool:
        """Backward-compat alias for is_provider()."""
        return self.is_provider()

    @property
    def primary_role(self) -> str | None:
        """Returns the first assigned role name, or None if no roles are set."""
        if self.user_roles:
            return self.user_roles[0].role.name
        return None

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


# ------------------------------------------------------------------ #
#  Model: ServiceCategory                                             #
# ------------------------------------------------------------------ #
# FIX (2026-04-24): Renamed from ServiceCategory to ServiceCategoryTable
# to avoid conflict with ServiceCategory enum used by Service.category.
# Before: Both enum and table model named ServiceCategory
# After: Table model renamed to ServiceCategoryTable

class ServiceCategoryTable(TimestampMixin, Base):
    """
    Service categories (e.g., car_detailing, mobile_mechanic, cleaning).
    Allows the platform to support multiple service types with a single
    provider model.

    FIX: Enables the ProviderProfile → ProviderProfile rename without
    fragmenting the codebase. Future service types get their own rows here.
    """

    __tablename__ = "service_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True,
        comment="URL-safe identifier: e.g. 'car_detailing'",
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Display name: e.g. 'Car Detailing'",
    )

    def __repr__(self) -> str:
        return f"<ServiceCategory {self.slug}>"


# ------------------------------------------------------------------ #
#  Model: ProviderProfile                                             #
# ------------------------------------------------------------------ #

class ProviderProfile(TimestampMixin, Base):
    """
    One-to-one extension of User for DETAILER-specific configuration.

    RENAME: This model is being renamed to ProviderProfile in a phased approach.
    The ProviderProfile name is being phased out in favor of a more
    generic "Provider" terminology that can accommodate future service types.

    WHY a separate table instead of more columns on User?
    - Detailer config (working hours, bio, is_accepting_bookings) is irrelevant
      for CLIENT users — it would clutter queries and the schema.
    - The 1:1 join is done once at login and cached; it's not in the hot path.
    - It allows CLIENTs to gain DETAILER status by inserting a profile row
      without altering the User row.

    working_hours stores a JSONB map of the form:
        {
          "monday":    {"start": "08:00", "end": "18:00", "enabled": true},
          "tuesday":   {"start": "08:00", "end": "18:00", "enabled": true},
          ...
          "sunday":    {"start": null,    "end": null,    "enabled": false}
        }

    JSONB is used over 14 separate time columns to keep the schema flat
    while supporting arbitrary future changes (holiday schedules, etc.).
    """

    __tablename__ = "provider_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    years_of_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_accepting_bookings: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    service_radius_miles: Mapped[int] = mapped_column(
        Integer, nullable=False, default=25,
        comment="Max distance the detailer will travel. Default 25 miles (Fort Wayne metro).",
    )
    # JSONB: {"monday": {"start": "08:00", "end": "18:00", "enabled": true}, ...}
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
    # ---- Timezone (Sprint 4) ----
    timezone: Mapped[str] = mapped_column(
        String(60), nullable=False, default="America/Indiana/Indianapolis",
        comment=(
            "IANA timezone name for this detailer's local time. "
            "Used to display availability slots in the correct local time. "
            "Examples: 'America/New_York', 'America/Chicago', 'America/Los_Angeles'."
        ),
    )

    # ---- Service category (Sprint 6 refactor) ----
    # FIX: Added to support ProviderProfile → ProviderProfile rename.
    # Allows multiple service types with a single model.
    service_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK to ServiceCategory. Defaults to 'car_detailing'.",
    )

    average_rating: Mapped[float | None] = mapped_column(
        Numeric(3, 2), nullable=True,
        comment="Denormalised average — updated on every new review.",
    )
    total_reviews: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    # ---- Specialties — junction table (migrated from JSONB in e1f2a3b4c5d6) ----
    specialties_rel: Mapped[list["Specialty"]] = relationship(
        "Specialty",
        secondary="provider_specialties",
        back_populates="providers",
        lazy="selectin",
    )

    @property
    def specialties(self) -> list[str]:
        """Return specialty slugs as a list of strings (backward-compat read path)."""
        return [s.slug for s in (self.specialties_rel or [])]

    # ---- Real-time location (detailers only) ----
    current_lat: Mapped[float | None] = mapped_column(
        Numeric(9, 6), nullable=True,
        comment="Last known latitude. Updated on detailer's location pings.",
    )
    current_lng: Mapped[float | None] = mapped_column(
        Numeric(9, 6), nullable=True,
        comment="Last known longitude.",
    )
    last_location_update: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="UTC timestamp of last location ping.",
    )

    # ---- Identity Verification (Stripe Identity) ----
    # Lifecycle: not_submitted → pending → approved | rejected
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_submitted",
        comment="not_submitted | pending | approved | rejected",
    )
    legal_full_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="Full legal name as it appears on government-issued ID.",
    )
    date_of_birth: Mapped[date | None] = mapped_column(
        Date, nullable=True,
        comment="Date of birth for background check cross-reference.",
    )
    address_line1: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(60), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stripe_verification_session_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True,
        comment="Stripe Identity VerificationSession ID (vs_xxx).",
    )
    background_check_consent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    background_check_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    verification_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    verification_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ---- H3 Geospatial index (v2) ----
    h3_index_r7: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="H3 cell at resolution 7 for proximity search.",
    )
    h3_index_r9: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="H3 cell at resolution 9 for precise storage.",
    )
    response_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0"),
        server_default="0",
        comment="Fraction of offers accepted. Updated by assignment engine.",
    )

    user: Mapped[User] = relationship("User", back_populates="provider_profile")
    detailer_services: Mapped[list[DetailerService]] = relationship(
        "DetailerService", back_populates="detailer", lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ProviderProfile user_id={self.user_id}>"


# ------------------------------------------------------------------ #
#  Model: Vehicle                                                     #
# ------------------------------------------------------------------ #

class Vehicle(TimestampMixin, Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        # La placa sigue siendo única por dueño para evitar duplicados
        UniqueConstraint("owner_id", "license_plate", name="uq_vehicle_owner_plate"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
    # --- Datos Técnicos (NHTSA / Manual) ---
    vin: Mapped[str | None] = mapped_column(String(17), index=True, nullable=True)
    make: Mapped[str] = mapped_column(String(60), nullable=False)
    model: Mapped[str] = mapped_column(String(60), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    series: Mapped[str | None] = mapped_column(String(60), nullable=True) # Ej: GT-Line
    
    # --- Datos de Identificación Visual ---
    color: Mapped[str] = mapped_column(String(40), nullable=False) # Ahora obligatorio
    license_plate: Mapped[str] = mapped_column(String(20), nullable=False) # Ahora obligatorio
    body_class: Mapped[str | None] = mapped_column(String(60), nullable=True)
    
    # size is NOT stored on the Vehicle row.
    # It is derived at runtime: map_body_to_size(vehicle.body_class)
    # Removing this column eliminates size/body_class drift after edits.
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relaciones
    owner: Mapped["User"] = relationship("User", back_populates="vehicles")
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="vehicle", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Vehicle {self.year} {self.make} {self.model} ({self.license_plate})>"


# ------------------------------------------------------------------ #
#  Model: DetailerService  (join: detailer ↔ service catalog)        #
# ------------------------------------------------------------------ #

class DetailerService(TimestampMixin, Base):
    """
    Detailer-specific service configuration.

    Each detailer can toggle individual platform services on/off and
    optionally override the base price with a custom_price_cents.
    If custom_price_cents is NULL, the platform base_price_cents is used.
    """

    __tablename__ = "detailer_services"
    __table_args__ = (
        UniqueConstraint("detailer_id", "service_id", name="uq_detailer_service"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    detailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    custom_price_cents: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None,
        comment="Override base price. NULL means use service.base_price_cents.",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    detailer: Mapped[ProviderProfile] = relationship(
        "ProviderProfile", back_populates="detailer_services"
    )
    service: Mapped[Service] = relationship("Service")

    def __repr__(self) -> str:
        return (
            f"<DetailerService detailer={self.detailer_id} "
            f"service={self.service_id} active={self.is_active}>"
        )


# ------------------------------------------------------------------ #
#  Model: Service                                                     #
# ------------------------------------------------------------------ #

class Service(TimestampMixin, Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[ServiceCategory] = mapped_column(
        # TODO: BUG - This uses the table model (line 636) not the enum (line 131).
        #       After fixing ServiceCategory naming, update to FK:
        #       category_id: Mapped[uuid.UUID] = mapped_column(
        #           ForeignKey("service_categories.id"))
        Enum(ServiceCategory, name="service_category_enum"), nullable=False
    )
    base_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    base_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price_small: Mapped[int] = mapped_column(Integer, nullable=False)
    price_medium: Mapped[int] = mapped_column(Integer, nullable=False)
    price_large: Mapped[int] = mapped_column(Integer, nullable=False)
    price_xl: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_small_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_medium_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_large_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_xl_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    appointments: Mapped[list[Appointment]] = relationship(
        "Appointment", back_populates="service", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Service id={self.id} name={self.name!r}>"


# ------------------------------------------------------------------ #
#  Model: Appointment                                                 #
# ------------------------------------------------------------------ #

class Appointment(TimestampMixin, Base):
    """
    Sprint 3 additions:
    - started_at:              UTC timestamp when status → IN_PROGRESS.
    - completed_at:            UTC timestamp when status → COMPLETED.
    - stripe_payment_intent_id: Stripe pi_xxx. Populated by PaymentService.
    """

    __tablename__ = "appointments"
    __table_args__ = (
        # Composite index for the single most common query pattern:
        # "all active future appointments for this detailer"
        Index(
            "ix_appointments_detailer_scheduled",
            "detailer_id", "scheduled_time", "is_deleted",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    detailer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True, index=True,
        comment="NULL while status=SEARCHING; set when a detailer accepts.",
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="RESTRICT"),
        nullable=True,
        comment=(
            "Sprint 4: single-vehicle snapshot (backward compat). "
            "Sprint 5+: see appointment_vehicles junction table."
        ),
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # UTC scheduling
    scheduled_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
    )
    estimated_end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    travel_buffer_end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Hard boundary: estimated_end_time + 30 min. NULL while SEARCHING.",
    )

    # Lifecycle timestamps
    arrived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
        comment="Set when status transitions to ARRIVED.",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
        comment="Set when status transitions to IN_PROGRESS.",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
        comment="Set when status transitions to COMPLETED.",
    )

    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status_enum"),
        nullable=False, default=AppointmentStatus.PENDING, index=True,
    )

    # Financial
    estimated_price: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="USD cents. Immutable after creation.",
    )
    actual_price: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None,
        comment="USD cents. Set on COMPLETED.",
    )

    # Stripe (Sprint 3)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True,
        comment="Stripe pi_xxx. Set by PaymentService.create_payment_intent().",
    )

    # Notes & location
    client_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    detailer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service_latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    service_longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)

# Relationships
    client: Mapped[User] = relationship(
        "User", foreign_keys=[client_id], back_populates="client_appointments",
        lazy="selectin",
    )
    detailer: Mapped[User] = relationship(
        "User", foreign_keys=[detailer_id], back_populates="detailer_appointments",
        lazy="selectin",
    )
    vehicle: Mapped[Vehicle] = relationship(
        "Vehicle", back_populates="appointments", lazy="selectin",
    )
    service: Mapped[Service] = relationship(
        "Service", back_populates="appointments", lazy="selectin",
    )
    review: Mapped[Review | None] = relationship(
        "Review", back_populates="appointment", uselist=False, lazy="selectin"
    )
    # Sprint 5 — multi-vehicle + addons
    appointment_vehicles: Mapped[list[AppointmentVehicle]] = relationship(
        "AppointmentVehicle", back_populates="appointment", lazy="selectin",
        cascade="all, delete-orphan",
    )
    appointment_addons: Mapped[list[AppointmentAddon]] = relationship(
        "AppointmentAddon", back_populates="appointment", lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Appointment id={self.id} "
            f"status={self.status} "
            f"scheduled={self.scheduled_time.isoformat()}>"
        )


# ------------------------------------------------------------------ #
#  Model: Addon  (Sprint 5)                                           #
# ------------------------------------------------------------------ #

class Addon(TimestampMixin, Base):
    """
    Optional add-on services that stack on top of a base service.

    Examples: Clay Bar Treatment (+$30, +45 min), Odor Eliminator (+$20, +20 min).
    The client selects zero or more addons when booking. Price + duration are
    summed with the base service during AppointmentCreate.

    Prices are immutable snapshots taken at booking time (stored in
    AppointmentAddon) so that price changes don't affect existing appointments.
    """

    __tablename__ = "addons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_cents: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Extra charge in USD cents (e.g. 3000 = $30.00).",
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Extra time added to total appointment duration.",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Addon id={self.id} name={self.name!r} price={self.price_cents}¢>"


# ------------------------------------------------------------------ #
#  Model: AppointmentVehicle  (Sprint 5 junction)                     #
# ------------------------------------------------------------------ #

class AppointmentVehicle(Base):
    """
    One row per vehicle in a multi-vehicle appointment.

    Price + duration are snapshots of what was computed at booking time
    so changes to the service catalogue don't affect existing appointments.
    """

    __tablename__ = "appointment_vehicles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    vehicle_size: Mapped[VehicleSize] = mapped_column(
        Enum(VehicleSize, name="vehicle_size_enum", create_type=False),
        nullable=False,
        comment="Size snapshot at booking time.",
    )
    price_cents: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Price snapshot for this vehicle at booking time.",
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Duration snapshot for this vehicle at booking time.",
    )

    appointment: Mapped[Appointment] = relationship(
        "Appointment", back_populates="appointment_vehicles"
    )
    vehicle: Mapped[Vehicle] = relationship("Vehicle", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<AppointmentVehicle appointment={self.appointment_id} "
            f"vehicle={self.vehicle_id} size={self.vehicle_size.value}>"
        )


# ------------------------------------------------------------------ #
#  Model: AppointmentAddon  (Sprint 5 junction)                       #
# ------------------------------------------------------------------ #

class AppointmentAddon(Base):
    """
    One row per addon selected for a given appointment.

    Price + duration are snapshots so catalogue changes don't retroactively
    affect booked appointments.
    """

    __tablename__ = "appointment_addons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    addon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("addons.id", ondelete="RESTRICT"),
        nullable=False,
    )
    price_cents: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Price snapshot at booking time.",
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Duration snapshot at booking time.",
    )

    appointment: Mapped[Appointment] = relationship(
        "Appointment", back_populates="appointment_addons"
    )
    addon: Mapped[Addon] = relationship("Addon")

    def __repr__(self) -> str:
        return (
            f"<AppointmentAddon appointment={self.appointment_id} "
            f"addon={self.addon_id} price={self.price_cents}¢>"
        )


# ------------------------------------------------------------------ #
#  Model: Review                                                      #
# ------------------------------------------------------------------ #

class Review(TimestampMixin, Base):
    """
    Post-service rating left by the CLIENT for the DETAILER.

    Constraints:
    - One review per appointment (unique constraint on appointment_id).
    - rating must be 1–5 (DB-level CHECK constraint — not just Pydantic).
    - Only allowed after COMPLETED status (enforced in ReviewService).
    """

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("appointment_id", name="uq_review_appointment"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True,
        comment="The CLIENT who submitted the review.",
    )
    detailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True,
        comment="Denormalised for fast detailer rating queries.",
    )
    rating: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="1 (worst) to 5 (best).",
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    appointment: Mapped[Appointment] = relationship(
        "Appointment", back_populates="review"
    )
    reviewer: Mapped[User] = relationship(
        "User", foreign_keys=[reviewer_id], back_populates="reviews_given"
    )

    def __repr__(self) -> str:
        return f"<Review id={self.id} rating={self.rating} appointment={self.appointment_id}>"


# ------------------------------------------------------------------ #
#  Model: AuditLog                                                    #
# ------------------------------------------------------------------ #

class AuditLog(Base):
    """
    Append-only audit trail for compliance and debugging.

    WHY no soft-delete mixin?
    Audit records must be immutable. Allowing is_deleted on an audit log
    would defeat its purpose. Deletion is prevented at the DB level by
    granting only INSERT privilege to the application's DB user.

    WHY JSONB for metadata?
    Event payloads are heterogeneous — a PAYMENT_CAPTURED event has
    different fields from an APPOINTMENT_STATUS_CHANGED event. JSONB
    avoids an EAV (Entity-Attribute-Value) anti-pattern while remaining
    queryable via PostgreSQL's @> operator.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        # "show me all events for appointment X"
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        # "all login events for user X" — partial index skips system (NULL actor) rows
        Index("ix_audit_logs_actor_action", "actor_id", "action",
              postgresql_where="actor_id IS NOT NULL"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="User who triggered the action. NULL for system events.",
    )
    action: Mapped[AuditAction] = mapped_column(
        # FIX: Changed from Postgres ENUM to VARCHAR(50).
        # Adding new audit action types now requires ZERO DB migration.
        # The Python enum provides type safety; the DB just stores strings.
        String(50), nullable=False, index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(60), nullable=False,
        comment="e.g. 'appointment', 'payment'.",
    )
    entity_id: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="UUID of the affected entity as string.",
    )
    stripe_metadata: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Event-specific payload. Queryable via JSONB operators.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    actor: Mapped[User | None] = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} "
            f"action={self.action} "
            f"entity={self.entity_type}:{self.entity_id}>"
        )


# ------------------------------------------------------------------ #
#  Model: WebAuthnCredential                                          #
# ------------------------------------------------------------------ #

class WebAuthnCredential(Base):
    """
    Stores a FIDO2/WebAuthn passkey credential for a user.

    Each row represents one passkey registered on a specific device
    (e.g. "iPhone de Yampi"). A user can have multiple credentials
    (multiple devices).

    credential_id:  The raw credential ID bytes returned by the authenticator.
                    Stored as LargeBinary; transmitted as base64url.
    public_key:     CBOR-encoded COSE public key from the attestation.
                    Used to verify future assertions.
    sign_count:     Monotonically increasing counter to detect cloned authenticators.
                    py_webauthn raises an error when the received count ≤ stored count.
    transports:     List of transport hints ("internal", "hybrid", "usb", etc.)
                    Sent back in allowCredentials so the OS knows how to prompt.
    device_name:    User-facing label set at registration time (e.g. "iPhone 16").
    """

    __tablename__ = "webauthn_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    credential_id: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False, unique=True, index=True,
        comment="Raw credential ID bytes (base64url when transmitted).",
    )
    public_key: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False,
        comment="CBOR-encoded COSE public key from attestation.",
    )
    sign_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Monotonic counter — used to detect cloned authenticators.",
    )
    transports: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        comment='Transport hints, e.g. ["internal", "hybrid"].',
    )
    device_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True,
        comment="User-visible label for this passkey (e.g. 'iPhone 16').",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship("User", back_populates="webauthn_credentials")

    def __repr__(self) -> str:
        return f"<WebAuthnCredential id={self.id} user_id={self.user_id} device={self.device_name!r}>"


# ------------------------------------------------------------------ #
#  Model: AuthProvider  (social login)                               #
# ------------------------------------------------------------------ #

class AuthProvider(Base):
    """
    One row per social identity linked to a user account.

    provider     : "google" | "apple"
    provider_uid : the stable sub/user_id from the provider
    provider_email: email as reported by the provider at link time
                   (Apple only sends this on the first login, so store it here)

    Using a separate table instead of google_id / apple_id columns on User means
    adding a new provider in the future is an INSERT, not an ALTER TABLE.
    """

    __tablename__ = "auth_providers"
    __table_args__ = (
        UniqueConstraint("provider", "provider_uid", name="uq_auth_providers_provider_uid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="Social provider name: 'google' | 'apple'",
    )
    provider_uid: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Stable user identifier from the provider (sub / user_id).",
    )
    provider_email: Mapped[str | None] = mapped_column(
        String(254), nullable=True,
        comment="Email as reported by the provider at link time.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped[User] = relationship("User", back_populates="auth_providers")

    def __repr__(self) -> str:
        return f"<AuthProvider {self.provider}:{self.provider_uid} user_id={self.user_id}>"


# ------------------------------------------------------------------ #
#  Model: RefreshToken  (stateful rotation)                          #
# ------------------------------------------------------------------ #

class RefreshToken(Base):
    """
    One row per issued refresh token.  Enables:
      - Single-use rotation: mark used_at on consumption, issue a new token.
      - Theft detection: if a used token is presented again, revoke the entire
        family_id group and force re-login.
      - Explicit revocation: set revoked=True without waiting for expiry.

    token_hash : SHA-256(raw_token) — only the hash is stored; the raw value
                 is sent to the client once and never persisted.
    family_id  : shared UUID across all rotations of a single session.
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        # Required by the cleanup job: DELETE WHERE expires_at < NOW()
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )
    # TODO: MEDIUM - No automatic cleanup for expired tokens.
    # Expired tokens accumulate indefinitely without a scheduled cleanup job.
    # FIX: Add daily cron job: DELETE FROM refresh_tokens WHERE expires_at < NOW() - interval '1 day'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True,
        comment="SHA-256 hex digest of the raw refresh token.",
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
        comment="Rotation family: all tokens in one session share this ID.",
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Set when this token is consumed. NULL = still valid.",
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Explicit revocation flag (e.g. logout, theft detection).",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<RefreshToken family={self.family_id} used={self.used_at is not None}>"


# ------------------------------------------------------------------ #
#  Model: PasswordResetToken  (single-use)                            #
# ------------------------------------------------------------------ #
# SECURITY FIX (2026-04-24): New table for single-use password reset tokens.
# Problem: Before, password reset tokens were stateless JWTs that could be reused.
# Risk: User clicks link twice, or email preview/缓存 intercepts it, same token works.
# Solution: Store token_hash in DB with used_at. Mark used after first use.
# Pattern: Mirrors RefreshToken but different lifecycle (one-shot vs rotating).
# Usage: 
#   - Create token: generate raw, store SHA-256 hash in DB
#   - Verify: check token_hash + used_at IS NULL + expires_at > now
#   - Consume: UPDATE used_at = NOW() WHERE id = X
#
# NEW: Added password_reset_token_repository.py with:
#   - create(user_id, raw_token, expires_at)
#   - get_by_raw(raw_token) -> token | None
#   - consume(raw_token) -> token | None (atomic mark used)
#   - is_valid(raw_token) -> bool

class PasswordResetToken(Base):
    """
    Single-use password reset tokens. Mirrors RefreshToken pattern:

    - token_hash: SHA-256(raw_token) — only hash stored, raw sent to user once.
    - used_at: If set, token has been consumed (prevents reuse).
    - expires_at: Token lifetime (typically 1 hour).

    Why separate from RefreshToken?
    - Different lifecycle: refresh tokens rotate continuously; reset tokens are one-shot.
    - Different revocation: reset tokens can be explicitly invalidated (e.g., security alert).
    - Audit trail: easier to query "all password resets for user X".

    FIX: Prevents token reuse from intercepted reset links (email preview, double-click).
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True,
        comment="SHA-256 hex digest of the raw reset token.",
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Set when token is consumed. NULL = unused.",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<PasswordResetToken user={self.user_id} used={self.used_at is not None}>"


# ------------------------------------------------------------------ #
#  Model: FareEstimate  (v2)                                         #
# ------------------------------------------------------------------ #

class FareEstimate(Base):
    """
    Snapshot of a fare calculation shown to the client before booking.

    fare_token is an HMAC-SHA256 signature over (id, estimated_price_cents,
    expires_at) so the rides router can verify it without a round-trip if
    the record is already cached in Redis.
    """

    __tablename__ = "fare_estimates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
    )
    vehicle_sizes: Mapped[list] = mapped_column(
        JSONB, nullable=False,
        comment='e.g. ["small", "medium"]',
    )
    client_lat: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    client_lng: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    base_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    surge_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("1.0")
    )
    estimated_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    nearby_detailers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fare_token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True,
        comment="HMAC-SHA256 hex over (id, estimated_price_cents, expires_at).",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<FareEstimate id={self.id} price={self.estimated_price_cents}>"


# ------------------------------------------------------------------ #
#  Model: AppointmentAssignment  (v2)                                #
# ------------------------------------------------------------------ #

class AppointmentAssignment(Base):
    """
    One row per offer attempt.  Multiple rows per appointment are expected
    (first detailer declined/timed out, second accepted, etc.).
    """

    __tablename__ = "appointment_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    detailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    offered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AssignmentStatus.OFFERED.value
    )
    offer_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AppointmentAssignment appt={self.appointment_id} detailer={self.detailer_id} status={self.status}>"


# ------------------------------------------------------------------ #
#  Model: ProcessedWebhook                                            #
# ------------------------------------------------------------------ #

class ProcessedWebhook(Base):
    """
    Deduplication table for Stripe webhook events.

    Stripe guarantees at-least-once delivery — the same event can arrive
    multiple times (network retry, Stripe retry on non-2xx, etc.).
    Without idempotency tracking, PAYMENT_CAPTURED could be processed twice,
    resulting in double-fulfillment or double-credit to a provider.

    Pattern:
      1. Attempt INSERT (stripe_event_id PRIMARY KEY).
      2. If UNIQUE VIOLATION → already processed → return 200 immediately.
      3. If inserted → process event normally.

    Uses ON CONFLICT DO NOTHING so the handler never needs a rollback path.
    """

    __tablename__ = "processed_webhooks"

    stripe_event_id: Mapped[str] = mapped_column(
        String(64), primary_key=True,
        comment="Stripe event ID (evt_xxxxxxxx). Primary key ensures uniqueness.",
    )
    event_type: Mapped[str] = mapped_column(
        String(80), nullable=False,
        comment="Stripe event type, e.g. 'payment_intent.succeeded'.",
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=sa_text("now()"),
    )

    def __repr__(self) -> str:
        return f"<ProcessedWebhook event={self.stripe_event_id} type={self.event_type}>"


# ------------------------------------------------------------------ #
#  Model: Specialty + ProviderSpecialty junction                      #
# ------------------------------------------------------------------ #

class Specialty(Base):
    """
    Lookup table of service specialties (e.g. 'ceramic_coating', 'full_detail').

    Replaces the ProviderProfile.specialties JSONB column (migration e1f2a3b4c5d6).
    Using a proper junction table enables:
      - Efficient filtering: JOIN rather than JSONB @> operator
      - Referential integrity: no dangling slug strings
      - Future per-specialty pricing or metadata

    slug is the stable identifier used in API responses and the seed.
    name is the human-readable label shown in the UI.
    """

    __tablename__ = "specialties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True,
        comment="Stable identifier (e.g. 'ceramic_coating'). Never rename.",
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Human-readable label (e.g. 'Ceramic Coating').",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    providers: Mapped[list["ProviderProfile"]] = relationship(
        "ProviderProfile",
        secondary="provider_specialties",
        back_populates="specialties_rel",
    )

    def __repr__(self) -> str:
        return f"<Specialty slug={self.slug!r}>"


class ProviderSpecialty(Base):
    """
    Many-to-many junction between ProviderProfile and Specialty.
    Composite primary key — one row per (provider, specialty) pair.
    """

    __tablename__ = "provider_specialties"

    provider_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    specialty_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("specialties.id", ondelete="CASCADE"),
        primary_key=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=sa_text("now()"),
    )

    def __repr__(self) -> str:
        return f"<ProviderSpecialty profile={self.provider_profile_id} specialty={self.specialty_id}>"
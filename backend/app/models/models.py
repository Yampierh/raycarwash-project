# app/models/models.py

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone

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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy_utils import EncryptedType

from app.core.config import get_settings


# ------------------------------------------------------------------ #
#  Settings for PII encryption                                       #
# ------------------------------------------------------------------ #

def _get_secret_key() -> str:
    return get_settings().SECRET_KEY


# ------------------------------------------------------------------ #
#  Enumerations                                                       #
# ------------------------------------------------------------------ #

class UserRole(str, enum.Enum):
    CLIENT   = "client"
    DETAILER = "detailer"
    ADMIN    = "admin"


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


# Terminal statuses: no longer occupy a detailer's schedule slot.
TERMINAL_STATUSES: frozenset[AppointmentStatus] = frozenset({
    AppointmentStatus.CANCELLED_BY_CLIENT,
    AppointmentStatus.CANCELLED_BY_DETAILER,
    AppointmentStatus.NO_SHOW,
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
    DETAILER_PROFILE_CREATED = "detailer_profile_created"
    DETAILER_PROFILE_UPDATED = "detailer_profile_updated"


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
    role: Mapped[Role] = relationship("Role")


# ------------------------------------------------------------------ #
#  Model: ClientProfile                                              #
# ------------------------------------------------------------------ #

class ClientProfile(TimestampMixin, Base):
    """
    One-to-one extension of User for CLIENT-specific configuration.
    
    WHY a separate table instead of more columns on User?
    - Client-specific fields (service_address, marketing_preferences, 
      payment_methods) are irrelevant for DETAILER/ADMIN users.
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

    # ---- Payment methods ----
    payment_methods: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        comment=(
            "Stored payment preferences. Structure: "
            '[{"type": "card", "last4": "4242", "brand": "visa"}]'
        ),
    )

    user: Mapped[User] = relationship("User", back_populates="client_profile")

    def __repr__(self) -> str:
        return f"<ClientProfile user_id={self.user_id}>"


# ------------------------------------------------------------------ #
#  Model: User                                                        #
# ------------------------------------------------------------------ #

class User(TimestampMixin, Base):
    """
    Unified user table (CLIENT / DETAILER / ADMIN).
    
    This is the central identity table containing authentication credentials
    and OAuth integration fields. Business logic is decoupled into:
        - ClientProfile: client-specific configuration (address, preferences)
        - DetailerProfile: detailer-specific configuration (bio, working hours)
    
    RBAC is implemented via many-to-many relationship with Role through
    the user_roles association table.
    
    PII fields (full_name, phone_number) are encrypted at rest using
    the application's SECRET_KEY.

    Sprint 3 additions:
    - stripe_customer_id: Stripe's customer object ID, set on first payment.
    
    Sprint 5 additions:
    - google_id, apple_id: Social login integration
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
    full_name: Mapped[str] = mapped_column(
        EncryptedType(String(120), _get_secret_key),
        nullable=True,
        comment="Full name, encrypted at rest using SECRET_KEY",
    )
    phone_number: Mapped[str | None] = mapped_column(
        EncryptedType(String(20), _get_secret_key),
        nullable=True,
        comment="Phone number, encrypted at rest using SECRET_KEY",
    )

    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="bcrypt digest. NEVER expose.",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ---- Stripe (Sprint 3) ----
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True,
        comment="Stripe cus_xxx. Set on first payment intent creation.",
    )

    # ---- Social auth (Sprint 5) ----
    google_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True,
        comment="Google user ID ('sub' from tokeninfo). NULL for non-Google users.",
    )
    apple_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True,
        comment="Apple 'sub' claim from identity_token. NULL for non-Apple users.",
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
    detailer_profile: Mapped[DetailerProfile | None] = relationship(
        "DetailerProfile",
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

    def is_detailer(self) -> bool:
        """Check if user has detailer role."""
        return self.has_role("detailer")

    @property
    def primary_role(self) -> str | None:
        """
        Get the user's primary role for JWT token payload.
        
        Returns the first role name, defaulting to 'client' if no roles assigned.
        """
        if self.user_roles:
            return self.user_roles[0].role.name
        return "client"

    @classmethod
    async def create_with_profiles(
        cls,
        email: str,
        password_hash: str,
        full_name: str,
        role_names: list[str],
        *,
        phone_number: str | None = None,
        session: "AsyncSession | None" = None,
    ) -> "User":
        """
        Factory method to create a user with the appropriate profile(s).
        
        This method handles the creation of both the User instance and any
        associated profile (ClientProfile or DetailerProfile) based on the
        assigned roles.
        
        Args:
            email: User's email address (must be unique)
            password_hash: Pre-hashed bcrypt password
            full_name: User's full name (will be encrypted)
            role_names: List of role names to assign (e.g., ['client'], ['detailer'])
            phone_number: Optional phone number (will be encrypted)
            session: Optional async SQLAlchemy session for database operations
            
        Returns:
            A new User instance with associated profile(s) created
            
        Note:
            If using with a session, you must call session.add() and commit()
            after this method returns. The method does not commit by default
            to allow for transactional control.
        """
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession as AsyncSession

        user = cls(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            phone_number=phone_number,
        )

        if session is not None:
            session.add(user)
            await session.flush()

            role_stmt = select(Role).where(Role.name.in_(role_names))
            result = await session.execute(role_stmt)
            roles = result.scalars().all()
            for role in roles:
                user_role = UserRoleAssociation(
                    user_id=user.id,
                    role_id=role.id,
                )
                session.add(user_role)

            if "detailer" in role_names:
                detailer_profile = DetailerProfile(user_id=user.id)
                session.add(detailer_profile)

            if "client" in role_names:
                client_profile = ClientProfile(user_id=user.id)
                session.add(client_profile)
        else:
            user._pending_role_names = role_names

        return user

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


# ------------------------------------------------------------------ #
#  Model: DetailerProfile                                             #
# ------------------------------------------------------------------ #

class DetailerProfile(TimestampMixin, Base):
    """
    One-to-one extension of User for DETAILER-specific configuration.

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

    __tablename__ = "detailer_profiles"

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

    average_rating: Mapped[float | None] = mapped_column(
        Numeric(3, 2), nullable=True,
        comment="Denormalised average — updated on every new review.",
    )
    total_reviews: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    # ---- Specialties (Sprint 6) ----
    specialties: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, default=list,
        comment='List of specialty tags, e.g. ["ceramic_coating", "full_detail"].',
    )

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

    user: Mapped[User] = relationship("User", back_populates="detailer_profile")
    detailer_services: Mapped[list[DetailerService]] = relationship(
        "DetailerService", back_populates="detailer", lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<DetailerProfile user_id={self.user_id}>"


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
        ForeignKey("detailer_profiles.id", ondelete="CASCADE"),
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

    detailer: Mapped[DetailerProfile] = relationship(
        "DetailerProfile", back_populates="detailer_services"
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
    detailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True,
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
    estimated_end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    travel_buffer_end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Hard boundary: estimated_end_time + 30 min.",
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
        # Speeds up "show me all events for appointment X" queries
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
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
        Enum(AuditAction, name="audit_action_enum"),
        nullable=False, index=True,
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
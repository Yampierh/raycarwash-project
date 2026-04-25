# app/schemas/schemas.py

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from app.models.models import (
    AppointmentStatus,
    ServiceCategory,
    VehicleSize,
)


# ------------------------------------------------------------------ #
#  Shared base                                                        #
# ------------------------------------------------------------------ #

class _BaseSchema(BaseModel):
    """Base for all response schemas. Builds from ORM objects via from_attributes=True."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class _BaseRequestSchema(BaseModel):
    """Base for all request schemas. No from_attributes — input always comes from JSON."""
    model_config = ConfigDict(str_strip_whitespace=True)


PositiveCents = int  # Validated via Field(gt=0) at usage sites


# ================================================================== #
#  AUTH SCHEMAS                                                       #
# ================================================================== #

class Token(_BaseSchema):
    """Response for POST /auth/token and POST /auth/refresh (OAuth2 form flow)."""
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    """Body para POST /auth/register — crear cuenta nueva."""
    email: EmailStr
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        # TODO: MEDIUM - Password complexity requirements missing.
        # BUG: Only enforces length - no complexity rules.
        # Risk: Weak passwords (e.g., "password123") are accepted.
        # FIX: Add validator for complexity:
        # - At least 1 uppercase letter
        # - At least 1 lowercase letter
        # - At least 1 number
        # - At least 1 special character (!@#$%^&*)
        # Example validator:
        # @field_validator('password')
        # def validate_password_strength(cls, v):
        #     if not re.search(r'[A-Z]', v): raise ValueError('uppercase')
        #     if not re.search(r'[a-z]', v): raise ValueError('lowercase')
        #     if not re.search(r'\d', v): raise ValueError('number')
        #     if not re.search(r'[!@#$%^&*]', v): raise ValueError('special')
        #     return v
    )

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower().strip()


class LoginRequest(BaseModel):
    """Body for POST /auth/login."""
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower().strip()


class LoginResponse(_BaseSchema):
    """
    Response for POST /auth/login and POST /auth/register.

    Onboarding pending (onboarding_completed=False):
      access_token=None, refresh_token=None, onboarding_token=<token>, next_step="complete_profile"

    Fully onboarded (onboarding_completed=True):
      access_token=<token>, refresh_token=<token>, onboarding_token=None, next_step="app"
    """
    access_token: str | None = None
    refresh_token: str | None = None
    onboarding_token: str | None = None
    roles: list[str] = Field(default_factory=list)
    onboarding_completed: bool = False
    next_step: str  # "complete_profile" | "detailer_onboarding" | "app"


class LogoutRequest(BaseModel):
    """Body for POST /auth/logout. Revokes the given refresh token (this device only)."""
    refresh_token: str


class CheckEmailRequest(BaseModel):
    """Body for POST /auth/check-email."""
    email: EmailStr


class CheckEmailResponse(_BaseSchema):
    """Response for POST /auth/check-email."""
    email: str
    exists: bool
    auth_method: str  # "password" | "google" | "apple" | "both" | "none"
    suggested_action: str  # "login" | "social_login" | "register"


class IdentifierRequest(BaseModel):
    """Body for POST /auth/identify (Identifier-First flow)."""
    identifier: str = Field(..., description="Email address or phone number.")
    identifier_type: str | None = Field(
        default=None,
        description="'email' or 'phone'. Auto-detected if omitted."
    )


class IdentifierResponse(_BaseSchema):
    """Response for POST /auth/identify."""
    identifier: str
    identifier_type: str  # "email" | "phone"
    exists: bool
    auth_methods: list[str]  # ["password", "google", "apple"]
    is_new_user: bool
    suggested_action: str  # "login_password" | "login_social" | "register"


class VerifyRequest(BaseModel):
    """Body for POST /auth/verify (Identifier-First login, backward-compatible)."""
    identifier: str
    identifier_type: str
    provider: str | None = None
    password: str | None = None
    access_token: str | None = None
    otp_code: str | None = None


class VerifyResponse(_BaseSchema):
    """Response for POST /auth/verify (Identifier-First login)."""
    access_token: str | None = None
    refresh_token: str | None = None
    is_new_user: bool
    temp_token: str | None = None
    needs_profile_completion: bool = False
    next_step: str  # "complete_profile" | "detailer_onboarding" | "app"
    assigned_role: str | None = None


class CompleteProfileRequest(BaseModel):
    """Body for PUT /auth/complete-profile."""
    full_name: str
    phone_number: str | None = None
    role: str = Field(default="client", description="'client' or 'detailer'")


class TokenData(_BaseSchema):
    """Internal representation of a decoded JWT payload. Never returned to clients."""
    user_id: uuid.UUID
    role: str


# ---- Social login ---- #

class GoogleLoginRequest(BaseModel):
    """Body for POST /auth/google — PKCE authorization code flow."""
    code: str = Field(..., description="Authorization code from Google OAuth2.")
    code_verifier: str = Field(..., description="PKCE code verifier generated by the client.")
    redirect_uri: str = Field(..., description="Must match the URI used in the authorization request.")


class AppleLoginRequest(BaseModel):
    """Body for POST /auth/apple."""
    identity_token: str = Field(..., description="RS256-signed JWT from Apple.")
    full_name: str | None = Field(
        default=None,
        max_length=120,
        description=(
            "User's full name. Apple only sends this on the first login; "
            "el frontend debe capturarlo y enviarlo en ese primer request."
        ),
    )


class SocialAuthResponse(BaseModel):
    """
    Response for POST /auth/google and POST /auth/apple.

    Onboarding required (new user or social account with no roles yet):
      onboarding_required=True, onboarding_token=<token>, access_token=None

    Fully onboarded (existing user):
      onboarding_required=False, access_token=<token>, refresh_token=<token>
    """
    is_new_user: bool
    onboarding_required: bool = False
    onboarding_token: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    active_role: str | None = None


class PasswordResetRequest(BaseModel):
    """Body for POST /auth/password-reset."""
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """Body for POST /auth/password-reset/confirm."""
    token: str = Field(..., description="Single-use reset token from email.")
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetConfirmResponse(BaseModel):
    """Response for successful password reset."""
    message: str


class PasswordResetResponse(BaseModel):
    message: str


# ================================================================== #
#  USER SCHEMAS                                                       #
# ================================================================== #

class UserCreate(_BaseRequestSchema):
    email: EmailStr = Field(..., examples=["jane.doe@example.com"])
    full_name: str = Field(..., min_length=2, max_length=120, examples=["Jane Doe"])
    phone_number: str | None = Field(
        default=None,
        pattern=r"^\+?[1-9]\d{1,14}$",
        examples=["+12605550100"],
    )
    password: str = Field(..., min_length=8, max_length=128)
    role_names: list[str] | None = Field(
        default=None,
        description="Optional roles to assign. Default is ['client'] if not provided.",
    )

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("role_names", mode="before")
    @classmethod
    def restrict_admin_registration(cls, value: list[str] | None) -> list[str] | None:
        if value and "admin" in value:
            raise ValueError(
                "No es posible registrarse como ADMIN. "
                "Contacta un administrador de la plataforma."
            )
        return value


class UserRead(_BaseSchema):
    """
    Representación pública del usuario.
    Excluye: password_hash, is_deleted, deleted_at.
    """
    id: uuid.UUID
    email: str
    full_name: str | None = Field(default=None)
    phone_number: str | None = Field(default=None)
    roles: list[str]  # Role names (e.g., ["client"], ["detailer"])
    onboarding_completed: bool
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(_BaseRequestSchema):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone_number: str | None = Field(default=None, pattern=r"^\+?[1-9]\d{1,14}$")
    # Note: service_address moved to ClientProfile


# ================================================================== #
#  VEHICLE SCHEMAS                                                    #
# ================================================================== #

class VehicleCreate(_BaseRequestSchema):
    make: str = Field(..., min_length=1, max_length=60, examples=["Kia"])
    model: str = Field(..., min_length=1, max_length=60, examples=["K5"])
    year: int = Field(..., ge=1970, le=2030, examples=[2023])
    vin: str | None = Field(default=None, min_length=17, max_length=17, examples=["1HGCM82633A003241"]) 
    series: str | None = Field(default=None, max_length=60, examples=["GT-Line"])
    body_class: str = Field(..., min_length=1, max_length=60, examples=["Sedan"])
    color: str | None = Field(default=None, max_length=40, examples=["Red"])
    license_plate: str | None = Field(default=None, max_length=20, examples=["FWT-821"])
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("license_plate", mode="before")
    @classmethod
    def uppercase_plate(cls, value: str | None) -> str | None:
        """mode="before" correcto: normalizar string antes de validar."""
        return value.upper() if value else value


class VehicleRead(_BaseSchema):
    id: uuid.UUID
    owner_id: uuid.UUID
    make: str
    model: str
    year: int
    vin: str | None = Field(default=None)
    series: str | None = Field(default=None)
    body_class: str | None = Field(default=None)
    color: str
    license_plate: str
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[misc]
    @property
    def suggested_size(self) -> str | None:
        """
        Pricing tier derived from body_class at runtime. Never stored in DB.
        Returns: "small" | "medium" | "large" | "xl" | None
        """
        if not self.body_class:
            return None
        from app.services.vehicle_lookup import map_body_to_size
        return map_body_to_size(self.body_class).value


# ================================================================== #
#  APPOINTMENT SCHEMAS                                                #
# ================================================================== #

class AppointmentVehicleCreate(BaseModel):
    """One vehicle entry in the new multi-vehicle appointment create body."""
    vehicle_id: uuid.UUID
    service_id: uuid.UUID
    addon_ids: list[uuid.UUID] = Field(default_factory=list)


class AppointmentCreate(_BaseRequestSchema):
    """
    Payload de creación de cita — frontend contract (Sprint 6).

    New format: `vehicles` array, each item carries its own service + addons.
    Legacy single-vehicle format also accepted for backward compat.
    """
    detailer_id: uuid.UUID
    scheduled_time: datetime = Field(
        ...,
        description=(
            "Fecha y hora de inicio en UTC (ISO 8601 con timezone). "
            "Ejemplo: '2025-12-15T10:00:00Z'"
        ),
    )
    service_address: str = Field(..., min_length=5, max_length=255)
    service_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    service_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    client_notes: str | None = Field(default=None, max_length=2000)

    # New multi-vehicle format
    vehicles: list[AppointmentVehicleCreate] | None = Field(
        default=None,
        min_length=1,
        max_length=10,
        description="Each vehicle has its own service_id and addon_ids.",
    )

    # Legacy single-vehicle compat fields
    vehicle_id: uuid.UUID | None = Field(default=None)
    vehicle_ids: list[uuid.UUID] | None = Field(default=None, min_length=1, max_length=10)
    addon_ids: list[uuid.UUID] = Field(default_factory=list)
    service_id: uuid.UUID | None = Field(default=None)

    @field_validator("scheduled_time", mode="after")
    @classmethod
    def must_be_utc_and_future(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError(
                "scheduled_time debe incluir zona horaria (UTC). "
                "Ejemplo: '2025-12-15T10:00:00Z'"
            )
        utc_value = value.astimezone(timezone.utc)
        if utc_value <= datetime.now(timezone.utc):
            raise ValueError("scheduled_time debe ser una fecha futura.")
        return utc_value

    @model_validator(mode="after")
    def normalize_vehicle_fields(self) -> AppointmentCreate:
        """
        Normalize new vs legacy format into a canonical `vehicles` list.
        After this validator, `self.vehicles` is always set.
        """
        if self.vehicles:
            # New format — already set, nothing to do
            return self

        # Legacy: build vehicles list from flat fields
        if self.vehicle_ids:
            vids = self.vehicle_ids
        elif self.vehicle_id:
            vids = [self.vehicle_id]
        else:
            raise ValueError(
                "Proporciona 'vehicles' (nuevo formato) o 'vehicle_id'/'vehicle_ids' (legado)."
            )

        if not self.service_id:
            raise ValueError(
                "service_id es requerido cuando se usa el formato legado (vehicle_id/vehicle_ids)."
            )

        object.__setattr__(self, "vehicles", [
            AppointmentVehicleCreate(
                vehicle_id=vid,
                service_id=self.service_id,
                addon_ids=self.addon_ids,
            )
            for vid in vids
        ])
        return self

    @model_validator(mode="after")
    def validate_coordinates_both_or_none(self) -> AppointmentCreate:
        lat, lon = self.service_latitude, self.service_longitude
        if (lat is None) != (lon is None):
            raise ValueError(
                "service_latitude y service_longitude deben proporcionarse juntos o ambos omitirse."
            )
        return self


class _VehicleSnap(_BaseSchema):
    """Minimal vehicle info embedded in appointment responses."""
    make: str
    model: str
    body_class: str | None = Field(default=None)
    color: str


class AppointmentVehicleRead(_BaseSchema):
    """Un vehículo dentro de una cita — includes nested vehicle snapshot."""
    id: uuid.UUID
    vehicle_id: uuid.UUID
    vehicle_size: VehicleSize
    price_cents: int
    duration_minutes: int
    vehicle: _VehicleSnap | None = Field(default=None)


class AppointmentAddonRead(_BaseSchema):
    """Un addon dentro de una cita (Sprint 5)."""
    id: uuid.UUID
    addon_id: uuid.UUID
    price_cents: int
    duration_minutes: int


class _ClientSnap(_BaseSchema):
    """Client info embedded in appointment responses."""
    full_name: str
    phone: str | None = Field(default=None)


class _DetailerSnap(_BaseSchema):
    """Detailer info embedded in appointment responses."""
    full_name: str


class AppointmentRead(_BaseSchema):
    """
    Full appointment detail — includes nested client, detailer, and vehicles.
    Uses frontend contract field names: estimated_price_cents, actual_price_cents.
    """
    id: uuid.UUID
    status: AppointmentStatus
    scheduled_time: datetime
    estimated_end_time: datetime
    travel_buffer_end_time: datetime
    service_address: str | None = Field(default=None)
    client_notes: str | None = Field(default=None)
    detailer_notes: str | None = Field(default=None)
    service_latitude: float | None = Field(default=None)
    service_longitude: float | None = Field(default=None)

    # Financial — frontend expects these exact names
    estimated_price_cents: int = Field(
        alias="estimated_price",
        description="Centavos USD totales al crear la cita.",
    )
    actual_price_cents: int | None = Field(
        default=None,
        alias="actual_price",
        description="Centavos USD finales. NULL hasta COMPLETED.",
    )

    # Lifecycle timestamps
    arrived_at: datetime | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    stripe_payment_intent_id: str | None = Field(default=None)

    # Nested objects (no extra calls needed from frontend)
    client: _ClientSnap | None = Field(default=None)
    detailer: _DetailerSnap | None = Field(default=None)
    vehicles: list[AppointmentVehicleRead] = Field(default_factory=list)

    # Legacy / internal IDs still included for reference
    client_id: uuid.UUID
    detailer_id: uuid.UUID
    vehicle_id: uuid.UUID | None = Field(default=None)
    service_id: uuid.UUID | None = Field(default=None)

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class AppointmentStatusUpdate(_BaseSchema):
    """
    Payload mínimo para PATCH /appointments/{id}/status.

    Solo permite cambiar status, detailer_notes y actual_price.
    Todos los demás campos son inmutables post-creación.
    """
    status: AppointmentStatus
    detailer_notes: str | None = Field(default=None, max_length=2000)
    actual_price: int | None = Field(
        default=None,
        gt=0,
        description=(
            "Precio final en centavos USD. "
            "OBLIGATORIO al transicionar a COMPLETED. "
            "Puede diferir de estimated_price por servicios adicionales."
        ),
    )



# ================================================================== #
#  SERVICE SCHEMAS                                                    #
# ================================================================== #

class ServiceRead(_BaseSchema):
    """Representación pública de un servicio con columnas de caché por tamaño."""
    id: uuid.UUID
    name: str
    # BUG-11 CORREGIDO: description es nullable en el modelo ORM
    description: str | None = Field(default=None)
    category: ServiceCategory
    base_price_cents: int
    base_duration_minutes: int
    price_small: int
    price_medium: int
    price_large: int
    price_xl: int
    duration_small_minutes: int
    duration_medium_minutes: int
    duration_large_minutes: int
    duration_xl_minutes: int
    is_active: bool
    created_at: datetime


# ================================================================== #
#  ADDON SCHEMAS  (Sprint 5)                                          #
# ================================================================== #

class AddonRead(_BaseSchema):
    """
    Servicio extra opcional que el cliente puede agregar a una cita.
    El precio y la duración se suman al total de la reserva.
    """
    id: uuid.UUID
    name: str
    description: str | None = Field(default=None)
    price_cents: int
    duration_minutes: int
    is_active: bool
    created_at: datetime


# ================================================================== #
#  MATCHING SCHEMAS  (Sprint 5)                                       #
# ================================================================== #

class MatchingResult(_BaseSchema):
    """
    Un detailer compatible retornado por GET /api/v1/matching.
    El elemento en el índice 0 es la recomendación del sistema.
    """
    user_id: uuid.UUID
    full_name: str
    bio: str | None = Field(default=None)
    years_of_experience: int | None = Field(default=None)
    service_radius_miles: int
    is_accepting_bookings: bool
    average_rating: float | None = Field(default=None)
    total_reviews: int
    distance_miles: float | None = Field(default=None)
    # Frontend contract field names
    estimated_price: int = Field(description="Precio total en centavos USD.")
    estimated_duration: int = Field(description="Duración total en minutos.")
    available_slots: list[TimeSlotRead] = Field(default_factory=list)


# ================================================================== #
#  ENVELOPES DE RESPUESTA GENÉRICOS                                   #
# ================================================================== #

class HealthResponse(_BaseSchema):
    status: str = "ok"
    service: str
    version: str
    db_reachable: bool


class ErrorDetail(_BaseSchema):
    code: str = Field(..., examples=["VALIDATION_ERROR", "NOT_FOUND"])
    message: str
    details: list[dict] | None = Field(default=None)


# ================================================================== #
#  SPRINT 3: SCHEMAS DE DISPONIBILIDAD                                #
# ================================================================== #

class TimeSlotRead(_BaseSchema):
    """
    Un slot de 30 minutos en el calendario del detailer.
    start_time / end_time son UTC-aware (ISO 8601 en el wire).
    """
    start_time: datetime
    end_time: datetime
    is_available: bool


class AvailabilityRequest(_BaseSchema):
    """Parámetros para GET /api/v1/detailers/{id}/availability."""
    request_date: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        examples=["2025-06-15"],
        description="Fecha en formato YYYY-MM-DD (ISO 8601).",
    )
    service_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Opcional. Con vehicle_size, los slots se calculan para acomodar "
            "la duración completa del servicio."
        ),
    )
    vehicle_size: VehicleSize | None = Field(default=None)


# ================================================================== #
#  SPRINT 3: SCHEMAS DE UBICACIÓN                                     #
# ================================================================== #

class LocationUpdate(_BaseRequestSchema):
    """
    Payload para POST /api/v1/detailers/location.

    BUG-18 CORREGIDO: heredaba de _BaseSchema (from_attributes=True),
    lo cual es semánticamente incorrecto para un schema de REQUEST.
    Los schemas de entrada nunca se construyen desde objetos ORM.
    """

    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    heading: float | None = Field(default=None, ge=0.0, lt=360.0)


class LocationResponse(_BaseSchema):
    user_id: uuid.UUID
    latitude: float
    longitude: float
    updated_at: datetime


# ================================================================== #
#  SPRINT 3: SCHEMAS DE REVIEWS                                       #
# ================================================================== #

class ReviewCreate(_BaseRequestSchema):
    """
    Payload para POST /api/v1/reviews.
    Hereda _BaseRequestSchema (no _BaseSchema) — es un schema de REQUEST.
    """

    appointment_id: uuid.UUID
    rating: int = Field(
        ..., ge=1, le=5,
        description="1 (peor) → 5 (mejor). Validado también a nivel DB (CHECK CONSTRAINT).",
    )
    comment: str | None = Field(default=None, max_length=2000)


class ReviewRead(_BaseSchema):
    id: uuid.UUID
    appointment_id: uuid.UUID
    reviewer_id: uuid.UUID
    detailer_id: uuid.UUID
    rating: int
    # BUG-12 CORREGIDO
    comment: str | None = Field(default=None)
    created_at: datetime


# ================================================================== #
#  SPRINT 3: SCHEMAS DE PAGOS                                         #
# ================================================================== #

class PaymentIntentResponse(_BaseSchema):
    """
    Respuesta de POST /api/v1/payments/create-intent.

    client_secret se pasa directamente al Stripe SDK en el frontend:
        await stripe.confirmPayment({ clientSecret })
    NUNCA loguear este valor — es un token de autenticación temporal.
    """
    payment_intent_id: str
    client_secret: str
    amount_cents: int
    currency: str = "usd"
    status: str


class PaymentIntentRequest(_BaseSchema):
    appointment_id: uuid.UUID


# ================================================================== #
#  SPRINT 3: PAGINACIÓN                                               #
# ================================================================== #

class PaginatedResponse(_BaseSchema):
    """Envelope genérico para endpoints de lista con paginación."""
    # STYLE-1 CORREGIDO: list → list[Any] para compatibilidad con mypy strict
    items: list[Any]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(
        cls,
        items: list[Any],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedResponse:
        pages = max(1, -(-total // page_size))  # división techo sin math.ceil
        return cls(items=items, total=total, page=page, page_size=page_size, pages=pages)


# ================================================================== #
#  SPRINT 3: SCHEMAS DE DETAILER                                      #
# ================================================================== #

class ProviderProfileRead(_BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    bio: str | None = Field(default=None)
    years_of_experience: int | None = Field(default=None)
    is_accepting_bookings: bool
    service_radius_miles: int
    timezone: str = Field(default="America/Indiana/Indianapolis")
    working_hours: dict
    average_rating: float | None = Field(default=None)
    total_reviews: int
    created_at: datetime


class DetailerMeRead(_BaseSchema):
    """
    Full private profile returned by GET /api/v1/detailers/me.
    Includes stats computed from appointments.
    """
    user_id: uuid.UUID
    full_name: str
    bio: str | None = Field(default=None)
    years_of_experience: int | None = Field(default=None)
    service_radius_miles: int
    is_accepting_bookings: bool
    average_rating: float | None = Field(default=None)
    total_reviews: int
    total_earnings_cents: int = Field(default=0)
    total_services: int = Field(default=0)
    specialties: list[str] = Field(default_factory=list)
    created_at: datetime


class DetailerServiceRead(_BaseSchema):
    """One platform service as seen by the owning detailer (GET /detailers/me/services)."""
    service_id: uuid.UUID
    name: str
    description: str | None = Field(default=None)
    base_price_cents: int
    custom_price_cents: int | None = Field(default=None)
    is_active: bool


class DetailerServiceUpdate(_BaseRequestSchema):
    """PATCH /detailers/me/services/{service_id}"""
    is_active: bool
    custom_price_cents: int | None = Field(
        default=None,
        gt=0,
        description="Override base price in cents. null = use platform base price.",
    )


class DetailerStatusUpdate(BaseModel):
    """PATCH /detailers/me/status"""
    is_accepting_bookings: bool


# ================================================================== #
#  SPRINT 3: SCHEMAS DE AUDITORÍA                                     #
# ================================================================== #

class AuditLogRead(_BaseSchema):
    id: uuid.UUID
    # BUG-16,17 CORREGIDOS: actor_id y metadata son nullable en el modelo
    actor_id: uuid.UUID | None = Field(default=None)
    action: str
    entity_type: str
    entity_id: str
    metadata: dict | None = Field(default=None)
    created_at: datetime


# ================================================================== #
#  SPRINT 4: DETAILER ONBOARDING + DISCOVERY                          #
# ================================================================== #

_IANA_TIMEZONE_PATTERN = r"^[A-Za-z]+(/[A-Za-z_]+)+$"

_DEFAULT_WORKING_HOURS: dict = {
    "monday":    {"start": "08:00", "end": "18:00", "enabled": True},
    "tuesday":   {"start": "08:00", "end": "18:00", "enabled": True},
    "wednesday": {"start": "08:00", "end": "18:00", "enabled": True},
    "thursday":  {"start": "08:00", "end": "18:00", "enabled": True},
    "friday":    {"start": "08:00", "end": "18:00", "enabled": True},
    "saturday":  {"start": "09:00", "end": "16:00", "enabled": True},
    "sunday":    {"start": None,    "end": None,    "enabled": False},
}

_VALID_DAYS = frozenset({
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
})


class WorkingHoursDay(BaseModel):
    """Single day schedule within the working_hours JSONB map."""
    start: str | None = Field(
        default=None,
        pattern=r"^\d{2}:\d{2}$",
        examples=["08:00"],
    )
    end: str | None = Field(
        default=None,
        pattern=r"^\d{2}:\d{2}$",
        examples=["18:00"],
    )
    enabled: bool = True

    @model_validator(mode="after")
    def start_and_end_required_when_enabled(self) -> WorkingHoursDay:
        if self.enabled and (self.start is None or self.end is None):
            raise ValueError(
                "start and end times are required when the day is enabled."
            )
        return self


class ProviderProfileCreate(_BaseRequestSchema):
    """
    Payload for POST /api/v1/detailers/profile.

    Creates the ProviderProfile row for an existing DETAILER user.
    All fields except timezone are optional (sensible defaults are applied).
    """

    bio: str | None = Field(
        default=None,
        max_length=1000,
        examples=["Professional detailer with 5 years of experience in Fort Wayne."],
    )
    years_of_experience: int | None = Field(
        default=None, ge=0, le=50, examples=[5]
    )
    service_radius_miles: int = Field(
        default=25, ge=1, le=100,
        description="Maximum distance the detailer will travel to a client.",
    )
    timezone: str = Field(
        default="America/Indiana/Indianapolis",
        pattern=_IANA_TIMEZONE_PATTERN,
        examples=["America/Indiana/Indianapolis", "America/Chicago", "America/New_York"],
        description="IANA timezone name for local-time slot display.",
    )
    working_hours: dict[str, WorkingHoursDay] | None = Field(
        default=None,
        description=(
            "7-day schedule keyed by lowercase day name. "
            "Omit to use the platform default (Mon–Sat 08:00–18:00, Sun off)."
        ),
    )
    specialties: list[str] | None = Field(
        default=None,
        examples=[["ceramic_coating", "interior_deep_clean"]],
        description="List of specialty tags.",
    )

    @field_validator("working_hours", mode="before")
    @classmethod
    def validate_working_hours_keys(cls, v: dict | None) -> dict | None:
        if v is None:
            return v
        invalid = set(v.keys()) - _VALID_DAYS
        if invalid:
            raise ValueError(
                f"Invalid day keys in working_hours: {invalid}. "
                f"Allowed: {sorted(_VALID_DAYS)}."
            )
        return v


class ProviderProfileUpdate(_BaseRequestSchema):
    """
    Payload for PATCH /api/v1/detailers/profile.
    All fields are optional — only supplied fields are updated.
    """
    bio: str | None = Field(default=None, max_length=1000)
    years_of_experience: int | None = Field(default=None, ge=0, le=50)
    is_accepting_bookings: bool | None = Field(default=None)
    service_radius_miles: int | None = Field(default=None, ge=1, le=100)
    timezone: str | None = Field(
        default=None,
        pattern=_IANA_TIMEZONE_PATTERN,
        examples=["America/Indiana/Indianapolis"],
    )
    working_hours: dict[str, WorkingHoursDay] | None = Field(default=None)

    @field_validator("working_hours", mode="before")
    @classmethod
    def validate_working_hours_keys(cls, v: dict | None) -> dict | None:
        if v is None:
            return v
        invalid = set(v.keys()) - _VALID_DAYS
        if invalid:
            raise ValueError(
                f"Invalid day keys in working_hours: {invalid}. "
                f"Allowed: {sorted(_VALID_DAYS)}."
            )
        return v


class DetailerPublicRead(_BaseSchema):
    """
    Public detailer card for discovery results (GET /api/v1/detailers).

    Joins User + ProviderProfile — constructed manually in the router
    because it spans two ORM objects.
    """
    user_id: uuid.UUID
    full_name: str
    bio: str | None = Field(default=None)
    years_of_experience: int | None = Field(default=None)
    service_radius_miles: int
    is_accepting_bookings: bool
    average_rating: float | None = Field(default=None)
    total_reviews: int
    # Distance from the queried coordinates (None if no location filter used)
    distance_miles: float | None = Field(
        default=None,
        description="Great-circle distance from the searched coordinates in miles.",
    )


# ================================================================== #
#  SPRINT 4: REFUND SCHEMAS                                           #
# ================================================================== #

class RefundResponse(_BaseSchema):
    """
    Response returned after a cancellation triggers an automatic refund.
    """
    appointment_id: uuid.UUID
    refund_amount_cents: int = Field(
        description="USD cents actually refunded. 0 if no refund applies."
    )
    refund_policy_applied: str = Field(
        description=(
            "One of: 'full' (100%%), 'partial' (50%%), 'none' (0%%). "
            "Determined by time remaining until the appointment."
        ),
        examples=["full", "partial", "none"],
    )
    stripe_refund_id: str | None = Field(
        default=None,
        description="Stripe re_xxx ID. Null if no payment was captured or refund is zero.",
    )


# ------------------------------------------------------------------ #
#  WebAuthn / FIDO2 Passkeys                                         #
# ------------------------------------------------------------------ #

class WebAuthnRegisterBeginResponse(_BaseSchema):
    """
    Returned by POST /auth/webauthn/register/begin.
    The client passes `options` directly to Passkey.register() and sends
    `challenge_token` back with the complete request.
    """
    challenge_token: str = Field(
        description="Short-lived JWT (5 min) embedding the challenge bytes and user ID."
    )
    options: dict = Field(
        description="PublicKeyCredentialCreationOptions serialized to JSON-compatible dict."
    )


class WebAuthnRegisterCompleteRequest(_BaseRequestSchema):
    """Body for POST /auth/webauthn/register/complete."""
    challenge_token: str = Field(description="JWT returned by register/begin.")
    credential: dict = Field(
        description=(
            "AuthenticatorAttestationResponse from Passkey.register(). "
            "Must include id, rawId, response (clientDataJSON, attestationObject), type."
        )
    )
    device_name: str = Field(
        default="My Device",
        max_length=120,
        description="User-visible label for this passkey (e.g. 'iPhone 16').",
    )


class WebAuthnRegisterCompleteResponse(_BaseSchema):
    """Returned after successful passkey registration."""
    credential_id: str = Field(description="base64url-encoded credential ID.")
    device_name: str


class WebAuthnAuthBeginRequest(_BaseRequestSchema):
    """Body for POST /auth/webauthn/authenticate/begin."""
    email: str = Field(description="Email of the user attempting passkey login.")


class WebAuthnAuthBeginResponse(_BaseSchema):
    """
    Returned by POST /auth/webauthn/authenticate/begin.
    The client passes `options` directly to Passkey.authenticate() and sends
    `challenge_token` back with the complete request.
    """
    challenge_token: str = Field(
        description="Short-lived JWT (5 min) embedding the challenge bytes and user ID."
    )
    options: dict = Field(
        description="PublicKeyCredentialRequestOptions serialized to JSON-compatible dict."
    )


class WebAuthnAuthCompleteRequest(_BaseRequestSchema):
    """Body for POST /auth/webauthn/authenticate/complete."""
    challenge_token: str = Field(description="JWT returned by authenticate/begin.")
    credential: dict = Field(
        description=(
            "AuthenticatorAssertionResponse from Passkey.authenticate(). "
            "Must include id, rawId, response (clientDataJSON, authenticatorData, signature), type."
        )
    )


class WebAuthnCredentialRead(_BaseSchema):
    """Public representation of a stored passkey credential."""
    id: uuid.UUID
    credential_id: str = Field(description="base64url-encoded credential ID.")
    device_name: str | None
    created_at: datetime
    last_used_at: datetime | None


class WebAuthnCredentialsListResponse(_BaseSchema):
    """Response for GET /auth/webauthn/credentials."""
    credentials: list[WebAuthnCredentialRead]
    total: int


class WebAuthnCredentialRenameRequest(_BaseRequestSchema):
    """Body for PATCH /auth/webauthn/credentials/{id}."""
    device_name: str = Field(
        ..., min_length=1, max_length=120,
        description="New user-visible label for this passkey (e.g. 'Work MacBook').",
    )


class WebAuthnCredentialDeleteResponse(_BaseSchema):
    """Response for DELETE /auth/webauthn/credentials/{id}."""
    deleted_id: uuid.UUID
    message: str


# ================================================================== #
#  SESSION MANAGEMENT SCHEMAS                                        #
# ================================================================== #

class SessionRead(_BaseSchema):
    """
    Public representation of an active session (refresh token family).
    FIX: Enables users to see and revoke their active sessions.
    """
    family_id: uuid.UUID
    created_at: datetime
    last_used_at: datetime | None
    revoked: bool
    expires_at: datetime


class SessionsListResponse(_BaseSchema):
    """Response for GET /auth/sessions."""
    sessions: list[SessionRead]
    total: int


class SessionRevokeResponse(_BaseSchema):
    """Response for DELETE /auth/sessions/{family_id}."""
    revoked_family_id: uuid.UUID
    message: str


# ================================================================== #
#  V2: FARE ESTIMATION SCHEMAS                                        #
# ================================================================== #

class FareEstimateRequest(_BaseRequestSchema):
    service_id: uuid.UUID
    vehicle_sizes: list[VehicleSize] = Field(..., min_length=1)
    client_lat: float = Field(..., ge=-90.0, le=90.0)
    client_lng: float = Field(..., ge=-180.0, le=180.0)


class FareEstimateResponse(_BaseSchema):
    fare_token: str
    base_price_cents: int
    surge_multiplier: Decimal
    estimated_price_cents: int
    nearby_detailers_count: int
    expires_at: datetime

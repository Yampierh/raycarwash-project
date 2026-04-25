# app/schemas/schemas.py
# COMPATIBILITY SHIM — re-exports all schemas from domain packages.
# Existing routers using `from app.schemas.schemas import X` continue to work unchanged.

from shared.schemas import (  # noqa: F401
    _BaseSchema, _BaseRequestSchema, PositiveCents,
    _validate_password_strength,
    HealthResponse, ErrorDetail, PaginatedResponse,
)
from domains.auth.schemas import (  # noqa: F401
    Token, RegisterRequest, LoginRequest, LoginResponse, LogoutRequest,
    CheckEmailRequest, CheckEmailResponse,
    IdentifierRequest, IdentifierResponse,
    VerifyRequest, VerifyResponse,
    CompleteProfileRequest, TokenData,
    GoogleLoginRequest, AppleLoginRequest, SocialAuthResponse,
    PasswordResetRequest, PasswordResetConfirmRequest,
    PasswordResetConfirmResponse, PasswordResetResponse,
    WebAuthnRegisterBeginResponse, WebAuthnRegisterCompleteRequest, WebAuthnRegisterCompleteResponse,
    WebAuthnAuthBeginRequest, WebAuthnAuthBeginResponse, WebAuthnAuthCompleteRequest,
    WebAuthnCredentialRead, WebAuthnCredentialsListResponse,
    WebAuthnCredentialRenameRequest, WebAuthnCredentialDeleteResponse,
    SessionRead, SessionsListResponse, SessionRevokeResponse,
)
from domains.users.schemas import UserCreate, UserRead, UserUpdate  # noqa: F401
from domains.vehicles.schemas import VehicleCreate, VehicleRead  # noqa: F401
from domains.appointments.schemas import (  # noqa: F401
    AppointmentVehicleCreate, AppointmentCreate,
    _VehicleSnap, AppointmentVehicleRead, AppointmentAddonRead,
    _ClientSnap, _DetailerSnap, AppointmentRead, AppointmentStatusUpdate,
    RefundResponse,
)
from domains.services_catalog.schemas import ServiceRead, AddonRead  # noqa: F401
from domains.matching.schemas import (  # noqa: F401
    TimeSlotRead, AvailabilityRequest,
    LocationUpdate, LocationResponse, MatchingResult,
)
from domains.providers.schemas import (  # noqa: F401
    WorkingHoursDay, ProviderProfileRead, DetailerMeRead,
    ProviderProfileCreate, ProviderProfileUpdate,
    DetailerPublicRead, DetailerServiceRead, DetailerServiceUpdate, DetailerStatusUpdate,
)
from domains.reviews.schemas import ReviewCreate, ReviewRead  # noqa: F401
from domains.payments.schemas import (  # noqa: F401
    PaymentIntentRequest, PaymentIntentResponse,
    FareEstimateRequest, FareEstimateResponse,
)
from domains.audit.schemas import AuditLogRead  # noqa: F401

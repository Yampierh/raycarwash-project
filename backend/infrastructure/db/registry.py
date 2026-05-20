"""
infrastructure/db/registry.py

Imports ALL domain models so SQLAlchemy's mapper registry can resolve
every string-based relationship reference before any query runs.

Call `import infrastructure.db.registry` once at startup — in main.py's
lifespan or at module level — before create_all() or any ORM query.

WHY a separate file (not __init__.py)?
  Domain model files do `from infrastructure.db.base import Base`.
  If __init__.py imported all domains, Python would hit a circular
  initialization: domain → infrastructure.db → __init__ → domain.
  A separate registry.py avoids that cycle entirely.
"""

from domains.auth.models import (  # noqa: F401
    Permission, Role, RolePermission, UserRoleAssociation,
    RefreshToken, PasswordResetToken,
    WebAuthnCredential, AuthProvider,
    UserLoginHistory, Session,
)
from domains.auth.totp_credential import TotpCredential  # noqa: F401
from domains.users.pending_contact_change import PendingContactChange  # noqa: F401
from domains.users.user_address import UserAddress  # noqa: F401
from domains.users.payment_method import PaymentMethod  # noqa: F401
from domains.users.client_favorite import ClientFavorite  # noqa: F401
from domains.users.document import Document, DocumentType  # noqa: F401
from domains.users.models import User, ClientProfile, OnboardingStatus  # noqa: F401
from domains.providers.models import ProviderProfile, ProviderAvailabilityException  # noqa: F401
from domains.providers.portfolio_photo import ProviderPortfolioPhoto  # noqa: F401
from domains.providers.achievement import ProviderAchievement  # noqa: F401
from domains.vehicles.models import Vehicle, VehicleSize  # noqa: F401
from domains.vehicles.vehicle_photo import VehiclePhoto  # noqa: F401
from domains.appointments.models import (  # noqa: F401
    Appointment, AppointmentVehicle, AppointmentAddon, AppointmentAssignment,
    AppointmentStatusHistory, AppointmentCancellation,
    AppointmentStatus, AssignmentStatus, TERMINAL_STATUSES, VALID_TRANSITIONS,
)
from domains.services_catalog.models import (  # noqa: F401
    Service, ServiceCategoryTable, Addon,
    ProviderService, ProviderServiceCategory, DetailerService,
    Specialty, ProviderSpecialty, ServiceCategory,
)
from domains.reviews.models import Review  # noqa: F401
from domains.payments.models import (  # noqa: F401
    FareEstimate, ProcessedWebhook,
    PaymentLedger, LedgerSeal, LedgerRevision, Refund, ProviderPayout,
)
from domains.audit.models import AuditLog, AuditAction  # noqa: F401
from domains.notifications.models import DeviceToken, DevicePlatform  # noqa: F401
from domains.public.models import (  # noqa: F401
    Testimonial, TestimonialRole,
    FaqItem, FaqCategory,
    CoverageZone, CoverageZip,
    ContactSubmission,
    WaitlistEntry, WaitlistRole,
)
from domains.locations.models import City, CityStatus  # noqa: F401
from domains.credits.models import CustomerCredit  # noqa: F401
from infrastructure.db.base import Base  # noqa: F401

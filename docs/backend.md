# Backend — Architecture & Developer Guide

Stack: **FastAPI · SQLAlchemy async · PostgreSQL 14+ · Python 3.13**

---

## Domain structure (DDD-lite)

Each domain owns its models, schemas, repository, service, and router.
No cross-domain shims — imports go directly between `domains/X` and `domains/Y`.

```
backend/
├── main.py                     # Composition root — lifespan, middleware, health
├── api/router.py               # Aggregates all domain routers into one APIRouter
│
├── domains/
│   ├── auth/                   # RS256 JWT, OAuth2 social, WebAuthn passkeys, lockout
│   │   ├── models.py           # Role, Permission, RolePermission, RefreshToken, PasswordResetToken, WebAuthnCredential, EmailVerificationToken
│   │   ├── schemas.py          # LoginResponse, RegisterRequest, TokenResponse, …
│   │   ├── service.py          # AuthService, get_current_user, require_role
│   │   ├── routers/            # Split by concern (replaces old router.py)
│   │   │   ├── __init__.py     # Assembles auth_router from sub-routers
│   │   │   ├── core.py         # register, login, logout, token, refresh, me, update, identify, verify, complete-profile
│   │   │   ├── social.py       # /auth/google, /auth/apple
│   │   │   ├── webauthn.py     # /auth/webauthn/* — passkey register/auth + CRUD
│   │   │   ├── sessions.py     # /auth/sessions list + revoke
│   │   │   ├── password.py     # /auth/password-reset, /password-reset/confirm
│   │   │   └── email_verification.py  # /auth/email/verify, /email/resend-verification
│   │   ├── wellknown_router.py # /.well-known/apple-app-site-association + /.well-known/jwks.json
│   │   ├── refresh_token_repository.py
│   │   ├── password_reset_token_repository.py
│   │   ├── email_verification_token_repository.py
│   │   ├── webauthn_repository.py
│   │   ├── auth_provider_repository.py
│   │   └── webauthn_service.py
│   │
│   ├── admin/                  # Admin dashboard API — /api/v1/admin/*
│   │   ├── repository.py       # AdminRepository — users, roles, permissions, appointments, verifications, ledger
│   │   ├── router.py           # 22 endpoints behind require_role("admin")
│   │   └── schemas.py          # AdminStats, AdminUserRead, AdminAppointmentDetail, AdminLedgerEntryRead, …
│   │
│   ├── users/                  # Registration, profiles, onboarding, sub-resources
│   │   ├── models.py           # User, ClientProfile, OnboardingStatus
│   │   ├── schemas.py          # UserCreate, UserRead, UserUpdate
│   │   ├── repository.py       # UserRepository
│   │   ├── router.py           # POST /api/v1/users
│   │   ├── avatar_router.py, address_router.py, payment_method_router.py
│   │   ├── favorites_router.py, vehicle_photo_router.py
│   │   ├── client_preferences_router.py, active_role_router.py
│   │   ├── contact_change_router.py
│   │   ├── provider_profile_router.py, provider_portfolio_router.py
│   │   ├── provider_documents_router.py, provider_verification_router.py
│   │
│   ├── providers/              # Detailer profiles, Stripe Identity
│   │   ├── models.py           # ProviderProfile
│   │   ├── schemas.py          # DetailerMeRead, ProviderProfileCreate, …
│   │   ├── repository.py       # ProviderRepository
│   │   ├── router.py           # /api/v1/detailers/*
│   │   └── verification_router.py  # /api/v1/detailers/verification/*
│   │
│   ├── vehicles/               # Vehicle CRUD, NHTSA VIN lookup
│   │   ├── models.py           # Vehicle, VehicleSize
│   │   ├── schemas.py          # VehicleCreate, VehicleRead
│   │   ├── repository.py
│   │   └── router.py           # /api/v1/vehicles/*
│   │
│   ├── appointments/           # FSM booking lifecycle, availability slots
│   │   ├── models.py           # Appointment, AppointmentVehicle, AppointmentAddon, FSM constants
│   │   ├── schemas.py          # AppointmentCreate, AppointmentRead, AppointmentStatusUpdate
│   │   ├── repository.py       # advisory locks, overlap check
│   │   ├── service.py          # AppointmentService — slots, create, transition_status
│   │   └── router.py           # /api/v1/appointments/*
│   │
│   ├── matching/               # H3 geospatial + scoring engine
│   │   ├── schemas.py          # MatchingResult, TimeSlotRead, LocationUpdate
│   │   ├── service.py          # assign(), score(), haversine
│   │   └── router.py           # GET /api/v1/matching
│   │
│   ├── payments/               # Stripe intents, webhooks, fare estimation, ledger
│   │   ├── models.py           # FareEstimate, ProcessedWebhook, PaymentLedger, LedgerSeal
│   │   ├── service.py          # PaymentService
│   │   ├── service_v2.py       # PaymentCoordinator (append-only ledger)
│   │   ├── fare_service.py     # calculate_surge, generate/verify fare token
│   │   ├── repository.py       # LedgerRepository
│   │   ├── router.py           # POST /api/v1/payments/create-intent
│   │   ├── webhook_router.py   # POST /webhooks/stripe
│   │   ├── fare_router.py      # POST /api/v1/fares/estimate
│   │   └── rides_router.py     # POST /api/v1/rides/request, accept, decline
│   │
│   ├── services_catalog/       # Service + addon catalogue
│   │   ├── models.py           # Service, Addon, ServiceCategory, Specialty
│   │   ├── repository.py       # ServiceRepository, AddonRepository
│   │   └── router.py           # /api/v1/services, /api/v1/addons
│   │
│   ├── reviews/                # Rating aggregation
│   │   ├── models.py           # Review
│   │   ├── repository.py       # atomic rating aggregate update
│   │   ├── service.py
│   │   └── router.py           # /api/v1/reviews
│   │
│   ├── notifications/          # Push notifications via Expo Push API
│   │   ├── models.py           # DeviceToken
│   │   ├── schemas.py
│   │   ├── repository.py       # DeviceTokenRepository (upsert, delete_by_token)
│   │   ├── service.py          # Expo Push API client
│   │   ├── handlers.py         # Event bus handlers (appointment.* → push)
│   │   └── router.py           # POST/DELETE /api/v1/notifications/device-token
│   │
│   ├── realtime/               # Redis Pub/Sub WebSocket rooms
│   │   ├── connection_manager.py  # ConnectionManager
│   │   └── router.py           # WS /ws/appointments/{id}, /ws/user/{id}
│   │
│   ├── audit/                  # Append-only audit log
│   │   ├── models.py           # AuditLog, AuditAction
│   │   └── repository.py       # AuditRepository
│   │
│   ├── credits/                # Customer comp credit system
│   │   └── models.py           # CreditGrant, CreditBalance
│   │
│   ├── identity/               # Identity verification state tracking
│   │   └── models.py           # IdentityVerification
│   │
│   ├── locations/              # City management, coverage zones
│   │   ├── models.py           # City, ServiceZipCode
│   │   ├── repository.py       # CityRepository
│   │   └── router.py           # /api/v1/locations/*
│   │
│   ├── onboarding/             # Multi-step onboarding flow
│   │   ├── models.py           # OnboardingStep, OnboardingProgress
│   │   └── router.py           # /api/v1/onboarding/advance
│   │
│   ├── promos/                 # Promo code system
│   │   ├── models.py           # PromoCode, PromoRedemption
│   │   ├── service.py          # PromoService — validate, apply, preview
│   │   └── router.py           # /api/v1/promo/*
│   │
│   └── public/                 # Public marketing content (no auth)
│       ├── models.py           # Testimonial, FAQEntry, CoverageArea
│       ├── repository.py
│       └── router.py           # /api/v1/public/*
│
├── infrastructure/             # Adapters for external systems
│   ├── db/
│   │   ├── base.py             # Base, TimestampMixin, _get_encryption_key
│   │   ├── session.py          # engine, AsyncSessionLocal, get_db
│   │   └── registry.py         # Imports all domain models → forces mapper resolution
│   ├── redis/client.py         # init_redis_pool (fakeredis fallback in dev)
│   ├── email/service.py        # EmailService — SMTP transactional email
│   ├── nhtsa/client.py         # lookup_vin_data, map_body_to_size
│   ├── h3/client.py            # H3 geospatial indexing, find_nearby_detailers
│   ├── stripe/                 # Stripe SDK wrappers + webhook verification
│   ├── geocoding/              # NominatimAdapter (dev) → GoogleMapsGeocodingAdapter (prod)
│   ├── sms/                    # ConsoleSmsAdapter (dev) → TwilioSmsAdapter (prod)
│   ├── storage/                # LocalStorageAdapter (dev) → S3StorageAdapter (prod)
│   └── auth/                   # OAuth provider configs, HMAC phone hashing
│
├── shared/schemas.py           # _BaseSchema, _BaseRequestSchema, PaginatedResponse, ErrorDetail
├── events/bus.py               # In-process async event bus (no Kafka)
│
├── workers/                    # Async background workers (lifespan + RQ)
│   ├── location_worker.py      # GPS stream → H3 index + WS broadcast
│   ├── assignment_worker.py    # Auto-assignment engine (Redis Stream)
│   ├── ledger_seal_worker.py   # Daily SHA-256 seal of the payment ledger
│   ├── token_cleanup_worker.py # Expired token GC (24h interval)
│   ├── session_cleanup_worker.py  # Daily session GC (Plan 23 F8)
│   ├── achievement_evaluator.py   # RQ worker: badge/level evaluation
│   ├── document_expiry_checker.py # RQ worker: document expiration checks
│   ├── login_history_purger.py    # RQ worker: old login history cleanup
│   ├── pending_contact_cleanup.py # RQ worker: stale contact changes
│   └── schedule.py             # RQ scheduler configuration
│
└── app/                        # Stable infrastructure (not domain code)
    ├── core/                   # config.py, security.py, limiter.py, logging_context.py
    └── db/                     # seed.py, seed_rbac.py, seed_promos.py, seed_public.py, detailer_seed.py
```

---

## Import rules

- `domains/X` → may import from `domains/Y` directly (no shims)
- `domains/X` → may import from `infrastructure/` and `shared/`
- `workers/` → imports from `domains/` and `infrastructure/`
- `app/core/` → imported by anyone (config, security, limiter are global)
- `main.py` → imports from `api/`, `infrastructure/`, `workers/`, `app/core/`, `app/db/`

---

## Startup sequence (lifespan)

1. Register event bus handlers (push-notification dispatchers in `domains/notifications/handlers.py`)
2. `create_all()` — create tables idempotently (production: use `alembic upgrade head`)
3. Seed RBAC roles + permissions + **default admin user** (`admin@raycarwash.com` / `Admin1234!`, only if missing)
4. Seed service categories + specialties + service catalogue (13 services with per-size prices) + addons (15)
5. Seed test detailers (6 Fort Wayne detailers)
6. Seed public content (testimonials, FAQ, coverage zones)
7. Seed promo codes (including NEW10 welcome credit)
8. Seed cities + service ZIP codes
9. Init Redis pool (real Redis or fakeredis fallback)
10. Init `ConnectionManager` WebSocket manager
11. Start background workers (location, assignment, ledger seal, token cleanup, session cleanup)

---

## Middleware stack

Execution order (defined in `main.py`):

| Order | Middleware | Purpose |
|---|---|---|
| 1 | RequestIDMiddleware | Generate unique `X-Request-ID` header |
| 2 | StructuredLoggingMiddleware | Structured JSON logging with request-ID propagation |
| 3 | AuditContextMiddleware | Extract IP / UA / request-id into context |
| 4 | IdempotencyMiddleware | Redis-backed idempotency-key (v1 legacy + v2 user-scoped) |
| 5 | CORS | Allow frontend origin + credentials |
| 6 | Request size limit | 413 if > 5 MB (Stripe webhooks exempted via `webhook_router` prefix) |
| 7 | Process time header | `X-Process-Time-Ms` on every response |
| 8 | Rate limiter (slowapi) | Per-endpoint per-IP limits |

---

## Key patterns

**Repository pattern** — no SQL in routers or services; only in `*_repository.py`.

**Advisory locks** — `pg_advisory_xact_lock(detailer_uuid)` inside appointment creation. Prevents double-booking race conditions.

**Soft deletes** — `is_deleted + deleted_at` on every entity. Always filter `Model.is_deleted == False`.

**PII encryption** — `full_name`, `phone_number` use `EncryptedType` keyed from `ENCRYPTION_KEY` (separate from JWT key).

**VehicleSize is never stored** — derived from `body_class` at runtime via `map_body_to_size()`. Never add a `size` column to Vehicle.

**Prices are integer cents** — always. Display: `price_cents / 100`. Never floats.

**estimated_price is immutable** — set once at appointment creation. `actual_price` is set on COMPLETED.

**Timestamps are UTC** — convert to detailer's IANA timezone only for display and availability logic.

**Schema bases**:
- `_BaseSchema` — response schemas, `from_attributes=True`
- `_BaseRequestSchema` — request schemas, JSON-only

---

## Pricing formula

```
vehicle_price = ceil(service.base_price_cents × SIZE_MULTIPLIER[vehicle.size])

SIZE_MULTIPLIERS = { small: 1.0, medium: 1.2, large: 1.5, xl: 2.0 }

total = Σ vehicle_price + Σ addon.price_cents
```

Per-size prices are precomputed at seed time (`price_small`, `price_medium`, `price_large`, `price_xl`).
If a detailer has `custom_price_cents` for a service, it replaces `base_price_cents`.

---

## Appointment state machine

```
PENDING
  ├→ CONFIRMED              (detailer / admin)
  ├→ CANCELLED_BY_CLIENT    (client / admin)
  └→ CANCELLED_BY_DETAILER  (detailer / admin)

CONFIRMED
  ├→ ARRIVED                (detailer / admin)
  ├→ IN_PROGRESS            (detailer / admin)
  ├→ CANCELLED_BY_CLIENT    (client / admin)
  └→ CANCELLED_BY_DETAILER  (detailer / admin)

ARRIVED → IN_PROGRESS       (detailer / admin)

IN_PROGRESS
  ├→ COMPLETED              (detailer / admin)
  └→ NO_SHOW                (detailer / admin)

Terminal: COMPLETED · CANCELLED_BY_CLIENT · CANCELLED_BY_DETAILER · NO_SHOW
```

Auto-stamped: `arrived_at` on ARRIVED · `started_at` on IN_PROGRESS · `completed_at` on COMPLETED.

---

## Cancellation refund policy

| Time before appointment | Refund |
|---|---|
| ≥ 24 hours | 100% |
| 2–24 hours | 50% |
| < 2 hours | 0% |

Configurable: `CANCELLATION_FULL_REFUND_HOURS`, `CANCELLATION_PARTIAL_REFUND_HOURS`, `CANCELLATION_PARTIAL_REFUND_PERCENT`.

---

## Availability algorithm

1. Load detailer's `working_hours` JSONB → convert HH:MM to UTC using detailer's IANA timezone
2. Fetch all active (non-terminal) appointments for the day
3. Build occupied intervals: `(scheduled_time, travel_buffer_end_time)`
4. Generate 30-min display slots within working hours
5. Each slot is `unavailable` if: in the past · service window overruns day end · overlaps any occupied interval
6. Return all slots (available + unavailable) for calendar rendering

---

## Authentication

### Identifier-first flow

```
POST /auth/identify   { identifier }
  → { is_new_user, available_methods }

POST /auth/verify     { identifier, password }   or   { identifier, provider, token }
  → existing user: { access_token, refresh_token }
  → new user:      { onboarding_token, next_step: "complete_profile" }

PUT /auth/complete-profile   Bearer <onboarding_token>
  { full_name, phone_number, role: "client"|"detailer" }
  → { access_token, refresh_token }
```

### Token types

| Type | TTL | Signing | Scope |
|---|---|---|---|
| `access` | 30 min | RS256 (JWKS-verifiable) | All protected endpoints |
| `refresh` | 7 days | Opaque, stored as SHA-256 hash (single-use, family-revocation) | `POST /auth/refresh` only |
| `onboarding` | 30 min | RS256 | `PUT /auth/complete-profile` only |
| `email_verification` | 24 h | Stateful (DB-backed, single-use) | `POST /auth/email/verify` only |
| WebAuthn challenges | 5 min | Stateful (Redis) | One-shot, consumed on verify |

JWT signing: **RS256 asymmetric**. Private key in `JWT_PRIVATE_KEY` signs; any service can verify via `GET /.well-known/jwks.json` (public key set, no shared secret).

### Security properties

- JWT `type` claim prevents cross-type token reuse
- bcrypt via passlib
- `dummy_verify()` — timing-safe even for nonexistent users
- `PUT /auth/complete-profile` returns 403 if `onboarding_status == "completed"` — prevents post-login role escalation to detailer without KYC
- Rate limits: 10/min on identify/verify/token · 5/min on refresh/social
- SQL injection protected via SQLAlchemy ORM (parameterized)
- Stripe webhook HMAC-SHA256 (`Stripe-Signature`)
- Request body limit: 5 MB (Stripe webhooks exempt)
- PII encrypted at rest

---

## Running the backend

```bash
cd backend

# Install deps
pip install -r requirements.txt

# DB migrations (production)
alembic upgrade head

# Start (dev — auto-seeds on startup)
python -m uvicorn main:app --reload --port 8000
```

Services after startup:
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/health`

---

## Tests

```bash
cd backend
python -m pytest tests/ -q
python -m pytest tests/test_auth.py tests/test_appointments.py -q  # core flow
```

| Suite | Tests | Status |
|---|---|---|---|
| `test_auth.py` | 72 | ✅ all pass (incl. role-escalation security test) |
| `test_appointments.py` | 22 | ✅ all pass |
| `test_user_flows.py` | 16 | ✅ all pass (client + detailer registration guard rails) |
| `test_admin.py` | 28 | ✅ all pass (users / roles / permissions endpoints) |
| `test_detailers.py` | 28 | ⚠️ edge cases (profile fixture) |
| `test_matching.py` | 10 | ⚠️ requires real Redis for spatial |
| `test_vehicles.py` | 17 | ⚠️ body_class / onboarding edge cases |

**Total**: 618 tests across 49 files. Standard green suite (excluding ⚠️ files): **563/563**.

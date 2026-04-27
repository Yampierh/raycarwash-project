# AGENTS.md — RayCarWash project context

## Project overview

**RayCarWash** is a mobile vehicle services marketplace (Airbnb/Uber model) connecting clients with mobile service providers.

- **Current vertical**: Car detailing (getting it fully functional before expanding)
- **Planned**: Multiservice — mechanics, accessories, inspections
- **Target market**: Fort Wayne, IN
- **Backend**: FastAPI + PostgreSQL (async-first, repository pattern)
- **Frontend**: React Native with Expo
- **Architecture**: Monorepo — root `package.json` orchestrates both projects

---

## Quick commands

```bash
npm run install        # Install npm dependencies (frontend)
npm run install-deps   # Create Python venv + install backend deps
npm run dev            # Start both backend and frontend in parallel
npm run dev:backend    # FastAPI on port 8000
npm run dev:frontend   # Expo on port 8081

cd backend && alembic upgrade head   # Run DB migrations
cd backend && pytest -v              # Run tests
```

---

## Project structure

```
raycarwash-project/
├── package.json                    # Root orchestrator (concurrently)
├── backend/
│   ├── main.py                     # App factory, router registration, lifespan hooks
│   ├── requirements.txt
│   └── app/
│       ├── core/                   # config.py (Pydantic settings), limiter.py (slowapi)
│       ├── db/                     # session.py (engine/pool), seed.py, detailer_seed.py
│       ├── models/models.py        # All SQLAlchemy ORM models
│       ├── schemas/schemas.py      # All Pydantic v2 schemas
│       ├── repositories/           # Data access layer (8 repos)
│       ├── services/               # Business logic layer
│       ├── routers/                # FastAPI route handlers (10 routers)
│       └── ws/                     # ConnectionManager + WebSocket router
└── frontend/
    └── src/
        ├── navigation/types.ts     # React Navigation param lists
        ├── screens/                # 17 screen components (see list below)
        ├── services/               # 11 API service files
        ├── hooks/                  # useAppointmentSocket
        ├── store/                  # authStore (Zustand — sync token for WS)
        ├── theme/
        └── utils/
```

---

## Environment variables

### Backend (`backend/.env`)

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/raycarwash
SECRET_KEY=<32+ char secret>
DEBUG=true

# Optional
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
SMTP_ENABLED=false
GOOGLE_CLIENT_ID=
APPLE_BUNDLE_ID=com.raycarwash.app
```

### Frontend (`frontend/.env.local`)

```
EXPO_PUBLIC_API_URL=http://localhost:8000
```

For physical device testing, replace `localhost` with your machine's LAN IP.

---

## Database

- **PostgreSQL 14+** with `asyncpg` driver
- **Alembic** for migrations: `cd backend && alembic upgrade head`
- **Auto-seeded on startup**: services catalog, addons, RBAC roles, test detailers
- **Soft deletes** everywhere: `is_deleted + deleted_at` columns
- **Advisory locks**: `pg_advisory_xact_lock()` prevents double-booking race conditions
- **PII encrypted at rest**: `full_name`, `phone_number` use `EncryptedType` with `SECRET_KEY`

---

## API reference

Base URL: `http://localhost:8000`
Docs: `/docs` (Swagger) · `/redoc` · `/health`

### Auth (`/auth`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/identify` | — | Step 1: email or phone → returns `is_new_user` + available methods |
| POST | `/auth/verify` | — | Step 2: password or social token → returns tokens or `registration_token` |
| PUT | `/auth/complete-profile` | Registration token | Step 3 (new users only): name + phone → returns full tokens |
| POST | `/auth/refresh` | — | Refresh token rotation (5 req/min) |
| GET | `/auth/me` | Bearer | Current user profile |
| PUT | `/auth/update` | Bearer | Update profile fields |
| POST | `/auth/google` | — | Google OAuth token exchange |
| POST | `/auth/apple` | — | Apple identity token exchange |
| POST | `/auth/password-reset` | — | Request password reset email |

**Token types**:
- `access`: 30 min · used in `Authorization: Bearer` header
- `refresh`: 7 days · used in `POST /auth/refresh?refresh_token=...`
- `registration`: 30 min · temporary token for `/auth/complete-profile` only

### Vehicles (`/api/v1/vehicles`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/vehicles` | Bearer(client) | Create vehicle |
| GET | `/api/v1/vehicles` | Bearer(client) | List own vehicles |
| GET | `/api/v1/vehicles/{id}` | Bearer(client) | Vehicle detail |
| PUT | `/api/v1/vehicles/{id}` | Bearer(client) | Update vehicle |
| DELETE | `/api/v1/vehicles/{id}` | Bearer(client) | Soft delete |
| GET | `/api/v1/vehicles/lookup/{vin}` | Bearer | NHTSA VIN decode |

### Services and addons

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/services` | — | List active services (public) |
| GET | `/api/v1/services/{id}` | — | Service detail |
| GET | `/api/v1/addons` | — | List active addons (public) |

### Detailers (`/api/v1/detailers`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/detailers` | — | Search detailers by geo + filters |
| GET | `/api/v1/detailers/me` | Bearer(detailer) | Own profile + stats |
| PUT | `/api/v1/detailers/me` | Bearer(detailer) | Upsert own profile (bio, zone, schedule) |
| PATCH | `/api/v1/detailers/me/status` | Bearer(detailer) | Toggle `is_accepting_bookings` |
| GET | `/api/v1/detailers/me/services` | Bearer(detailer) | Catalog services with detailer toggle state |
| PATCH | `/api/v1/detailers/me/services/{id}` | Bearer(detailer) | Toggle service on/off + optional custom price |
| GET | `/api/v1/detailers/{id}/availability` | — | Available slots for a date |
| POST | `/api/v1/detailers/location` | Bearer(detailer) | GPS location update |
| GET | `/api/v1/detailers/{id}/profile` | — | Public detailer profile |

### Matching (`/api/v1/matching`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/matching` | Bearer(client) | Ranked detailers + available slots |

Query params: `lat`, `lng`, `date`, `service_id`, `vehicle_sizes` (comma-sep), `addon_ids`, `radius_miles`

### Appointments (`/api/v1/appointments`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/appointments` | Bearer(client) | Create booking (single or multi-vehicle + addons) |
| GET | `/api/v1/appointments` | Bearer | List own appointments (paginated) |
| GET | `/api/v1/appointments/{id}` | Bearer | Appointment detail |
| PATCH | `/api/v1/appointments/{id}/status` | Bearer | State machine transition |

### Payments and reviews

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/payments/create-intent` | Bearer(client) | Create Stripe PaymentIntent |
| POST | `/api/v1/reviews` | Bearer(client) | Submit review (appointment must be COMPLETED) |
| GET | `/api/v1/reviews/detailer/{id}` | — | List detailer reviews (paginated) |
| POST | `/webhooks/stripe` | Stripe-Signature | Stripe event handler |

### WebSocket

```
WS /ws/appointments/{id}?token=<access_token>
```

JWT passed as query param (WS connections cannot send headers after handshake).

**Close codes**: `4001` unauthorized · `4003` forbidden · `4004` not found

**Client → server**: `{ type: "ping" }` · `{ type: "location_update", lat, lng }` (detailer only)

**Server → client**: `{ type: "pong" }` · `{ type: "status_change", status, appointment_id, ts }` · `{ type: "location_update", lat, lng, ts }`

---

## Data models

### Key models

**User** — Unified identity. Has `user_roles` (RBAC), optional `client_profile` and `detailer_profile`. PII encrypted at rest.

**DetailerProfile** — 1:1 with User. Fields: `bio`, `years_of_experience`, `working_hours` (JSONB), `service_radius_miles`, `timezone` (IANA), `current_lat/lng`, `is_accepting_bookings`, `average_rating`, `total_reviews`.

**Vehicle** — Belongs to User. `body_class` from NHTSA determines `VehicleSize` at runtime — never stored. Fields: `make`, `model`, `year`, `vin`, `body_class`, `color`, `license_plate`.

**Service** — Catalog item. Prices precomputed per size: `price_small`, `price_medium`, `price_large`, `price_xl` (cents). Duration precomputed per size too.

**Addon** — Optional extras. Flat `price_cents` + `duration_minutes`.

**Appointment** — Core booking. Links client, detailer, service, vehicles, addons. Has `estimated_price` (immutable after creation) and `actual_price` (set on COMPLETED). Auto-stamps: `arrived_at`, `started_at`, `completed_at`.

**AppointmentVehicle / AppointmentAddon** — Multi-vehicle/addon support. Snapshot prices at booking time.

**Review** — 1:1 with Appointment. `rating` (1–5), `comment`. Updates `average_rating` + `total_reviews` on DetailerProfile.

**AuditLog** — Append-only event log.

---

## Business logic

### Pricing

```
vehicle_price = ceil(service.base_price_cents × SIZE_MULTIPLIER[vehicle_size])

SIZE_MULTIPLIERS = { small: 1.0, medium: 1.2, large: 1.5, xl: 2.0 }

total = Σ vehicle_price + Σ addon.price_cents
```

If detailer has `custom_price_cents` for a service, it replaces `base_price_cents`.

### Appointment state machine

```
PENDING
  ├→ CONFIRMED              (detailer / admin)
  ├→ CANCELLED_BY_CLIENT    (client / admin)
  └→ CANCELLED_BY_DETAILER  (detailer / admin)

CONFIRMED
  ├→ ARRIVED                (detailer / admin) — detailer reached client location
  ├→ IN_PROGRESS            (detailer / admin)
  ├→ CANCELLED_BY_CLIENT    (client / admin)
  └→ CANCELLED_BY_DETAILER  (detailer / admin)

ARRIVED
  └→ IN_PROGRESS            (detailer / admin)

IN_PROGRESS
  ├→ COMPLETED              (detailer / admin — requires actual_price)
  └→ NO_SHOW                (detailer / admin)

Terminal: COMPLETED · CANCELLED_BY_CLIENT · CANCELLED_BY_DETAILER · NO_SHOW
```

### Cancellation and refund policy

| Time before appointment | Refund |
|---|---|
| ≥ 24 hours | 100% |
| 2–24 hours | 50% |
| < 2 hours | 0% |

Configurable via env: `CANCELLATION_FULL_REFUND_HOURS`, `CANCELLATION_PARTIAL_REFUND_HOURS`, `CANCELLATION_PARTIAL_REFUND_PERCENT`.

### Availability calculation

1. Load detailer's `working_hours` JSONB in their IANA timezone
2. Fetch existing CONFIRMED/IN_PROGRESS appointments
3. Generate 30-min slots within working hours
4. Exclude slots overlapping appointments + 30-min travel buffer (`TRAVEL_BUFFER_MINUTES=30`)
5. Return `TimeSlotRead[]` with `{ start_time, end_time, is_available }`

### Smart matching sort

- No date specified (ASAP): `distance ASC, rating DESC`
- Date specified: `rating DESC, distance ASC`

---

## Authentication

### Identifier-first flow (Uber style)

```
1. POST /auth/identify   { identifier: "email or phone" }
   → { is_new_user, available_methods }

2. POST /auth/verify     { identifier, password } or { identifier, provider, token }
   → existing user:  { access_token, refresh_token, token_type }
   → new user:       { registration_token, needs_profile_completion: true }

3. PUT /auth/complete-profile   (new users only, Authorization: Bearer <registration_token>)
   { full_name, phone_number, role: "client"|"detailer" }
   → { access_token, refresh_token, token_type }

4. Frontend routes by role:
   → client:   Main tabs (Home, Vehicles, Profile)
   → detailer: DetailerOnboarding if no profile, else DetailerMain tabs
```

### Social login

- **Google**: verify via `googleapis.com/oauth2/v1/tokeninfo`, store `google_id`
- **Apple**: verify RS256 JWT via Apple JWKS, store `apple_id`
- Social-only users get an unusable bcrypt hash — never attempt password login for them

### Security

- JWT with `type` claim: `access` · `refresh` · `registration` (prevents cross-type reuse)
- bcrypt password hashing via passlib
- Timing-safe auth (`dummy_verify()`)
- Rate limit: 10 req/min on identify/verify/token · 5 req/min on refresh
- SQL injection protected via SQLAlchemy ORM (parameterized queries)
- Stripe webhook verified via HMAC-SHA256 (`Stripe-Signature`)
- Soft deletes preserve audit trail
- PII encrypted at rest (`EncryptedType`)
- Request body limit: 5 MB (bypassed for Stripe webhooks)
- CORS configurable via env

---

## Backend architecture

### Layer order

```
Router → Service → Repository → SQLAlchemy ORM → PostgreSQL
```

### Key patterns

- **Async-first**: all DB queries use `await session.execute(...)` — no sync I/O
- **Repository pattern**: no SQL in routers or services — only in `*_repository.py`
- **Advisory locks**: `SELECT pg_advisory_xact_lock(bigint)` keyed on detailer UUID in appointment creation
- **Soft deletes**: filter `Model.is_deleted == False` in every query
- **Fail-fast config**: Pydantic `Settings` raises `ValidationError` at startup if required env vars missing
- **Schema bases**: response schemas extend `_BaseSchema` (`from_attributes=True`); request schemas extend `_BaseRequestSchema` (JSON-only, model_config shared)

### Startup lifespan (main.py)

1. `create_all()` — create tables if not exist
2. Seed RBAC roles and permissions
3. Seed service catalog
4. Seed addons
5. Seed test detailers (`detailer_seed.py`)
6. Initialize `app.state.ws_manager = ConnectionManager()` (WebSocket room registry)
7. On shutdown: `engine.dispose()`

### Middleware stack

1. CORS (`http://localhost:8081` + configured origins)
2. Request size limiter (413 if > 5 MB)
3. Response time header injection (`X-Process-Time`)
4. Rate limiting (slowapi)

---

## Frontend architecture

### Screens (17 total)

| Category | Screens |
|---|---|
| Auth | `LoginScreen`, `RegisterScreen` |
| Client | `HomeScreen` (real-time WS status + detailer location) |
| Profile | `ProfileScreen`, `EditProfileScreen` |
| Vehicles | `VehiclesScreen`, `AddVehicleScreen`, `VehicleDetailScreen`, `SelectVehiclesScreen` |
| Booking | `BookingScreen`, `ScheduleScreen`, `DetailerSelectionScreen`, `BookingSummaryScreen` |
| Detailer | `DetailerOnboardingScreen`, `DetailerProfileScreen`, `DetailerServicesScreen`, `DetailerHomeScreen` (WS + GPS push) |

### Navigation structure

```
RootStack
├── LoginScreen / RegisterScreen
├── Main (client bottom tabs)
│   ├── HomeScreen
│   ├── VehiclesScreen
│   └── ProfileScreen
├── DetailerMain (detailer bottom tabs)
│   ├── DetailerHomeScreen
│   └── DetailerProfileScreen
└── Stack / Modal screens
    ├── AddVehicle, VehicleDetail, SelectVehicles
    ├── Booking, Schedule, DetailerSelection, BookingSummary
    ├── EditProfile
    └── DetailerOnboarding, DetailerServices
```

### Hooks

| File | Responsibility |
|---|---|
| `useAppointmentSocket.ts` | WS: auto-connect, exponential backoff (1s→30s), heartbeat ping every 30s, status + location callbacks |

### Store

| File | Responsibility |
|---|---|
| `store/authStore.ts` | Synchronous JWT + roles for WS. `saveToken`/`clearAuthTokens` sync the store. `app.tsx` hydrates at boot. |

### Services (11 total)

| File | Responsibility |
|---|---|
| `api.ts` | Axios instances (`authClient` for `/auth`, `apiClient` for `/api/v1`), JWT injection, 401 auto-refresh, `WS_BASE_URL` export |
| `auth.service.ts` | Identify, verify, complete-profile, refresh, social auth, password reset |
| `user.service.ts` | User profile management |
| `vehicle.service.ts` | Vehicle CRUD + VIN lookup |
| `service.service.ts` | Service catalog |
| `addon.service.ts` | Addon catalog |
| `appointment.service.ts` | Create, list, detail, patch status |
| `detailer.service.ts` | Search, availability, smart matching |
| `detailer-private.service.ts` | Authenticated detailer own profile |
| `payment.service.ts` | Stripe PaymentIntent creation |
| `review.service.ts` | Submit and fetch reviews |

### Two Axios clients — critical distinction

```
authClient  → base: /auth        (login, identify, verify, complete-profile, refresh, social)
apiClient   → base: /api/v1      (everything else)
```

Never use `apiClient` for auth endpoints — they live at `/auth`, not `/api/v1/auth`.

---

## Client onboarding flow

8 steps from install to first booking.

| Step | Screen | Blocking | API call |
|---|---|---|---|
| 1 | Splash — choose role | — | — |
| 2 | Identifier-first | — | `POST /auth/identify` |
| 3 | Create account | — | `POST /auth/verify` → `registration_token` |
| 4 | Complete profile (name + phone) | — | `PUT /auth/complete-profile` |
| 5 | Contact details (fill gap) | — | `PUT /auth/update` |
| 6 | Add vehicle | Yes — no vehicle = no booking | `POST /api/v1/vehicles` |
| 7 | Payment method | Yes — no payment = no booking | Stripe SDK |
| 8 | Preferences | No | `PUT /auth/update` |

Home unlocked after step 7.

---

## Detailer onboarding flow

10 steps from install to receiving jobs.

| Step | Screen | Blocking | API call |
|---|---|---|---|
| 1 | Splash — choose role | — | — |
| 2 | Identifier-first + create account | — | `POST /auth/identify` → `POST /auth/verify` → `PUT /auth/complete-profile` |
| 3 | Personal info + bio | No | `PUT /api/v1/detailers/me` |
| 4 | Service zone (city + radius) | No | `PUT /api/v1/detailers/me` |
| 5 | Services offered (toggle + custom price) | No | `PATCH /api/v1/detailers/me/services/{id}` |
| 6 | Weekly availability (days + hours + buffer) | No | `PUT /api/v1/detailers/me` |
| 7 | Identity verification | Yes — required to receive payments | Stripe Identity SDK |
| 8 | Bank account for payouts | Yes — required to receive payments | Stripe Connect |
| 9 | Activate availability | No | `PATCH /api/v1/detailers/me/status` |
| 10 | Detailer dashboard | — | — |

Steps 7 and 8 can be done in parallel or sequentially. Without both, detailer cannot receive payouts.

---

## Testing

```bash
cd backend
pytest          # all tests
pytest -v       # verbose
pytest tests/test_auth.py -v   # auth only (21 passing)
```

### Current test status

| Module | Tests | Status |
|---|---|---|
| Auth | 21 | ✅ All passing |
| Vehicles | 17 | ⚠️ 7 passing — 10 need fixes in test setup |
| Appointments | 18 | ❌ Blocked by missing `category` field in Service seed |
| Detailers | 18 | ❌ Same root cause |
| Matching | 10 | ❌ Same root cause |
| WebSocket | 0 | 📋 Not yet written — needs `pytest-asyncio` + mock WS |

**Root cause for ❌ tests**: `Service` model requires a `category` column (NOT NULL) that the test seed doesn't populate. Fix: add `ServiceCategory` model, add `category_id` FK to `Service`, update seed. This also enables multiservice architecture.

---

## Sprint roadmap

| Sprint | Status | Key features |
|---|---|---|
| 1 | ✅ Done | Project skeleton, DB setup |
| 2 | ✅ Done | Auth (identifier-first), vehicles, reviews |
| 3 | ✅ Done | Appointments, services, Stripe payments, state machine |
| 4 | ✅ Done | Detailer discovery, webhooks, refund policy, timezone scheduling, rate limiting, social login |
| 5 | ✅ Done | Addons, multi-vehicle bookings, smart matching, email service |
| 6 | 🔄 In progress | Security hardening, frontend contract fixes, push notifications, admin dashboard |
| 7 | 📋 Planned | Multiservice: `ServiceCategory` model, mechanic vertical, provider onboarding by type |

---

## Common pitfalls

- **VehicleSize is never stored** — derived from `body_class` at runtime via `body_class_to_size()`. Do not add a `size` column to Vehicle.
- **Prices are in cents** — always integer cents, never floats. Display: `price_cents / 100`.
- **Timestamps are UTC** — convert to detailer's IANA timezone only for display and availability logic.
- **Soft deletes** — always filter `Model.is_deleted == False`. Never hard-delete.
- **estimated_price is immutable** — set once at appointment creation, never update after.
- **Advisory lock scope** — per-detailer, transaction-scoped. Always inside `async with session.begin()`.
- **Social-only users** — have unusable bcrypt hash. Check `google_id`/`apple_id` before attempting password login.
- **Two Axios clients** — `authClient` for `/auth`, `apiClient` for `/api/v1`. Never mix.
- **WS auth** — JWT goes in query param (`?token=`), not in headers. WebSocket connections can't set headers after handshake.
- **CORS** — frontend on port 8081, backend allows this by default. Update `ALLOWED_ORIGINS` for production.
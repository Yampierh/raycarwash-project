# AGENTS.md — RayCarwash Project Context

## Project Overview

**RayCarwash** is a mobile car detailing marketplace (Airbnb/Uber model) connecting clients with mobile detailers.

- **Backend**: FastAPI + PostgreSQL (async-first, repository pattern)
- **Frontend**: React Native with Expo
- **Architecture**: Monorepo — root `package.json` orchestrates both projects

---

## Quick Commands

```bash
# Install all dependencies (frontend + backend npm packages)
npm run install

# Create Python venv and install backend deps
npm run install-deps

# Start both projects simultaneously
npm run dev

# Start only one
npm run dev:backend    # FastAPI on port 8000
npm run dev:frontend   # Expo on port 8081
```

---

## Project Structure

```text
raycarwash-project/
├── package.json                  # Root orchestrator (concurrently)
├── backend/
│   ├── main.py                   # App factory, router registration, lifespan hooks
│   ├── requirements.txt
│   ├── app/
│   │   ├── core/                 # config.py (Pydantic settings), limiter.py (slowapi)
│   │   ├── db/                   # session.py (engine/pool), seed.py, detailer_seed.py
│   │   ├── models/models.py      # All SQLAlchemy ORM models
│   │   ├── schemas/schemas.py    # All Pydantic v2 schemas
│   │   ├── repositories/         # Data access layer (8 repos)
│   │   ├── services/             # Business logic layer
│   │   └── routers/              # FastAPI route handlers (10 routers)
│   └── alembic/                  # Database migrations
└── frontend/
    └── src/
        ├── navigation/types.ts   # React Navigation param lists
        ├── screens/              # 17 screen components
        ├── services/             # 11 API service files
        ├── hooks/
        ├── theme/
        └── utils/
```

---

## Environment Variables

### Backend (`backend/.env`)

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/raycarwash
SECRET_KEY=<32+ char secret>
DEBUG=true

# Optional / defaults shown
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
SMTP_ENABLED=false
GOOGLE_CLIENT_ID=
APPLE_BUNDLE_ID=com.raycarwash.app
```

### Frontend (`frontend/.env.local`)

```env
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

---

## API Reference

All REST endpoints are at `http://localhost:8000/api/v1/` (except webhooks and health).

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health**: http://localhost:8000/health

### Auth (`/auth`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/identify` | — | Identifier-First: identify by email or phone |
| POST | `/auth/verify` | — | Identifier-First: verify credentials (password/social) |
| PUT | `/auth/complete-profile` | — | Complete profile after registration (temp token) |
| POST | `/auth/check-email` | — | Check if email exists (legacy) |
| POST | `/auth/token` | — | Email/password login (10 req/min rate limit) |
| POST | `/auth/refresh` | — | Refresh token rotation (5 req/min) |
| POST | `/auth/google` | — | Google OAuth token exchange |
| POST | `/auth/apple` | — | Apple identity token exchange |
| POST | `/auth/password-reset` | — | Email password reset |
| POST | `/users` | — | Register new user (legacy) |

### Vehicles (`/vehicles`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/vehicles` | Bearer(client) | Create vehicle (NHTSA VIN decode) |
| GET | `/vehicles` | Bearer(client) | List own vehicles |
| GET | `/vehicles/{id}` | Bearer(client) | Get vehicle detail |
| PUT | `/vehicles/{id}` | Bearer(client) | Update vehicle |
| DELETE | `/vehicles/{id}` | Bearer(client) | Soft delete |
| GET | `/vehicles/lookup/{vin}` | Bearer(client) | NHTSA VIN lookup |

### Services & Addons
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/services` | — | List active services (public) |
| GET | `/services/{id}` | — | Service detail |
| GET | `/addons` | — | List active addons (public) |

### Detailers (`/detailers`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/detailers` | — | Search detailers (geo-filter, pagination) |
| GET | `/detailers/me` | Bearer(detailer) | Own profile + stats |
| PUT | `/detailers/me` | Bearer(detailer) | Upsert own profile |
| PATCH | `/detailers/me/status` | Bearer(detailer) | Toggle is_accepting_bookings |
| GET | `/detailers/me/services` | Bearer(detailer) | Platform services with detailer state |
| PATCH | `/detailers/me/services/{id}` | Bearer(detailer) | Toggle service + custom price |
| GET | `/detailers/{id}/availability` | — | Available time slots for a date |
| POST | `/detailers/location` | Bearer(detailer) | GPS location update |

### Matching (Sprint 5)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/matching` | Bearer(client) | Smart matching: ranked detailers + slots |

Query params: `service_id`, `vehicle_sizes` (comma-separated), `lat`, `lng`, `date`, `addon_ids`, `radius_miles`

### Appointments (`/appointments`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/appointments` | Bearer(client) | Create booking (multi-vehicle + addons) |
| GET | `/appointments` | Bearer | List own appointments (paginated) |
| GET | `/appointments/{id}` | Bearer | Get appointment detail |
| PATCH | `/appointments/{id}/status` | Bearer | State machine status transition |

### Payments & Reviews
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/payments/create-intent` | Bearer(client) | Create Stripe PaymentIntent |
| POST | `/reviews` | Bearer(client) | Submit review (appointment must be COMPLETED) |
| GET | `/reviews/detailer/{id}` | — | List detailer reviews (paginated) |
| POST | `/webhooks/stripe` | Stripe-Signature | Stripe event handler |

---

## Data Models

### Key Models Summary

**User** — Unified identity. Has `user_roles` (RBAC), optional `client_profile` and `detailer_profile`. PII (`full_name`, `phone_number`) encrypted at rest.

**Role / Permission** — RBAC. Roles: `admin`, `detailer`, `client`. Permissions format: `action:resource` (e.g. `read:appointments`).

**Vehicle** — Belongs to User. `body_class` from NHTSA determines `VehicleSize` at runtime (never stored). Fields: `make`, `model`, `year`, `vin`, `body_class`, `color`, `license_plate`.

**DetailerProfile** — 1:1 with User. Key fields: `working_hours` (JSONB), `service_radius_miles`, `timezone` (IANA), `current_lat/lng`, `is_accepting_bookings`, `average_rating`.

**Service** — Catalog item. Prices precomputed per size: `price_small`, `price_medium`, `price_large`, `price_xl` (all in cents).

**Addon** — Optional extras. Flat `price_cents` + `duration_minutes`.

**Appointment** — Core booking. Links client, detailer, service, vehicles, addons. Has `estimated_price` (immutable after creation) and `actual_price` (set on COMPLETED). Timestamps: `started_at`, `completed_at`.

**AppointmentVehicle** / **AppointmentAddon** — Sprint 5 multi-vehicle/addon support. Snapshot prices at booking time.

**Review** — 1:1 with Appointment. `rating` (1–5), `comment`. Updates detailer's `average_rating` / `total_reviews`.

**AuditLog** — Append-only event log. `action` enum: `appointment_created`, `payment_captured`, `user_registered`, etc.

---

## Business Logic

### Pricing

```text
vehicle_price = ceil(service.base_price_cents × SIZE_MULTIPLIER[vehicle_size])
SIZE_MULTIPLIERS = { small: 1.0, medium: 1.2, large: 1.5, xl: 2.0 }
total_price = Σ vehicle_price + Σ addon.price_cents
```

If detailer has `custom_price_cents` for a service, it replaces `base_price_cents`.

### Duration

```text
vehicle_duration = service.duration_{size}_minutes (precomputed per size)
total_duration = Σ vehicle_duration + Σ addon.duration_minutes
```

### Appointment State Machine

```text
PENDING
  ├→ CONFIRMED            (detailer / admin)
  ├→ CANCELLED_BY_CLIENT  (client / admin)
  └→ CANCELLED_BY_DETAILER (detailer / admin)

CONFIRMED
  ├→ IN_PROGRESS          (detailer / admin)
  ├→ CANCELLED_BY_CLIENT  (client / admin)
  └→ CANCELLED_BY_DETAILER (detailer / admin)

IN_PROGRESS
  ├→ COMPLETED            (detailer / admin; requires actual_price)
  └→ NO_SHOW              (detailer / admin)

Terminal states: COMPLETED, CANCELLED_BY_CLIENT, CANCELLED_BY_DETAILER, NO_SHOW
```

### Cancellation / Refund Policy
| Time before appointment | Refund |
|------------------------|--------|
| ≥ 24 hours | 100% |
| 2 – 24 hours | 50% |
| < 2 hours | 0% |

Configurable via env: `CANCELLATION_FULL_REFUND_HOURS`, `CANCELLATION_PARTIAL_REFUND_HOURS`, `CANCELLATION_PARTIAL_REFUND_PERCENT`.

### Availability Calculation
1. Load detailer's `working_hours` JSONB in their IANA timezone
2. Fetch existing CONFIRMED/IN_PROGRESS appointments
3. Generate 30-min slots within working hours
4. Exclude slots overlapping appointments + 30-min travel buffer (`TRAVEL_BUFFER_MINUTES=30`)
5. Return `TimeSlotRead[]` with `{ start_time, end_time, is_available }`

### Smart Matching Sort Order
- **No `requested_time`** (ASAP): sort by `(distance ASC, rating DESC)`
- **With `date`**: sort by `(rating DESC, distance ASC)`

---

## Authentication

### JWT Flow
- **Access token**: 30 min, HS256, payload `{ sub, role, type:"access", iat, exp }`
- **Refresh token**: 7 days, payload `{ sub, role, type:"refresh", iat, exp }`
- **Registration token**: 30 min, payload `{ sub, role, type:"registration", iat, exp }` - temporary token for completing profile
- Token type discriminator prevents cross-type reuse
- Stored on client via `expo-secure-store`

### Identifier-First Auth (Estilo Uber)
El flujo de autenticación sigue el patrón Uber:
1. **Identify**: Usuario ingresa email o teléfono → Backend retorna métodos disponibles
2. **Verify**: Usuario verifica credenciales (password, social, OTP)
3. **CompleteProfile**: Si es nuevo usuario → completar perfil básico (nombre, teléfono)
4. **Redirect**: Según rol → Main (cliente) o DetailerOnboarding (detailer sin perfil)

### Social Login
- **Google**: verifies via `googleapis.com/oauth2/v1/tokeninfo`, stores `google_id`
- **Apple**: verifies RS256 JWT via Apple JWKS, stores `apple_id`

### RBAC
- Roles: `admin`, `detailer`, `client`
- Enforced via `require_role("detailer")` FastAPI dependency
- Check: `user.has_role("detailer")` or `user.has_permission("read:appointments")`

### Security
- PII encrypted at rest (`EncryptedType` with `SECRET_KEY`)
- bcrypt password hashing (social-only users get unusable hash)
- Rate limit: 10 req/min on `/auth/identify`, `/auth/verify`, `/auth/token`, 5 req/min on `/auth/refresh`
- Request body limit: 5 MB (configurable, bypassed for Stripe webhooks)
- Stripe webhooks verified via HMAC-SHA256 (`Stripe-Signature` header)
- Registration tokens expire in 30 minutes, scoped to profile completion only

---

## Backend Architecture

### Layer Order

```text
Router → Service → Repository → SQLAlchemy ORM → PostgreSQL
```

### Key Patterns
- **Async-first**: all DB queries use `await session.execute(...)`, all I/O non-blocking
- **Repository pattern**: no SQL in routers or services — only in `*_repository.py` files
- **Advisory locks**: `SELECT pg_advisory_xact_lock(bigint)` keyed on detailer UUID in appointment creation
- **Soft deletes**: filter `Model.is_deleted == False` in every query
- **Fail-fast config**: Pydantic `Settings` raises `ValidationError` at startup if required vars missing

### Startup Lifespan (main.py)
1. `create_all()` — create tables if not exist
2. Seed RBAC roles & permissions
3. Seed service catalog
4. Seed addons
5. Seed test detailers (detailer_seed.py)
6. On shutdown: `engine.dispose()`

### Middleware Stack
1. CORS (`http://localhost:8081` + configured origins)
2. Request size limiter (413 if > 5 MB)
3. Response time header injection (`X-Process-Time`)
4. Rate limiting (slowapi)

---

## Frontend Architecture

### Screens (17 total)
| Category | Screens |
|----------|---------|
| Auth | LoginScreen, RegisterScreen |
| Client home | HomeScreen |
| Profile | ProfileScreen, EditProfileScreen |
| Vehicles | VehiclesScreen, AddVehicleScreen, VehicleDetailScreen, SelectVehiclesScreen |
| Booking flow | BookingScreen, ScheduleScreen, DetailerSelectionScreen, BookingSummaryScreen |
| Detailer | DetailerOnboardingScreen, DetailerProfileScreen, DetailerServicesScreen, DetailerHomeScreen |

### Services (11 total)
| File | Responsibility |
|------|---------------|
| `api.ts` | Axios instances, JWT injection, 401 auto-refresh logic |
| `auth.service.ts` | Login, register, social auth, token refresh, password reset |
| `user.service.ts` | User profile management |
| `vehicle.service.ts` | Vehicle CRUD |
| `service.service.ts` | Service catalog |
| `addon.service.ts` | Addon catalog |
| `appointment.service.ts` | Create, list, patch status, cancel |
| `detailer.service.ts` | Search, availability, smart matching |
| `detailer-private.service.ts` | Authenticated detailer own profile |
| `payment.service.ts` | Stripe PaymentIntent creation |
| `review.service.ts` | Submit and fetch reviews |

### Navigation Structure

```text
RootStack
├── Login / Register
├── Main (client bottom tabs)
│   ├── Home
│   ├── Vehicles
│   └── Profile
├── DetailerMain (detailer bottom tabs)
│   ├── DetailerHome
│   └── DetailerProfile
└── Modal / Stack screens
    ├── AddVehicle, VehicleDetail, SelectVehicles
    ├── Booking, Schedule, DetailerSelection, BookingSummary
    ├── EditProfile
    ├── DetailerOnboarding, DetailerServices
```

---

## Testing

```bash
cd backend
pytest          # all tests
pytest -v       # verbose
```

- Uses `pytest` + `pytest-asyncio`
- Test file: `backend/test_endpoints.py`

---

## Sprint Roadmap

| Sprint | Status | Key Features |
|--------|--------|--------------|
| 1 | ✅ Done | Project skeleton, DB setup |
| 2 | ✅ Done | Auth, vehicles, reviews |
| 3 | ✅ Done | Appointments, services, Stripe payments, state machine |
| 4 | ✅ Done | Detailer discovery, webhooks, refund policy, timezone scheduling, rate limiting, social login |
| 5 | ✅ Done | Addons, multi-vehicle bookings, smart matching, email service, expanded catalog |
| 6 | 🔜 Next | Push notifications, admin dashboard, real-time tracking, detailer seed data |

---

## Common Pitfalls

- **VehicleSize is never stored** — it's derived from `body_class` at runtime via `body_class_to_size()`. Don't add a `size` column to Vehicle.
- **Prices are in cents** — always integer cents (`price_cents`), never floats.
- **Timestamps are UTC** — convert to detailer's IANA timezone only for display/availability logic.
- **Soft deletes** — always filter `Model.is_deleted == False`; never hard-delete rows.
- **estimated_price is immutable** — set once at appointment creation; never update it after creation.
- **Advisory lock scope** — the lock is per-detailer and transaction-scoped; always used within an async `with session.begin()` block.
- **Social-only users** — assigned an unusable bcrypt hash. Check `google_id`/`apple_id` before attempting password login.
- **CORS** — frontend runs on port 8081; backend allows this by default. For production, update `ALLOWED_ORIGINS`.

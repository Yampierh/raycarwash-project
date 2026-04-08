# RayCarwash Backend API

**RayCarwash** is a mobile car detailing marketplace (Airbnb / Uber model) that connects vehicle owners with mobile detailing specialists. Clients book appointments; detailers manage their schedule, location, and pricing. The backend is a production-grade async REST API built with **FastAPI + PostgreSQL**.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Data Models](#data-models)
5. [API Endpoints Reference](#api-endpoints-reference)
6. [Authentication & Security](#authentication--security)
7. [Business Logic](#business-logic)
8. [Environment Variables](#environment-variables)
9. [Database Migrations](#database-migrations)
10. [Running Locally](#running-locally)
11. [Seed Data](#seed-data)
12. [Sprint Roadmap](#sprint-roadmap)

---

## Architecture Overview

```
Mobile App (React Native / Expo)
         │
         ▼
   FastAPI (async)          ← single process, uvicorn + uvloop
         │
    ┌────┴────────────────────────────────────┐
    │  Routers → Services → Repositories     │
    │  (HTTP layer) (business) (SQL queries)  │
    └────┬────────────────────────────────────┘
         │
   PostgreSQL (asyncpg)     ← connection pool (SQLAlchemy 2.0)
         │
   Stripe Webhooks ─────────► webhook_router → payment_service
```

**Key design decisions:**
- **Async-first** — every database call, HTTP call, and email send uses `async/await` (no blocking calls on the event loop).
- **Repository pattern** — routers never touch the ORM directly; they call services which call repositories.
- **Advisory locks** — `pg_advisory_xact_lock(bigint)` prevents double-booking under concurrent requests.
- **Soft deletes** — all models carry `is_deleted + deleted_at`; no hard `DELETE` statements.
- **Fail-fast config** — Pydantic-Settings raises `ValidationError` at startup if any required env var is missing.

---

## Tech Stack

| Layer | Library | Version |
|-------|---------|---------|
| Framework | FastAPI | 0.115.5 |
| ASGI server | Uvicorn + uvloop | 0.32.1 |
| ORM | SQLAlchemy 2.0 (async) | 2.0.36 |
| DB driver | asyncpg | 0.30.0 |
| Migrations | Alembic | 1.14.0 |
| Validation | Pydantic v2 | 2.10.3 |
| Settings | pydantic-settings | 2.6.1 |
| Auth | python-jose[cryptography] | 3.3.0 |
| Passwords | passlib[bcrypt] | 1.7.4 |
| Payments | stripe | 11.3.0 |
| HTTP client | httpx | 0.27.2 |
| Rate limiting | slowapi | 0.1.9 |

---

## Project Structure

```
RAYCARWASH/
├── main.py                        # App factory, lifespan, router registration
├── requirements.txt
├── alembic.ini
├── FRONTEND_GUIDE.md              # Full API integration guide for mobile team
│
├── alembic/
│   ├── env.py                     # Async Alembic configuration
│   └── versions/
│       ├── 6520e3ed82aa_reset_alembic.py
│       ├── b905678c7172_add_body_class.py
│       ├── c7d8e9f0a1b2_add_oauth_columns_and_audit_actions.py
│       └── e4f5a6b7c8d9_sprint5_addons_multivehicle.py
│
├── app/
│   ├── core/
│   │   ├── config.py              # Settings (pydantic-settings, .env)
│   │   └── limiter.py             # slowapi rate limiter instance
│   │
│   ├── db/
│   │   ├── database.py            # Async engine + session factory
│   │   └── seed.py                # Service catalog + addon catalog seeds
│   │
│   ├── models/
│   │   └── models.py              # All SQLAlchemy ORM models
│   │
│   ├── schemas/
│   │   └── schemas.py             # All Pydantic v2 request/response schemas
│   │
│   ├── repositories/
│   │   ├── user_repository.py
│   │   ├── detailer_repository.py
│   │   ├── appointment_repository.py
│   │   ├── service_repository.py
│   │   ├── vehicle_repository.py
│   │   ├── review_repository.py
│   │   └── addon_repository.py
│   │
│   ├── services/
│   │   ├── auth.py                # JWT, bcrypt, Google/Apple token verification
│   │   ├── appointment_service.py # Booking logic, slot calculation, advisory locks
│   │   ├── payment_service.py     # Stripe PaymentIntent + refund policy
│   │   ├── review_service.py
│   │   ├── vehicle_service.py
│   │   ├── vehicle_lookup.py      # NHTSA VIN decode + body_class → VehicleSize map
│   │   └── email_service.py       # SMTP transactional email (async via thread)
│   │
│   └── routers/
│       ├── auth_router.py         # /auth/*
│       ├── appointment_router.py  # /api/v1/appointments/*
│       ├── detailer_router.py     # /api/v1/detailers/*
│       ├── matching_router.py     # /api/v1/matching
│       ├── addon_router.py        # /api/v1/addons
│       ├── service_router.py      # /api/v1/services/*
│       ├── vehicle_router.py      # /api/v1/vehicles/*
│       ├── review_router.py       # /api/v1/reviews/*
│       ├── payment_router.py      # /api/v1/payments/*
│       └── webhook_router.py      # /webhooks/stripe
```

---

## Data Models

### Users & Auth

```
User
  id              UUID PK
  email           VARCHAR unique
  password_hash   VARCHAR          ← bcrypt; "unusable" hash for social-only accounts
  full_name       VARCHAR
  role            ENUM(client, detailer, admin)
  phone_number    VARCHAR nullable
  google_id       VARCHAR(128) unique nullable   ← Sprint 4
  apple_id        VARCHAR(128) unique nullable   ← Sprint 4
  is_active       BOOLEAN
  is_deleted      BOOLEAN
  created_at / updated_at / deleted_at

RefreshToken
  id / token_hash / user_id FK / expires_at / revoked

AuditLog
  id / user_id / action(ENUM) / ip_address / user_agent / extra_data(JSONB)
```

### Detailer Profile

```
DetailerProfile
  id / user_id FK(unique)
  bio / years_experience / service_radius_miles
  latitude / longitude               ← current/home location
  timezone                           ← IANA (e.g. "America/Indiana/Indianapolis")
  working_hours                      ← JSONB  {"monday": {"start":"08:00","end":"18:00"}, ...}
  average_rating / total_reviews
  is_available / is_verified
```

### Services & Addons

```
Service
  id / name / description
  base_price_cents                   ← price for a "small" vehicle
  duration_minutes                   ← duration for a "small" vehicle
  is_active

Addon
  id / name / description
  price_cents                        ← flat add-on price
  duration_minutes                   ← flat add-on time
  is_active

DetailerService (join)
  detailer_id / service_id / custom_price_cents nullable
```

### Vehicles

```
Vehicle
  id / user_id FK
  make / model / year / vin nullable
  body_class                         ← from NHTSA VIN decode
  license_plate / color / notes

VehicleSize (computed, not stored)
  small | medium | large | xl        ← derived from body_class at runtime
  SIZE_MULTIPLIERS = {small:1.0, medium:1.2, large:1.5, xl:2.0}
```

### Appointments

```
Appointment
  id / client_id FK / detailer_id FK
  service_id FK / vehicle_id FK nullable   ← nullable for multi-vehicle
  status ENUM(pending, confirmed, in_progress, completed, cancelled)
  scheduled_at / estimated_duration_minutes
  estimated_price_cents / final_price_cents nullable
  client_lat / client_lng / client_address
  stripe_payment_intent_id
  cancellation_reason / cancelled_at

AppointmentVehicle                   ← Sprint 5: one row per vehicle in booking
  id / appointment_id FK / vehicle_id FK
  vehicle_size(ENUM snapshot) / price_cents / duration_minutes

AppointmentAddon                     ← Sprint 5: one row per addon in booking
  id / appointment_id FK / addon_id FK
  price_cents / duration_minutes
```

### Reviews

```
Review
  id / appointment_id FK(unique) / reviewer_id FK / reviewee_id FK
  rating(1-5) / comment / is_verified_purchase
```

---

## API Endpoints Reference

All endpoints are prefixed with `/api/v1` unless noted.

### Auth — `/auth`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | — | Register client or detailer |
| POST | `/auth/token` | — | Login (email + password), returns access + refresh token |
| POST | `/auth/refresh` | — | Exchange refresh token for new access token |
| POST | `/auth/logout` | Bearer | Revoke refresh token |
| POST | `/auth/google` | — | Login / register with Google access token |
| POST | `/auth/apple` | — | Login / register with Apple identity token |
| POST | `/auth/password-reset` | — | Request password reset email (always 200) |

**Rate limits:** `POST /auth/token` → 10 req/min per IP; `POST /auth/refresh` + social → 5 req/min per IP.

#### Token response shape
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Detailers — `/api/v1/detailers`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/detailers` | Bearer | Search detailers by lat/lng + radius. Haversine geo-filter. |
| GET | `/detailers/{id}` | Bearer | Get detailer profile + services |
| GET | `/detailers/{id}/slots` | Bearer | Available booking slots for a date |
| PUT | `/detailers/me` | Bearer(detailer) | Update own profile (bio, working_hours, location, timezone) |
| POST | `/detailers/me/services` | Bearer(detailer) | Add a service to own catalog |
| DELETE | `/detailers/me/services/{service_id}` | Bearer(detailer) | Remove service from catalog |

**Search query params:** `lat`, `lng`, `radius_miles` (default 25), `page`, `size`.

### Smart Matching — `/api/v1/matching`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/matching` | Bearer(client) | Find + rank detailers for a specific booking request |

**Query params:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `service_id` | UUID | yes | Service to book |
| `vehicle_ids` | UUID[] | yes | One or more client vehicles |
| `lat` | float | yes | Client latitude |
| `lng` | float | yes | Client longitude |
| `addon_ids` | UUID[] | no | Optional add-ons |
| `requested_time` | datetime | no | Omit for ASAP mode |
| `radius_miles` | float | no | Default 25 |

**ASAP mode** (no `requested_time`): sorted by `(distance, -rating)`.  
**Date mode** (with `requested_time`): sorted by `(-rating, distance)`.

**Response** includes per-detailer: `total_price_cents`, `total_duration_minutes`, `next_available_slot`, `available_slots[]`, `is_asap_available`.

### Appointments — `/api/v1/appointments`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/appointments` | Bearer(client) | Create booking (single or multi-vehicle + addons) |
| GET | `/appointments` | Bearer | List own appointments (paginated) |
| GET | `/appointments/{id}` | Bearer | Get appointment detail |
| PATCH | `/appointments/{id}/status` | Bearer(detailer) | Update status (confirmed → in_progress → completed) |
| POST | `/appointments/{id}/cancel` | Bearer | Cancel + trigger Stripe refund |

**Create request:**
```json
{
  "detailer_id": "uuid",
  "service_id": "uuid",
  "vehicle_ids": ["uuid", "uuid"],
  "addon_ids": ["uuid"],
  "scheduled_at": "2025-06-15T10:00:00Z",
  "client_lat": 41.0793,
  "client_lng": -85.1394,
  "client_address": "123 Main St, Fort Wayne, IN"
}
```

> `vehicle_id` (singular) is also accepted for backward compatibility.

**Concurrency safety:** booking overlap checks run inside a PostgreSQL advisory lock keyed on the detailer UUID, preventing double-booking under parallel requests.

### Vehicles — `/api/v1/vehicles`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/vehicles` | Bearer(client) | Add vehicle (VIN decoded via NHTSA) |
| GET | `/vehicles` | Bearer(client) | List own vehicles |
| GET | `/vehicles/{id}` | Bearer(client) | Get vehicle detail |
| PUT | `/vehicles/{id}` | Bearer(client) | Update vehicle |
| DELETE | `/vehicles/{id}` | Bearer(client) | Soft-delete vehicle |

### Services — `/api/v1/services`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/services` | — | List all active services |
| GET | `/services/{id}` | — | Get service detail |

### Add-ons — `/api/v1/addons`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/addons` | — | List all active add-ons |

### Payments — `/api/v1/payments`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/payments/create-intent` | Bearer(client) | Create Stripe PaymentIntent for appointment |
| GET | `/payments/{appointment_id}` | Bearer | Get payment status |

### Reviews — `/api/v1/reviews`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/reviews` | Bearer(client) | Submit review for a completed appointment |
| GET | `/reviews/detailer/{detailer_id}` | — | List reviews for a detailer |

### Stripe Webhook — `/webhooks/stripe`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/webhooks/stripe` | Stripe-Signature header | Receive Stripe events |

Handled events: `payment_intent.succeeded`, `payment_intent.payment_failed`, `charge.refunded`.  
Signature verified with `STRIPE_WEBHOOK_SECRET` before processing.

---

## Authentication & Security

### JWT Token Flow

```
1. POST /auth/token  →  { access_token, refresh_token }
2. All API calls     →  Authorization: Bearer <access_token>
3. POST /auth/refresh →  { access_token, refresh_token }  (rotates refresh token)
4. POST /auth/logout  →  revokes refresh token in DB
```

- **Access token** — HS256 JWT, expires in 30 min. Payload: `sub` (user_id), `role`, `type="access"`.
- **Refresh token** — HS256 JWT, expires in 7 days. Payload: `type="refresh"`. Stored as bcrypt hash in `refresh_tokens` table.
- **Token type** discriminator — using an access token on `/auth/refresh` is rejected (and vice versa).
- **Password reset token** — short-lived JWT (`type="password_reset"`, 1 h). Sent via email link, single-use.

### Social Login

**Google (`POST /auth/google`):**
```json
{ "access_token": "<Google OAuth2 access token>" }
```
Verifies token via `https://www.googleapis.com/oauth2/v1/tokeninfo`. On first login, creates a `client` account. Subsequent logins find user by `google_id`, falling back to matching by email (account linking).

**Apple (`POST /auth/apple`):**
```json
{ "identity_token": "<Apple RS256 JWT>", "full_name": "Jane Doe" }
```
Verifies JWT using Apple's public JWKS (`https://appleid.apple.com/auth/keys`). `full_name` stored only on first login (Apple only sends it once).

### Rate Limiting

Implemented with **slowapi** (X-Forwarded-For aware):

| Endpoint | Limit |
|----------|-------|
| POST `/auth/token` | 10 / min / IP |
| POST `/auth/refresh` | 5 / min / IP |
| POST `/auth/google` | 5 / min / IP |
| POST `/auth/apple` | 5 / min / IP |

### Request Size Guard

All requests over **5 MB** are rejected with `HTTP 413` before the body is read (configurable via `MAX_REQUEST_BODY_BYTES`).

---

## Business Logic

### Pricing

```
vehicle_price = ceil(service.base_price_cents × SIZE_MULTIPLIERS[vehicle_size])

SIZE_MULTIPLIERS = { small: 1.0, medium: 1.2, large: 1.5, xl: 2.0 }

total_price = Σ vehicle_price  +  Σ addon.price_cents
```

If a detailer has a `custom_price_cents` override for that service, it replaces `base_price_cents`.

### Duration

```
vehicle_duration = ceil(service.duration_minutes × SIZE_MULTIPLIERS[vehicle_size])
total_duration   = Σ vehicle_duration  +  Σ addon.duration_minutes
```

### Cancellation & Refund Policy

| Time before appointment | Refund |
|------------------------|--------|
| ≥ 24 hours | 100% |
| 2 – 24 hours | 50% |
| < 2 hours | 0% |

Thresholds are configurable via env vars (`CANCELLATION_FULL_REFUND_HOURS`, `CANCELLATION_PARTIAL_REFUND_HOURS`, `CANCELLATION_PARTIAL_REFUND_PERCENT`). Refund is issued via Stripe `Refund` object.

### Availability Slots

`GET /detailers/{id}/slots?date=2025-06-15&service_id=...&vehicle_size=medium`

1. Load detailer's `working_hours[weekday]` from JSONB (in their IANA timezone).
2. Load existing confirmed/in-progress appointments for that day.
3. Build candidate slots every `slot_step_minutes` (default 30).
4. Reject slots that overlap existing appointments + `TRAVEL_BUFFER_MINUTES` (default 30 min).
5. Return array of `{ start, end, available: true }`.

The matching endpoint calls the same logic with `override_duration_minutes` (computed total across all vehicles + addons) to check real availability for a specific booking.

### VehicleSize Derivation

NHTSA decodes the VIN and returns a `body_class` string (e.g. `"Sport Utility Vehicle (SUV)/Multi-Purpose Vehicle (MPV)"`). The function `map_body_to_size(body_class)` maps this to one of `small | medium | large | xl` using keyword matching. The result is **not stored** — it's computed on each request from `body_class`.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in all required values.

### Required

| Variable | Example | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://ray:pass@localhost:5432/raycarwash` | Must use asyncpg driver |
| `SECRET_KEY` | `openssl rand -hex 32` | JWT signing key, min 32 chars |

### Stripe

| Variable | Default | Description |
|----------|---------|-------------|
| `STRIPE_SECRET_KEY` | `sk_test_placeholder` | Use `sk_test_*` in dev |
| `STRIPE_WEBHOOK_SECRET` | `whsec_placeholder` | From Stripe Dashboard → Webhooks |
| `STRIPE_CURRENCY` | `usd` | ISO 4217 currency code |

### Social Login

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CLIENT_ID` | `""` | Leave empty to skip audience check (dev only) |
| `APPLE_BUNDLE_ID` | `com.raycarwash.app` | Must match App Store Connect bundle ID |

### Email (SMTP)

| Variable | Default | Description |
|----------|---------|-------------|
| `SMTP_ENABLED` | `false` | Set `true` to send real emails |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | 587 = STARTTLS, 465 = SSL |
| `SMTP_USERNAME` | `""` | Usually your email address |
| `SMTP_PASSWORD` | `""` | App password (not account password) |
| `SMTP_FROM_EMAIL` | `noreply@raycarwash.com` | From address |
| `SMTP_FROM_NAME` | `RayCarwash` | From display name |

> When `SMTP_ENABLED=false`, password reset links are printed to stdout — useful for development.

### Tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | |
| `TRAVEL_BUFFER_MINUTES` | `30` | Gap between appointments |
| `CANCELLATION_FULL_REFUND_HOURS` | `24` | |
| `CANCELLATION_PARTIAL_REFUND_HOURS` | `2` | |
| `CANCELLATION_PARTIAL_REFUND_PERCENT` | `50` | |
| `MAX_REQUEST_BODY_BYTES` | `5242880` | 5 MB |
| `DB_POOL_SIZE` | `10` | SQLAlchemy pool |
| `DB_MAX_OVERFLOW` | `20` | |
| `RATE_LIMIT_AUTH_PER_MINUTE` | `10` | |
| `RATE_LIMIT_API_PER_MINUTE` | `120` | |
| `APP_BASE_URL` | `https://api.raycarwash.com` | Used in email links |
| `ALLOWED_ORIGINS` | `["http://localhost:8081"]` | CORS allowed origins |

---

## Database Migrations

Alembic is configured for **async** PostgreSQL. Run migrations with:

```bash
# Apply all pending migrations
alembic upgrade head

# Check current revision
alembic current

# Create a new migration (auto-detect model changes)
alembic revision --autogenerate -m "your description"

# Roll back one step
alembic downgrade -1
```

### Migration History

| Revision | Description |
|----------|-------------|
| `6520e3ed82aa` | Reset / baseline |
| `b905678c7172` | Add `body_class` to vehicles |
| `c7d8e9f0a1b2` | Add `google_id`, `apple_id` to users; new audit actions |
| `e4f5a6b7c8d9` | Sprint 5: `addons`, `appointment_vehicles`, `appointment_addons` tables; make `vehicle_id` nullable |

> **Note:** The `c7d8e9f0a1b2` migration uses `AUTOCOMMIT` isolation for the `ALTER TYPE ... ADD VALUE` statements — this is required by PostgreSQL and handled automatically by the migration script.

---

## Running Locally

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- (Optional) A Stripe account for payment testing

### Setup

```bash
# 1. Clone and install dependencies
git clone https://github.com/Yampierh/RAYCARWASH.git
cd RAYCARWASH
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Create the database
createdb raycarwash

# 3. Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL and SECRET_KEY at minimum

# 4. Run migrations
alembic upgrade head

# 5. Start the API server
uvicorn main:app --reload --port 8000
```

The API is now available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`  
ReDoc: `http://localhost:8000/redoc`

### Health Check

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"v1","sprint":"Sprint 5"}
```

---

## Seed Data

On startup, the app automatically seeds the following catalog (idempotent — safe to restart):

### Services Seeded

| Service | Base Price | Duration (small) |
|---------|-----------|-----------------|
| Exterior Wash & Dry | $29 | 45 min |
| Interior Vacuum & Wipe | $35 | 60 min |
| Full Detail (Interior + Exterior) | $120 | 180 min |
| Engine Bay Cleaning | $75 | 60 min |
| Paint Decontamination | $95 | 90 min |
| Ceramic Coating (Entry) | $299 | 240 min |
| Paint Correction (1-Step) | $199 | 240 min |
| Headlight Restoration | $49 | 45 min |

Prices for `medium`, `large`, and `xl` vehicles are computed automatically using `SIZE_MULTIPLIERS`.

### Add-ons Seeded

| Add-on | Price | Duration |
|--------|-------|---------|
| Clay Bar Treatment | +$30 | +45 min |
| Odor Eliminator | +$20 | +20 min |
| Ceramic Spray Coat | +$50 | +30 min |
| Engine Bay Clean | +$40 | +40 min |
| Headlight Restoration | +$35 | +35 min |

---

## Sprint Roadmap

| Sprint | Status | Key Features |
|--------|--------|--------------|
| Sprint 1 | ✅ Done | Project skeleton, DB setup |
| Sprint 2 | ✅ Done | Auth (register/login/refresh/logout), vehicles, reviews |
| Sprint 3 | ✅ Done | Appointments, services, payments scaffold |
| Sprint 4 | ✅ Done | Detailer discovery (geo-search), Stripe webhooks, cancellation/refund policy, timezone-aware scheduling, rate limiting, social login (Google/Apple), password reset |
| Sprint 5 | ✅ Done | Add-ons, multi-vehicle bookings, smart matching endpoint, email service (SMTP), expanded service catalog |
| Sprint 6 | 🔜 Next | Detailer seed data for testing, push notifications (FCM/APNs), admin dashboard endpoints, real-time appointment tracking |

---

## Error Codes

All errors follow this shape:
```json
{ "detail": "Human-readable message" }
```

| HTTP | When |
|------|------|
| 400 | Validation error, bad request body |
| 401 | Missing or expired token |
| 403 | Authenticated but not authorized (wrong role, wrong owner) |
| 404 | Resource not found |
| 409 | Conflict (e.g. time slot no longer available) |
| 413 | Request body too large |
| 422 | Pydantic schema validation failed |
| 429 | Rate limit exceeded |
| 500 | Unexpected server error |

---

## CORS

Configured via `ALLOWED_ORIGINS`. In development, `http://localhost:8081` (Expo) and `http://localhost:3000` (web) are allowed by default.

---

## License

Proprietary — all rights reserved by RayCarwash.

# AGENTS.md — RayCarWash project context

## Project overview

**RayCarWash** — Mobile vehicle services marketplace (Airbnb/Uber model).
Connects clients with mobile detailers who come to the client's location.

- **Current vertical**: Car detailing (fully functional)
- **Planned**: Multiservice — mechanics, accessories, inspections (Sprint 7)
- **Market**: Fort Wayne, IN
- **Backend**: FastAPI + PostgreSQL + Redis — DDD-lite architecture
- **Frontend**: React Native + Expo + TypeScript

---

## Quick commands

```bash
npm run install        # frontend npm deps
npm run install-deps   # Python venv + backend deps
npm run dev            # start both (concurrently)
npm run dev:backend    # FastAPI on :8000
npm run dev:frontend   # Expo on :8081

cd backend
alembic upgrade head   # run DB migrations (production)
python -m pytest tests/test_auth.py tests/test_appointments.py -q  # core tests
```text

---

## Documentation

| File | Contents |
| --- | --- |
| `README.md` | Project overview, quick start, tech stack, sprint roadmap |
| `docs/backend.md` | DDD structure, patterns, startup sequence, auth, state machine |
| `docs/api.md` | Complete REST + WebSocket API reference (frontend integration) |
| `docs/frontend.md` | Screens, navigation, Axios clients, booking flow, onboarding steps |
| `docs/decisions.md` | Architectural decisions, bugs fixed, sprint changelog, pitfalls |

---

## Architecture: DDD-lite

```text
backend/
├── main.py                 # Composition root
├── api/router.py           # Aggregates all domain routers
├── domains/                # Business logic by domain
│   ├── auth/               # JWT (RS256), WebAuthn, OAuth2, lockout
│   │   └── routers/        # Split by concern: core, social, webauthn, sessions, password, email_verification
│   ├── admin/              # Admin API — users/roles/permissions CRUD (/api/v1/admin/*)
│   ├── users/              # User, ClientProfile, onboarding
│   ├── providers/          # ProviderProfile, Stripe Identity
│   ├── vehicles/           # Vehicle CRUD, NHTSA VIN
│   ├── appointments/       # FSM lifecycle, slots, advisory locks
│   ├── matching/           # H3 geospatial scoring
│   ├── payments/           # Stripe, ledger, fare, rides
│   ├── services_catalog/   # Service + addon catalogue
│   ├── reviews/            # Rating aggregation
│   ├── notifications/      # Push notifications — Expo Push API, device tokens, event handlers
│   ├── realtime/           # WebSocket rooms (Redis Pub/Sub)
│   └── audit/              # Append-only event log
├── infrastructure/         # External adapters
│   ├── db/                 # SQLAlchemy engine, Base, registry
│   ├── redis/              # Connection pool + fakeredis fallback
│   ├── email/              # SMTP service
│   ├── nhtsa/              # VIN decode API
│   └── h3/                 # Geospatial indexing
├── shared/schemas.py       # Cross-domain base classes
├── workers/                # Background asyncio tasks
└── app/core/ + app/db/     # Config, security, seed data (stable, not domain code)
```text

**Import rule**: `domains/X` imports from `domains/Y`, `infrastructure/`, or `shared/` directly. No shims.

---

## Environment variables

### Backend (`backend/.env`)

```text
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/raycarwash

# JWT — RS256 asymmetric (replaced HS256 JWT_SECRET_KEY in sprint 7)
# Generate: openssl genrsa -out priv.pem 2048 && openssl rsa -in priv.pem -pubout -out pub.pem
# Escape newlines for .env: JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMII...\n-----END RSA PRIVATE KEY-----"
JWT_PRIVATE_KEY=<PEM RSA-2048 private key>
JWT_PUBLIC_KEY=<PEM RSA-2048 public key>

ENCRYPTION_KEY=<32+ char base64 key for PII — independent of JWT keys>
PHONE_LOOKUP_KEY=<32+ char hex for phone HMAC — independent of other keys>
DEBUG=true

STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
SMTP_ENABLED=false
GOOGLE_CLIENT_ID=
APPLE_BUNDLE_ID=com.raycarwash.app
REDIS_URL=redis://localhost:6379
REQUIRE_EMAIL_VERIFICATION=false
```text

### Frontend (`frontend/.env.local`)

```text
EXPO_PUBLIC_API_URL=http://localhost:8000
```text

### Admin dashboard (`web/.env.local`)

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
```text

For physical device testing, replace `localhost` with your machine's LAN IP.

---

## Key business rules

**Pricing**: `price = ceil(service.base_price_cents × SIZE_MULTIPLIER[vehicle.size])`
Multipliers: small ×1.0 · medium ×1.2 · large ×1.5 · xl ×2.0.

**VehicleSize**: derived at runtime from `body_class` via `map_body_to_size()`. Never stored.

**Appointment FSM**: PENDING → CONFIRMED → ARRIVED → IN_PROGRESS → COMPLETED (or cancellations).

**Cancellation refunds**: ≥24h → 100% · 2–24h → 50% · <2h → 0%.

**Prices are cents**: always integer cents. Never floats. Display: `/ 100`.

**Soft deletes**: every entity has `is_deleted + deleted_at`. Never hard-delete.

**estimated_price is immutable**: set once at creation. `actual_price` set on COMPLETED.

---

## Auth flow summary

```text
POST /auth/register  → { onboarding_token }   (new account)
POST /auth/login     → { access_token, refresh_token }  (existing, onboarding_completed)
                     → { onboarding_token }             (existing, onboarding incomplete)
PUT  /auth/complete-profile  [Bearer onboarding_token]  → { access_token, refresh_token }
```text

Token types:
- `access`      — 30 min, RS256 signed. Verified via public key or GET /.well-known/jwks.json
- `refresh`     — 7 days, single-use opaque token, stored as SHA-256 hash, theft detection via family revocation
- `onboarding`  — 30 min, RS256 signed, scope-limited to /auth/complete-profile ONLY

JWT algorithm: **RS256** (asymmetric). Private key signs; public key verifies.
JWKS public endpoint: `GET /.well-known/jwks.json` — any internal service can verify tokens without the private key.

Email verification tokens: DB-backed, single-use (table: `email_verification_tokens`). No longer a stateless JWT.
WebAuthn challenges: stored in Redis (key: `webauthn_challenge:{session_id}`, TTL 5 min). Consumed on verify — prevents replay.

Token storage (frontend SecureStore):
- `raycarwash_jwt_token`          — access token
- `raycarwash_onboarding_token`   — onboarding token (separate key — do NOT conflate)
- `raycarwash_refresh_token`      — refresh token

authClient injects: access_token ?? onboarding_token (fallback)
apiClient injects: access_token ONLY

Security: PUT /auth/complete-profile rejects with 403 if onboarding_status == "completed".
This prevents a logged-in client from escalating to detailer role without KYC.

## Admin API

All endpoints under `/api/v1/admin/*` require `role=admin` Bearer token.

```text
GET  /api/v1/admin/stats                              # platform overview counts
GET  /api/v1/admin/users?page&per_page&search&role    # paginated user list
GET  /api/v1/admin/users/{id}                         # user detail + roles + permissions
PATCH /api/v1/admin/users/{id}                        # set is_active
POST /api/v1/admin/users/{id}/roles                   # assign role { role_id }
DELETE /api/v1/admin/users/{id}/roles/{role_id}       # revoke role
GET  /api/v1/admin/roles                              # all roles with permissions
POST /api/v1/admin/roles                              # create role
PATCH /api/v1/admin/roles/{id}                        # update role (non-system only)
DELETE /api/v1/admin/roles/{id}                       # soft-delete role (non-system only)
POST /api/v1/admin/roles/{id}/permissions             # assign permission { permission_id }
DELETE /api/v1/admin/roles/{id}/permissions/{perm_id} # revoke permission
GET  /api/v1/admin/permissions                        # full permission catalog
POST /api/v1/admin/permissions                        # create permission
DELETE /api/v1/admin/permissions/{id}                 # delete permission
```text

System roles (`is_system=True`): admin, detailer, client — cannot be deleted via API.
Seeded permissions (18 total): read/write/delete across users, roles, permissions, appointments, providers, payments, reviews, services.

## Admin dashboard (web/)

Next.js 15 app at `http://localhost:3000`. Start: `cd web && npm run dev`.

Pages:
- `/login` — admin email/password login; verifies JWT role == "admin"
- `/dashboard` — stats cards (users, detailers, appointments, etc.)
- `/dashboard/users` — paginated table, search, role filter, ban/unban toggle
- `/dashboard/users/[id]` — user detail, role assignment/revocation, effective permissions
- `/dashboard/roles` — role list + permission matrix (toggle checkboxes per resource)
- `/dashboard/permissions` — catalog grouped by resource, create/delete form

---

## Two Axios clients (frontend — critical)

```text
authClient  → base /auth      (register, login, complete-profile, social, refresh, sessions, passkeys)
apiClient   → base /api/v1    (everything else)
```text

Never mix. Auth endpoints are at `/auth`, not `/api/v1/auth`.

authClient request interceptor: injects `access_token ?? onboarding_token` — supports mid-onboarding calls to /complete-profile.
apiClient request interceptor: injects `access_token` only — never onboarding scope.
apiClient response interceptor: auto-refresh on 401, queue concurrent requests, revoke+redirect on refresh failure.

---

## WebSocket

```text
WS /ws/appointments/{id}?token=<access_token>
```text

JWT in query param (headers unavailable post-handshake).
Frontend hook: `useAppointmentSocket` — auto-connect, exponential backoff, 30s heartbeat.

---

## Push notifications (Sprint 8)

Expo Push API — no Firebase project needed for managed workflow. Tokens have format `ExponentPushToken[...]`.

```text
POST /api/v1/notifications/device-token   # register (call after login)
DELETE /api/v1/notifications/device-token # unregister (call on logout)
```

Event bus triggers (domains/notifications/handlers.py):

| Event | Recipient | Notification |
|---|---|---|
| appointment.created (PENDING) | detailer | "New booking request" |
| CONFIRMED | client | "Booking confirmed!" |
| ARRIVED | client | "Your detailer has arrived" |
| IN_PROGRESS | client | "Service in progress" |
| COMPLETED | client | "All done! ⭐" |
| CANCELLED_BY_CLIENT | detailer | "Appointment cancelled" |
| CANCELLED_BY_DETAILER | client | "Appointment cancelled" |

Frontend: `usePushNotifications` hook in `src/hooks/` — requests permission, registers token, handles tap navigation. Token persisted in SecureStore. `clearAuthTokens()` unregisters on logout.

---

## Test status

```text
tests/test_auth.py         70/70  ✅  (includes role-escalation security test)
tests/test_appointments.py 19/19  ✅
tests/test_user_flows.py   17/17  ✅  (client + detailer registration flows, guard rails)
tests/test_admin.py        27/27  ✅  (all /api/v1/admin/* — auth, stats, users, roles, permissions)
tests/test_detailers.py    ⚠️  edge cases (profile fixture)
tests/test_matching.py     ⚠️  requires real Redis for H3 spatial tests
tests/test_vehicles.py     ⚠️  body_class / onboarding edge cases
```

Run core suite:

```bash
cd backend
python -m pytest tests/test_auth.py tests/test_appointments.py tests/test_user_flows.py tests/test_admin.py -q
```

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
│   ├── auth/               # JWT, WebAuthn, OAuth2, lockout
│   ├── users/              # User, ClientProfile, onboarding
│   ├── providers/          # ProviderProfile, Stripe Identity
│   ├── vehicles/           # Vehicle CRUD, NHTSA VIN
│   ├── appointments/       # FSM lifecycle, slots, advisory locks
│   ├── matching/           # H3 geospatial scoring
│   ├── payments/           # Stripe, ledger, fare, rides
│   ├── services_catalog/   # Service + addon catalogue
│   ├── reviews/            # Rating aggregation
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
SECRET_KEY=<32+ char secret>
ENCRYPTION_KEY=<32+ char key for PII — separate from JWT key>
DEBUG=true

STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
SMTP_ENABLED=false
GOOGLE_CLIENT_ID=
APPLE_BUNDLE_ID=com.raycarwash.app
REDIS_URL=redis://localhost:6379
```text

### Frontend (`frontend/.env.local`)

```text
EXPO_PUBLIC_API_URL=http://localhost:8000
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
POST /auth/identify  → { is_new_user, available_methods }
POST /auth/verify    → tokens (existing) | onboarding_token (new)
PUT  /auth/complete-profile  [Bearer onboarding_token]  → full tokens
```text

Token types: `access` (30 min) · `refresh` (7 days) · `onboarding` (30 min, scoped).

---

## Two Axios clients (frontend — critical)

```text
authClient  → base /auth      (identify, verify, complete-profile, social, refresh)
apiClient   → base /api/v1    (everything else)
```text

Never mix. Auth endpoints are at `/auth`, not `/api/v1/auth`.

---

## WebSocket

```text
WS /ws/appointments/{id}?token=<access_token>
```text

JWT in query param (headers unavailable post-handshake).
Frontend hook: `useAppointmentSocket` — auto-connect, exponential backoff, 30s heartbeat.

---

## Test status

```text
tests/test_auth.py         69/69  ✅
tests/test_appointments.py 19/19  ✅
tests/test_detailers.py    ⚠️  edge cases
tests/test_matching.py     ⚠️  requires real Redis
tests/test_vehicles.py     ⚠️  edge cases
```

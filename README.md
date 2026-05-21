# RayCarWash

Mobile vehicle services marketplace — Fort Wayne, IN.

Connects clients with mobile service providers (detailers, mechanics, and more) who come to the client's location. Think Uber, but for car care.

> **Current phase**: Detailing vertical — getting it 100% functional before expanding to multiservice.

---

## Project structure

```
raycarwash-project/
├── backend/                        # FastAPI · Python 3.13 · PostgreSQL
│   ├── main.py                     # Composition root — lifespan, middleware, health check
│   ├── api/router.py               # Single aggregation of all domain routers
│   ├── domains/                    # Domain-Driven Design (DDD-lite) — 19 domains
│   │   ├── auth/                   # JWT (RS256), OAuth2 social, WebAuthn passkeys, lockout, 2FA
│   │   │   └── routers/            # Split: core, social, webauthn, sessions, password, email, security
│   │   ├── admin/                  # Admin dashboard API — users, roles, permissions CRUD
│   │   ├── users/                  # Registration, profiles, onboarding (client+detailer)
│   │   ├── providers/              # Detailer profiles, Stripe Identity verification
│   │   ├── vehicles/               # Vehicle CRUD, NHTSA VIN lookup
│   │   ├── appointments/           # FSM booking lifecycle, availability slots
│   │   ├── matching/               # H3 geospatial + scoring engine
│   │   ├── payments/               # Stripe intents, webhooks, fare estimation, ledger
│   │   ├── services_catalog/       # Service + addon catalogue
│   │   ├── reviews/                # Rating aggregation
│   │   ├── notifications/          # Push notifications — Expo Push API, device tokens
│   │   ├── realtime/               # Redis Pub/Sub WebSocket rooms
│   │   ├── audit/                  # Append-only audit log
│   │   ├── credits/                # Comp credits system
│   │   ├── identity/               # Identity verification flows
│   │   ├── locations/              # Geocoding, city/ZIP coverage
│   │   ├── onboarding/             # Multi-step onboarding wizard
│   │   ├── promos/                 # Promo code system
│   │   └── public/                 # Public marketing endpoints
│   ├── infrastructure/             # Adapters for external systems — 11 adapters
│   │   ├── db/                     # SQLAlchemy engine, session, Base, mapper registry
│   │   ├── redis/                  # Connection pool + fakeredis dev fallback
│   │   ├── email/                  # SMTP transactional email
│   │   ├── nhtsa/                  # VIN decode API client
│   │   ├── h3/                     # H3 geospatial indexing (detailer discovery)
│   │   ├── stripe/                 # Stripe SDK clients
│   │   ├── geocoding/              # Nominatim/Google geocoding
│   │   ├── sms/                    # SMS adapter
│   │   ├── storage/                # S3-compatible object storage
│   │   └── auth/                   # Auth provider adapters
│   ├── shared/schemas.py           # Envelope[T], PaginatedEnvelope[T], ErrorEnvelope
│   ├── workers/                    # Async background workers — 11 workers
│   │   ├── location_worker.py      # GPS stream → H3 index + WS broadcast
│   │   ├── assignment_worker.py    # Auto-assignment engine
│   │   ├── ledger_seal_worker.py   # Daily ledger SHA-256 seal
│   │   ├── token_cleanup_worker.py # Expired token GC
│   │   ├── session_cleanup_worker.py
│   │   ├── achievement_evaluator.py
│   │   ├── document_expiry_checker.py
│   │   ├── login_history_purger.py
│   │   ├── pending_contact_cleanup.py
│   │   └── schedule/               # Scheduled task dispatcher
│   ├── events/bus.py               # In-process async event bus
│   └── app/                        # Stable infrastructure (config, seed, security)
│       ├── core/                   # config.py, security.py, limiter.py
│       └── db/                     # seed.py, seed_rbac.py (roles + permissions), detailer_seed.py
│
├── frontend/                       # React Native · Expo 54 · TypeScript
│   └── src/
│       ├── screens/                # 35 screen components
│       ├── services/               # 17 API service files
│       ├── components/             # Shared design system: Button, Card, EmptyState, etc.
│       ├── hooks/                  # useAppointmentSocket, useLocation, etc.
│       ├── store/                  # authStore (Zustand)
│       ├── navigation/             # RootStack, MainTabs, DetailerTabs
│       ├── utils/                  # storage (SecureStore), auth-redirect, formatters
│       └── theme/colors.ts         # Semantic tokens
│
├── web/
│   ├── admin/                      # Next.js 16 · Admin dashboard (:3000)
│   ├── portal/                     # Next.js 16 · Public site + provider portal (:3001)
│   └── portal_v2/                  # Next.js 16 · Portal v2 rebuild (:3002, PR #8)
│
├── docker-compose.yml
├── AGENTS.md                       # Full technical context for AI agents
└── docs/                           # INDEX.md · backend.md · frontend.md · api.md · plans/
```

---

## Prerequisites

- **Node.js** 18+
- **Python** 3.11+
- **PostgreSQL** 14+
- **Redis** (optional — fakeredis fallback in dev)

---

## Quick start

```bash
# 1. Install npm dependencies (frontend)
npm run install

# 2. Create Python venv + install backend deps
npm run install-deps

# 3. Run database migrations
cd backend && alembic upgrade head && cd ..

# 4. Start backend + frontend
npm run dev
```

> **First-time startup** seeds a default admin user: `admin@raycarwash.com` / `Admin1234!`

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Expo (frontend) | http://localhost:8081 |
| Admin dashboard | http://localhost:3000 |
| Portal (public) | http://localhost:3001 |
| Portal v2 | http://localhost:3002 |

---

## Available scripts

| Command | Description |
|---|---|
| `npm run install` | Install npm deps (frontend) |
| `npm run install-deps` | Create Python venv + install backend deps |
| `npm run dev` | Backend + frontend concurrently |
| `npm run dev:backend` | Backend only (FastAPI :8000) |
| `npm run dev:frontend` | Frontend only (Expo :8081) |
| `npm run dev:admin` | Admin dashboard (Next.js :3000) |
| `npm run dev:portal` | Public portal (Next.js :3001) |
| `npm run dev:portal-v2` | Portal v2 (Next.js :3002) |

---

## Tech stack

### Backend
- FastAPI (REST + WebSocket)
- SQLAlchemy async (asyncpg) — DDD-lite domain structure
- PostgreSQL 14+
- Pydantic v2
- Alembic (migrations)
- Stripe SDK v11 + Stripe Identity
- WebAuthn (passkeys via FIDO2), TOTP (2FA)
- slowapi (rate limiting)
- H3 (Uber's geospatial indexing)
- Redis / fakeredis (Pub/Sub, caching, idempotency)
- RS256 asymmetric JWT (JWKS at `/.well-known/jwks.json`)

### Frontend (mobile)
- React Native (Expo 54)
- React Navigation
- Axios + WebSocket
- Zustand (auth store)
- expo-secure-store

### Web
- Next.js 16 (App Router) — 3 workspaces
- TypeScript + Tailwind CSS
- next-intl (portal i18n)
- TanStack Table (admin)

---

## Architecture: DDD-lite

The backend is organized into 19 domains under `domains/`. Each domain owns its models, schemas, repository, service, and router. Cross-domain imports go direct (no shims).

**Key principles:**
- Prices in integer cents (never floats). Display: `/ 100`.
- Soft deletes on every entity (`is_deleted` + `deleted_at`). Never hard-delete.
- Timestamps are UTC. Convert to local only for display.
- Response envelope: `Envelope[T]` on every v1 endpoint.
- Append-only audit log on every mutation.
- Session enforcement (`sid` claim) on login-sensitive operations.
- Idempotency-Key middleware (Redis-backed) for payment-sensitive endpoints.

---

## Test status

**618 tests across 49 files — 563/563 green suite** (excluding 3 ⚠️ files).

Run tests:
```bash
cd backend
python -m pytest tests/test_auth.py tests/test_appointments.py tests/test_user_flows.py tests/test_admin.py -q
```

See [`AGENTS.md`](./AGENTS.md) for the full test matrix and per-file counts.

---

## License

Private — All rights reserved.

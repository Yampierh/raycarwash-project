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
│   ├── domains/                    # Domain-Driven Design (DDD-lite)
│   │   ├── auth/                   # JWT, OAuth2 social, WebAuthn passkeys, lockout
│   │   ├── users/                  # Registration, profiles, onboarding
│   │   ├── providers/              # Detailer profiles, Stripe Identity verification
│   │   ├── vehicles/               # Vehicle CRUD, NHTSA VIN lookup
│   │   ├── appointments/           # FSM booking lifecycle, availability slots
│   │   ├── matching/               # H3 geospatial + scoring engine
│   │   ├── payments/               # Stripe intents, webhooks, fare estimation, ledger
│   │   ├── services_catalog/       # Service + addon catalogue
│   │   ├── reviews/                # Rating aggregation
│   │   ├── realtime/               # Redis Pub/Sub WebSocket rooms
│   │   └── audit/                  # Append-only audit log
│   ├── infrastructure/             # Adapters for external systems
│   │   ├── db/                     # SQLAlchemy engine, session, Base, mapper registry
│   │   ├── redis/                  # Connection pool + fakeredis dev fallback
│   │   ├── email/                  # SMTP transactional email
│   │   ├── nhtsa/                  # VIN decode API client
│   │   └── h3/                     # H3 geospatial indexing (detailer discovery)
│   ├── shared/schemas.py           # Cross-domain base classes + shared types
│   ├── workers/                    # Async background workers
│   │   ├── location_worker.py      # GPS stream → H3 index + WS broadcast
│   │   ├── assignment_worker.py    # Auto-assignment engine
│   │   ├── ledger_seal_worker.py   # Daily ledger SHA-256 seal
│   │   └── token_cleanup_worker.py # Expired token GC
│   ├── events/bus.py               # In-process async event bus
│   └── app/                        # Legacy infrastructure (config, seed, security)
│       ├── core/                   # config.py, security.py, limiter.py
│       └── db/                     # seed.py, seed_rbac.py, detailer_seed.py
│
├── frontend/                       # React Native · Expo · TypeScript
│   └── src/
│       ├── screens/                # 17 screen components
│       ├── services/               # 11 API service files
│       ├── hooks/                  # useAppointmentSocket
│       ├── store/                  # authStore (Zustand)
│       ├── navigation/             # RootStack, MainTabs, DetailerTabs
│       └── theme/
│
├── docker-compose.yml
├── AGENTS.md                       # Full technical context for AI agents
├── API_GUIDE.md                    # REST + WebSocket reference
└── AUDIT_REPORT.md                 # Bug log and test coverage status
```

---

## Prerequisites

- **Node.js** 18+
- **Python** 3.11+
- **PostgreSQL** 14+

---

## Quick start

```bash
# 1. Install npm dependencies (frontend)
npm run install

# 2. Create Python venv + install backend deps
npm run install-deps

# 3. Configure environment variables (see below)

# 4. Run database migrations
cd backend && alembic upgrade head && cd ..

# 5. Start both projects
npm run dev
```

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Expo (frontend) | http://localhost:8081 |

---

## Environment variables

**Backend** — `backend/.env`:
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/raycarwash
SECRET_KEY=your-32-char-secret-here
DEBUG=true

# Optional
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
SMTP_ENABLED=false
GOOGLE_CLIENT_ID=
APPLE_BUNDLE_ID=com.raycarwash.app
```

**Frontend** — `frontend/.env.local`:
```
EXPO_PUBLIC_API_URL=http://localhost:8000
```

> For physical device testing, replace `localhost` with your machine's LAN IP.

---

## Available scripts

| Command | Description |
|---|---|
| `npm run install` | Install npm deps (frontend) |
| `npm run install-deps` | Create Python venv + install backend deps |
| `npm run dev` | Start both backend and frontend in parallel |
| `npm run dev:backend` | Backend only (FastAPI on port 8000) |
| `npm run dev:frontend` | Frontend only (Expo on port 8081) |

---

## Tech stack

### Backend
- FastAPI (REST + WebSocket)
- SQLAlchemy async (asyncpg) — DDD-lite domain structure
- PostgreSQL 14+
- Pydantic v2
- Alembic (migrations)
- Stripe SDK v11 + Stripe Identity
- WebAuthn (passkeys via FIDO2)
- slowapi (rate limiting)
- H3 (Uber's geospatial indexing library)
- Redis / fakeredis (Pub/Sub + location caching)

### Frontend
- React Native (Expo)
- React Navigation
- Axios + WebSocket
- Zustand (auth store)
- expo-secure-store

---

## Architecture: DDD-lite

The backend was refactored from a monolithic `app/` structure into a Domain-Driven Design layout. Each domain owns its models, schemas, repository, service, and router. Cross-domain dependencies go through the `shared/` layer or direct domain imports (no circular dependencies).

**Import rules:**

- `domains/X` → may import from `domains/Y` (direct, no shims)
- `domains/X` → may import from `infrastructure/` and `shared/`
- `workers/` → imports from `domains/` and `infrastructure/`
- `app/core/` and `app/db/` → remain as stable infrastructure (not domain code)

---

## User flows

### Client (8 steps to full profile)
1. Splash — choose role
2. Identifier-first (email or phone → new vs returning)
3. Create account (name + password)
4. Contact details (fill missing email or phone)
5. Add vehicle (VIN lookup via NHTSA or manual)
6. Payment method (Stripe)
7. Preferences (notifications, search radius)
8. Home — ready to book

**Blocking steps**: vehicle (step 5) + payment (step 6). Everything else is optional.

### Detailer (10 steps to full profile)
1. Splash — choose role
2. Identifier-first + create account
3. Personal info + bio (public profile)
4. Service zone (city + radius in miles)
5. Services offered (toggle from catalog + optional custom price)
6. Weekly availability (days + hours + buffer between jobs)
7. Identity verification (Stripe Identity — may take minutes/hours)
8. Bank account for payouts (Stripe Connect)
9. Activate availability (toggle "accepting bookings")
10. Dashboard — ready to receive jobs

**Blocking steps**: identity verification (step 7) + bank account (step 8). Without both, detailer cannot receive payments.

---

## Sprint roadmap

| Sprint | Status | Key features |
|---|---|---|
| 1 | ✅ Done | Project skeleton, DB setup |
| 2 | ✅ Done | Auth (identifier-first), vehicles, reviews |
| 3 | ✅ Done | Appointments, services, Stripe payments, state machine |
| 4 | ✅ Done | Detailer discovery, webhooks, refund policy, timezone scheduling, rate limiting, social login |
| 5 | ✅ Done | Addons, multi-vehicle bookings, smart matching, email service |
| 6 | ✅ Done | DDD-lite refactor, structured logging + request ID, WebAuthn passkeys, Stripe Identity, H3 geospatial, auto-assignment engine, append-only ledger, WebSocket real-time tracking |
| 7 | 📋 Planned | Push notifications (RAMEN/Fireball), admin dashboard, full test coverage, multiservice: mechanic vertical |

---

## Test status

```text
tests/test_auth.py         69/69  ✅ all pass
tests/test_appointments.py 19/19  ✅ all pass
tests/test_detailers.py    ~pass  (profile fixture edge cases pending)
tests/test_matching.py     ~pass  (H3 index requires real Redis for spatial tests)
tests/test_vehicles.py     ~pass  (body_class / onboarding edge cases pending)
```

Run tests:

```bash
cd backend
python -m pytest tests/test_auth.py tests/test_appointments.py -q
```

---

## License

Private — All rights reserved.

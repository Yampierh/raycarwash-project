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
│   │   ├── auth/                   # JWT (RS256), OAuth2 social, WebAuthn passkeys, lockout
│   │   │   └── routers/            # Split: core, social, webauthn, sessions, password, email
│   │   ├── admin/                  # Admin dashboard API — users, roles, permissions CRUD
│   │   ├── users/                  # Registration, profiles, onboarding
│   │   ├── providers/              # Detailer profiles, Stripe Identity verification
│   │   ├── vehicles/               # Vehicle CRUD, NHTSA VIN lookup
│   │   ├── appointments/           # FSM booking lifecycle, availability slots
│   │   ├── matching/               # H3 geospatial + scoring engine
│   │   ├── payments/               # Stripe intents, webhooks, fare estimation, ledger
│   │   ├── services_catalog/       # Service + addon catalogue
│   │   ├── reviews/                # Rating aggregation
│   │   ├── notifications/          # Push notifications — Expo Push API, device tokens
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
│   └── app/                        # Stable infrastructure (config, seed, security)
│       ├── core/                   # config.py, security.py, limiter.py
│       └── db/                     # seed.py, seed_rbac.py (roles + permissions), detailer_seed.py
│
├── frontend/                       # React Native · Expo · TypeScript
│   └── src/
│       ├── screens/                # 21 screen components
│       ├── services/               # API service files
│       ├── hooks/                  # useAppointmentSocket
│       ├── store/                  # authStore (Zustand)
│       ├── navigation/             # RootStack, MainTabs, DetailerTabs
│       └── theme/
│
├── web/                            # Next.js 15 · TypeScript · Tailwind — Admin dashboard
│   └── app/
│       ├── login/                  # Admin login page
│       └── dashboard/              # Overview · Users · Roles · Permissions
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

# 6. (Optional) Start admin dashboard
cd web && npm install && npm run dev
```

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Expo (frontend) | http://localhost:8081 |
| Admin dashboard | http://localhost:3000 |

---

## Environment variables

**Backend** — `backend/.env`:
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/raycarwash

# JWT signing — RS256 asymmetric key pair (replaces old JWT_SECRET_KEY)
# Generate: openssl genrsa -out jwt_private.pem 2048 && openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem
# Store as single-line with \n: JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
JWT_PRIVATE_KEY=<PEM-encoded RSA-2048 private key>
JWT_PUBLIC_KEY=<PEM-encoded RSA-2048 public key>

ENCRYPTION_KEY=your-32-char-encryption-key-here   # PII encryption (separate from JWT)
PHONE_LOOKUP_KEY=your-32-char-lookup-key-here      # Phone hash for dedup
DEBUG=true

# Optional integrations
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
SMTP_ENABLED=false
GOOGLE_CLIENT_ID=
APPLE_BUNDLE_ID=com.raycarwash.app
REDIS_URL=redis://localhost:6379
REQUIRE_EMAIL_VERIFICATION=false
```

**Frontend** — `frontend/.env.local`:
```
EXPO_PUBLIC_API_URL=http://localhost:8000
```

**Admin dashboard** — `web/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
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
| `cd web && npm run dev` | Admin dashboard (Next.js on port 3000) |

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

### Frontend (mobile)

- React Native (Expo)
- React Navigation
- Axios + WebSocket
- Zustand (auth store)
- expo-secure-store

### Admin dashboard

- Next.js 15 (App Router)
- TypeScript + Tailwind CSS
- TanStack Table (server-side pagination)

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

### Client

1. Register (email + password)
2. Complete profile (name + phone) → assigned `client` role
3. Add vehicle (VIN lookup via NHTSA or manual)
4. Payment method (Stripe)
5. Home — ready to book

**Blocking steps**: vehicle + payment. Everything else is optional.

### Detailer

1. Register + toggle "Become a Service Provider"
2. Select service type (Detailer — Mechanic/Wash coming Sprint 7)
3. Complete profile (name + phone) → assigned `detailer` role
4. DetailerOnboarding wizard:
   a. Personal info (legal name, DOB, address)
   b. Identity verification (Stripe Identity — may take minutes/hours)
   c. Consent + background check
   d. Confirmation
5. Dashboard — ready to receive jobs

**Blocking steps**: identity verification (step 4b). Cannot receive payments without KYC approval.

---

## Sprint roadmap

| Sprint | Status | Key features |
|---|---|---|
| 1 | ✅ Done | Project skeleton, DB setup |
| 2 | ✅ Done | Auth (identifier-first), vehicles, reviews |
| 3 | ✅ Done | Appointments, services, Stripe payments, state machine |
| 4 | ✅ Done | Detailer discovery, webhooks, refund policy, timezone scheduling, rate limiting, social login |
| 5 | ✅ Done | Addons, multi-vehicle bookings, smart matching, email service |
| 6 | ✅ Done | DDD-lite refactor, WebAuthn passkeys, Stripe Identity, H3 geospatial, auto-assignment, WebSocket real-time |
| 7 | ✅ Done | Auth hardening: RS256 JWT, stateful email/WebAuthn tokens, lazy loading fix, auth router split, admin domain + dashboard |
| 8 | 🚧 In progress | Push notifications (Expo Push API ✅), user flow + admin tests 44/44 ✅, TOTP/2FA, mechanic vertical |

---

## Test status

```text
tests/test_auth.py         70/70  ✅ all pass  (includes role-escalation security test)
tests/test_appointments.py 19/19  ✅ all pass
tests/test_user_flows.py   17/17  ✅ all pass  (client + detailer registration flows)
tests/test_admin.py        27/27  ✅ all pass  (all /api/v1/admin/* endpoints)
tests/test_detailers.py    ~pass  (profile fixture edge cases pending)
tests/test_matching.py     ~pass  (H3 index requires real Redis for spatial tests)
tests/test_vehicles.py     ~pass  (body_class / onboarding edge cases pending)
```

Run tests:

```bash
cd backend
python -m pytest tests/test_auth.py tests/test_appointments.py tests/test_user_flows.py tests/test_admin.py -q
```

---

## License

Private — All rights reserved.

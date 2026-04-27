# RayCarWash

Mobile vehicle services marketplace — Fort Wayne, IN.

Connects clients with mobile service providers (detailers, mechanics, and more) who come to the client's location. Think Uber, but for car care.

> **Current phase**: Detailing vertical — getting it 100% functional before expanding to multiservice.

---

## Project structure

```
raycarwash-project/
├── backend/                        # FastAPI · Python 3.11+ · PostgreSQL
│   ├── main.py                     # App factory, router registration, lifespan hooks
│   ├── requirements.txt
│   └── app/
│       ├── core/                   # config.py (Pydantic settings), limiter.py (slowapi)
│       ├── db/                     # session.py, seed.py, detailer_seed.py
│       ├── models/models.py        # All SQLAlchemy ORM models
│       ├── schemas/schemas.py      # All Pydantic v2 schemas
│       ├── repositories/           # Data access layer (8 repos)
│       ├── services/               # Business logic layer
│       ├── routers/                # FastAPI route handlers (10 routers)
│       └── ws/                     # WebSocket connection manager + router
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
- SQLAlchemy async (asyncpg)
- PostgreSQL 14+
- Pydantic v2
- Alembic (migrations)
- Stripe SDK v11 + Stripe Identity
- WebAuthn (passkeys)
- slowapi (rate limiting)

### Frontend
- React Native (Expo)
- React Navigation
- Axios + WebSocket
- Zustand (auth store)
- expo-secure-store

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
| 6 | 🔄 In progress | Security hardening, push notifications, admin dashboard, test coverage |
| 7 | 📋 Planned | Multiservice: ServiceCategory model, mechanic vertical, provider onboarding by type |

---

## License

Private — All rights reserved.
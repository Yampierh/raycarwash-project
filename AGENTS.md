# AGENTS.md — RayCarWash

Mobile vehicle services marketplace (Fort Wayne, IN). Monorepo with no monorepo tool — `concurrently` orchestrates services.

| Dir | Stack | Port |
|---|---|---|
| `backend/` | FastAPI + PostgreSQL + Redis | `:8000` |
| `frontend/` | React Native + Expo 54 | `:8081` |
| `web/admin/` | Next.js 16 admin dashboard | `:3000` |
| `web/portal/` | Next.js 16 + next-intl public site + provider portal | `:3001` |

---

## Commands

```bash
npm run install          # npm deps for frontend + backend
npm run install-deps     # python venv + pip install -r requirements.txt
npm run dev              # backend + frontend concurrently
npm run dev:backend      # uvicorn main:app --reload --host 0.0.0.0 --port 8000
npm run dev:admin        # Next.js admin on :3000
npm run dev:portal       # Next.js portal on :3001

cd backend
python -m pytest \
  tests/test_auth.py tests/test_appointments.py tests/test_user_flows.py tests/test_admin.py \
  tests/test_appointments_cancel.py tests/test_public_endpoints.py \
  tests/test_idempotency_body_hash.py tests/test_idempotency_v2_user_scope.py \
  tests/test_rate_limit_handler.py tests/test_users_provider_profile.py -q

cd backend && alembic upgrade head
```

---

## Two Axios clients (frontend — most common mistake)

```ts
authClient  → base /auth      (register, login, complete-profile, social, refresh, sessions, passkeys)
apiClient   → base /api/v1    (everything else)
```

- **Never mix.** Auth endpoints are at `/auth`, not `/api/v1/auth`.
- `authClient` injects `access_token ?? onboarding_token` (supports mid-onboarding).
- `apiClient` injects `access_token` only. Auto-refresh on 401 with concurrent-request queuing.

---

## Auth flow

```
POST /auth/identify  → { is_new_user, available_methods }
POST /auth/verify    → { access_token, refresh_token } | { onboarding_token }
PUT  /auth/complete-profile [Bearer onboarding_token] → { access_token, refresh_token }
```

Three token types:
- **access** — 30 min, RS256 signed. JWKS at `GET /.well-known/jwks.json`.
- **refresh** — 7 days, opaque SHA-256 hash, single-use. Theft detection via family revocation.
- **onboarding** — 30 min, scoped to `/auth/complete-profile` only.

SecureStore keys: `raycarwash_jwt_token`, `raycarwash_onboarding_token`, `raycarwash_refresh_token`.

`PUT /auth/complete-profile` returns 403 if `onboarding_status == "completed"` (prevents KYC bypass).

---

## Architecture: DDD-lite

`domains/X` imports from `domains/Y`, `infrastructure/`, or `shared/` directly. No shims.

```
backend/
├── main.py                 # composition root: lifespan, middleware, health, seed
├── api/router.py           # aggregates all domain routers
├── domains/{auth,admin,users,providers,vehicles,appointments,
│           services_catalog,reviews,payments,matching,realtime,audit,
│           notifications,public,locations}
├── infrastructure/{db,redis,email,nhtsa,h3,stripe}
├── shared/schemas.py       # Envelope[T], PaginatedEnvelope[T], ErrorEnvelope
├── workers/                # background asyncio: location, assignment, audit redaction
└── app/core/ + app/db/    # config, security, seed data (stable, not domain code)
```

`infrastructure/db/registry.py` must be imported by `main.py` before any model usage (registers all models with SQLAlchemy).

Middleware stack (execution order): RequestID → StructuredLogging → AuditContext → Idempotency.

---

## Key business rules

- **Prices in integer cents.** Never floats. Display: `/ 100`.
- **estimated_price is immutable.** Set once at creation. `actual_price` set on COMPLETED.
- **VehicleSize is runtime-derived** via `map_body_to_size(body_class)`. Never stored — do NOT add a `size` column.
- **Appointment FSM**: PENDING → CONFIRMED → ARRIVED → IN_PROGRESS → COMPLETED (+ cancellations).
- **Cancellation refunds**: ≥24h 100% · 2–24h 50% · <2h 0%.
- **Soft deletes** on every entity (`is_deleted` + `deleted_at`). Always filter. Never hard-delete.
- **Double-booking prevention**: `pg_advisory_xact_lock(detailer_uuid_hash)` inside appointment creation. Must be inside `async with session.begin()`.
- **PII encrypted at rest** via `EncryptedType` with separate `ENCRYPTION_KEY`.
- **Body size limit**: 5 MB (Stripe webhooks exempted via `webhook_router` prefix).
- **Timestamps are UTC.** Convert to local only for display.

---

## Admin

Default credentials (seeded on first startup): `admin@raycarwash.com` / `Admin1234!`.

All endpoints at `/api/v1/admin/*` require `role=admin` Bearer. Force-status (`PATCH /admin/appointments/{id}/status`) bypasses FSM but writes to audit log.

---

## WebSocket

```
WS /ws/appointments/{id}?token=<access_token>
```

JWT in query param (headers unavailable post-handshake). Frontend hook: `useAppointmentSocket` (exponential backoff, 30s heartbeat).

---

## web/ workspace

`web/admin/AGENTS.md` warns: this Next.js version may differ from training data. **Read `node_modules/next/dist/docs/` before writing code there.**  
`web/portal/` is the public site + provider portal (no version warning — same Next.js 16).

---

## Test quirks

| Test | Count | Notes |
|---|---|---|
| `test_auth.py` | 70/70 | Includes role-escalation security test |
| `test_appointments.py` | 19/19 | All pass |
| `test_user_flows.py` | 17/17 | Client + detailer registration flows |
| `test_admin.py` | 27/27 | Users/roles/permissions |
| `test_appointments_cancel.py` | 8/8 | Plan 21 §2 — customer cancel wrapper of FSM, refund preview policy |
| `test_idempotency_body_hash.py` | 7/7 | Body-hash isolation under the v2 dep (Plan 22 §6.1.3) |
| `test_idempotency_v2_user_scope.py` | 4/4 | H1 cross-user collision regression (Plan 22 §6.1.3) |
| `test_rate_limit_handler.py` | 3/3 | Envelope-shaped 429 + Retry-After (Plan 19 §10) |
| `test_public_endpoints.py` | 28/28 | Plan 19 Track 1 — all 9 public endpoints |
| `test_users_provider_profile.py` | 18/18 | Plan 24 Wave 1: signup fields (ssn/city/tank/skills) + submit endpoint |
| `test_users_addresses.py` | 12/12 | Plan 24 Wave 1 C-3: opt-in ZIP coverage gate |
| `test_vehicle_price_estimate.py` | 9/9 | Plan 24 Wave 1 C-1: anonymous price preview |
| `test_detailers.py` | ⚠️ | Edge cases (profile fixture) |
| `test_matching.py` | ⚠️ | Requires real Redis (H3 spatial) |
| `test_vehicles.py` | ⚠️ | body_class / onboarding edge cases |

Standard green suite (above, excluding the ⚠️ files): **224/224** in ~5 min.

Sprint 9 admin extensions (appointments/verifications/payments) ship without dedicated tests.

`backend/tests/conftest.py` drops/recreates all tables + explicit enum cleanup (`DROP TYPE IF EXISTS`). Async tests use `pytest-asyncio` with `asyncio_mode = auto`.

---

## Backend conventions

- **Async SQLAlchemy 2.0**: `select()`, `await session.execute()`. Never legacy `query()`.
- **Repositories** own all DB access. Services have zero SQL.
- **Audit log** every mutation (append-only, 90-day full JSONB → redacted → Glacier).
- **Response envelope**: `response_model=Envelope[T]` on every v1 endpoint. `EnvelopeRouter` raises at boot if a route is non-compliant. CI test `test_envelope_compliance.py` enforces this.
- **Structured JSON logging** with `X-Request-ID` propagation.
- **Idempotency-Key** middleware (Redis-backed) for payment-sensitive endpoints.

---

## Push notifications

Expo Push API (no Firebase needed). Tokens: `ExponentPushToken[...]`. Register on login via `POST /api/v1/notifications/device-token`. Unregister on logout via `DELETE`. Events drive push via `domains/notifications/handlers.py` on every appointment state transition.

---

## Mobile UI components

`frontend/src/components/`: Button (5 variants), Card, StatusBadge, EmptyState, SectionHeader, Typography, AnimatedInput. Use these — never inline `<TouchableOpacity>`. Theme tokens in `frontend/src/theme/colors.ts` with semantic keys (`Colors.bg.*`, `Colors.textColor.*`, `Colors.status.*`, `Spacing`, `Radius`, `TypographyScale`). Legacy flat keys preserved for backward compat.

---

---

## Documentation Map

The single entry point for all project documentation, plans, and audits is [`docs/INDEX.md`](./docs/INDEX.md).

| Category | Location | Description |
|-----------|----------|-------------|
| **Manifest** | [`docs/INDEX.md`](./docs/INDEX.md) | Central index — maps all plans, status, and audit cross-refs |
| **Master Plan** | [`/plan.md`](./plan.md) | Profile system Phases 0–9 (read-only until implementation) |
| **Integration Plans** | [`docs/integration_plans/`](./docs/integration_plans/) | 5 vertical plans (00-user through 04-vehicles) |
| **Technical Audit** | [`docs/audit/`](./docs/audit/) | ~60 findings across architecture, tests, infra, web, DB |
| **Operational Plans** | [`docs/plans/`](./docs/plans/) | CI/CD, infrastructure, observability, hardening |

**New plans**: Create in `docs/plans/{NN}-{name}.md`, then register in `docs/INDEX.md` section 3.

---

## Hard constraints

The file `.claude/execution_protocol.md` defines a mandatory pipeline for ALL backend changes: ARCHITECTURE → CONTRACTS → DOMAIN SKILL → IMPLEMENTATION → OBSERVABILITY → VALIDATION. Claude Code must treat this as hard constraints, not suggestions.

---

## Team Protocol

See [`docs/AGENT_PROMPT.md`](./docs/AGENT_PROMPT.md) — el equipo de desarrollo 2026 audita todo plan de implementación antes de ejecutar.

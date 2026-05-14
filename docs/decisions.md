# Technical Decisions & Audit Log

Source of truth for architectural choices, bugs found/fixed, and pending work.

---

## Architectural decisions

### Identifier-first auth (Sprint 2)

Three-step flow modeled after Uber: identify → verify → complete-profile.
User types their email/phone once; the system decides login vs register.

- `POST /auth/identify` — returns `is_new_user`
- `POST /auth/verify` — returns tokens (existing) or `onboarding_token` (new)
- `PUT /auth/complete-profile` — name, phone, role → full tokens

### Two Axios clients

`authClient` (`/auth`) and `apiClient` (`/api/v1`) are separate intentionally.
Auth endpoints live at `/auth`, not `/api/v1/auth`. Mixing causes 404.

### VehicleSize is runtime-derived (never stored)

`body_class` is stored on Vehicle. `VehicleSize` (small/medium/large/xl) is derived
from it at runtime via `map_body_to_size()`. Keeps pricing flexible without migrations.

### Prices in integer cents

All monetary values are integer cents. Never floats. Display: `/ 100`.

### estimated_price is immutable

Set once at appointment creation. `actual_price` is set separately on COMPLETED.
These are two distinct fields — do not merge them.

### Soft deletes everywhere

`is_deleted + deleted_at` on every entity. No hard deletes. Preserves full audit trail.

### Advisory locks for appointment creation

`pg_advisory_xact_lock(detailer_uuid_hash)` inside appointment creation prevents
double-booking race conditions at the DB level without requiring `SERIALIZABLE` isolation.

### DDD-lite architecture (Sprint 6)

Refactored monolithic `app/` into `domains/` + `infrastructure/` + `workers/` + `shared/`.
Each domain owns its models, schemas, repository, service, and router.
No shim files — direct imports between domains.

### Append-only payment ledger

`PaymentLedger` + `LedgerSeal` (daily SHA-256 hash) for financial audit trail.
`PaymentCoordinator` (service_v2) handles authorization → capture → refund lifecycle.

### H3 geospatial indexing

Detailer locations indexed at H3 resolution 7 in Redis + PostgreSQL.
`find_nearby_detailers()` uses H3 ring expansion for O(1) proximity lookup.

### Fireball filter (location worker)

GPS updates are deduplicated before writing to DB: skip if moved < N meters
AND heading change < N degrees. Prevents DB thrash from stationary detailers.

### RS256 JWT + JWKS (Sprint 7)

JWT signing moved from HS256 shared secret to RS256 asymmetric. Private key signs
only on the auth service; any internal service can verify tokens by pulling the
public key set from `GET /.well-known/jwks.json`. Lets future microservices verify
tokens without distributing a secret.

### Stateful email-verification + WebAuthn challenge tokens (Sprint 7)

Email-verification tokens are now DB-backed in `email_verification_tokens`
(single-use, revocable) instead of stateless JWT — prevents replay after logout.
WebAuthn challenges are stored in Redis (`webauthn_challenge:{session_id}`, TTL 5 min)
and consumed on verify.

### Auth router split (Sprint 7)

`domains/auth/router.py` (one giant file) was split into `domains/auth/routers/`
sub-routers by concern: `core`, `social`, `webauthn`, `sessions`, `password`,
`email_verification`. Assembled into a single `auth_router` in `routers/__init__.py`.
Makes ownership and route audits much faster.

### Onboarding-completion lockout (Sprint 7)

`PUT /auth/complete-profile` returns 403 once `onboarding_status == "completed"`.
Without this, a logged-in client could call complete-profile with `role=detailer`
and self-promote to the detailer side, bypassing KYC.

### Default admin user seeded on first startup (Sprint 8)

`app/db/seed_rbac.py::_seed_admin_user` creates `admin@raycarwash.com` / `Admin1234!`
on first boot if no user with that email exists. Idempotent and dev-only —
the password must be changed before deploying to production.

### Push notifications via Expo Push API (Sprint 8)

Chose Expo Push over Firebase to avoid maintaining a Firebase project on the
managed-Expo workflow. Tokens (`ExponentPushToken[…]`) are stored in
`device_tokens` and dispatched via in-process event-bus handlers
(`domains/notifications/handlers.py`) on every appointment-state transition.

### Mobile UI consistency system (Sprint 9)

All 21 screens were standardized onto a shared component library at
`frontend/src/components/` (Button, Card, StatusBadge, EmptyState, SectionHeader,
Typography, AnimatedInput) plus semantic theme tokens
(`Colors.bg/textColor/border/status`, `Spacing`, `Radius`, `TypographyScale`).
Removed 50+ duplicated inline button/pill/empty-state definitions and replaced
ad-hoc `fontWeight: "bold"`, hex color literals, and inconsistent padding
(16px ↔ 20px) with named tokens. Legacy `Colors.*` flat keys are preserved
for backward compatibility.

### Admin force-status override (Sprint 9)

`PATCH /api/v1/admin/appointments/{id}/status` lets an admin set any status,
bypassing the normal FSM transitions. Necessary for ops recovery (stuck
appointments, missed COMPLETED, disputed cancellations). Every override writes
to the audit log; the FSM remains authoritative for normal client/detailer
calls.

---

## Bugs found and fixed

### Sprint 2

| # | Severity | Component | Description |
|---|---|---|---|
| 1 | Critical | `auth.service.ts` | Refresh token sent as JSON body — backend expects query param |
| 2 | Critical | `auth.service.ts` | Social auth called via `apiClient` → 404. Fixed: use `authClient` |
| 3 | High | `auth_router.py` | `service_address` in UserUpdate pointed to nonexistent column |
| 4 | Critical | `auth.py` | `get_current_user()` didn't eager-load `user_roles` → `is_client()` always False |

### Sprint 6 — security audit (April 2026)

| # | Severity | Component | Description |
|---|---|---|---|
| 1 | Critical | `webhook_router.py` | Bare `except Exception` intercepted system errors. Narrowed to specific types |
| 2 | High | `payment_service.py` | `stripe.api_key` assigned inside each method. Moved to module level |
| 3 | High | `auth_router.py` | Social provider detected by string heuristic. Fixed: explicit `provider` field |
| 4 | Medium | `auth_router.py` | Role assignment via nonexistent attribute. Fixed: use `UserRoleAssociation` |
| 5 | Medium | `config.py` | `STRIPE_SECRET_KEY` validator didn't reject invalid formats |
| 6 | Low | `schemas.py` | 9 request schemas repeated `model_config`. Extracted to `_BaseRequestSchema` |

### Sprint 6 — WebSocket + ARRIVED (April 2026)

| # | Severity | Component | Description |
|---|---|---|---|
| 1 | High | `detailer_repository.py` | `update_location` did UPDATE on `User` — fields live on `ProviderProfile` |
| 2 | High | `appointment_service.py` | RBAC check used `actor.role ==` (singular). Fixed: `actor.has_role()` |
| 3 | Medium | `appointment_service.py` | `service_duration_minutes` unbound if service not found → `UnboundLocalError` |

### Sprint 6 — DDD migration (April 2026)

| # | Severity | Component | Description |
|---|---|---|---|
| 1 | Bug | `seed.py` | `seed_service_categories` called `select(ServiceCategory)` on the Python enum instead of `ServiceCategoryTable` (ORM model). Fixed. |
| 2 | Bug | `conftest.py` | `drop_all` leaves PostgreSQL ENUM types behind; next `create_all` fails. Fixed: drop enums explicitly before `create_all`. |
| 3 | Bug | `tests/` | `ProviderProfile` created twice for `test_detailer` (fixture + inline). Fixed: conftest creates full profile. |
| 4 | Bug | `test_appointments.py` | Past dates in scheduled_time rejected by validator. Fixed: all dates → 2027. |
| 5 | Bug | `AppointmentRead` schema | `estimated_end_time` / `travel_buffer_end_time` required but nullable in model. Made Optional. |

---

## Security properties (verified good — no action needed)

- JWT with explicit `type` claim — prevents token confusion attacks
- bcrypt via passlib — correct rounds
- `dummy_verify()` — timing-safe even for nonexistent users
- Rate limiting on all auth endpoints (slowapi)
- SQL injection protected via SQLAlchemy ORM (parameterized queries)
- Stripe webhook HMAC-SHA256 verified (`Stripe-Signature`)
- Soft deletes preserve full audit trail
- PII encrypted at rest (`EncryptedType` with separate `ENCRYPTION_KEY`)
- Request body limit: 5 MB (Stripe webhooks exempted)
- CORS configurable via env
- WebSocket auth via query param JWT (correct pattern — headers unavailable post-handshake)

---

## Sprint changelog

### Sprint 6 deliverables

| Feature | Status |
|---|---|
| DDD-lite refactor (domains/, infrastructure/, workers/, shared/) | ✅ Done |
| Structured JSON logging + `X-Request-ID` propagation | ✅ Done |
| WebAuthn passkeys (4 endpoints) | ✅ Done |
| Stripe Identity verification (4-step wizard + dev bypass) | ✅ Done |
| H3 geospatial indexing + auto-assignment engine | ✅ Done |
| Append-only payment ledger (LedgerSeal) | ✅ Done |
| WebSocket real-time tracking (ARRIVED state, GPS) | ✅ Done |
| Test suite stabilized (auth: 69/69, appointments: 19/19) | ✅ Done |

### Sprint 7 deliverables

| Feature | Status |
|---|---|
| RS256 JWT + JWKS public-key verification | ✅ Done |
| Stateful email-verification tokens (replaces stateless JWT) | ✅ Done |
| WebAuthn challenges in Redis (TTL 5 min) | ✅ Done |
| Auth router split into `domains/auth/routers/*` by concern | ✅ Done |
| `domains/admin` + 16 RBAC endpoints (users / roles / permissions) | ✅ Done |
| Next.js 15 admin dashboard (`web/`) with auth-gated pages | ✅ Done |
| Onboarding-completion lockout (prevents role escalation) | ✅ Done |
| Lazy-loading fix for `get_current_user()` user_roles | ✅ Done |
| `test_auth.py` expanded to 70/70 (includes role-escalation test) | ✅ Done |

### Sprint 8 deliverables

| Feature | Status |
|---|---|
| Push notifications via Expo Push API (`domains/notifications`) | ✅ Done |
| Event-bus → push triggers on every appointment state transition | ✅ Done |
| `usePushNotifications` hook + `clearAuthTokens()` unregister-on-logout | ✅ Done |
| Default admin user seeded on first startup | ✅ Done |
| `test_user_flows.py` (17/17) + `test_admin.py` (27/27) | ✅ Done |
| `expo-device` dependency added (required by push hook) | ✅ Done |

### Sprint 9 deliverables

| Feature | Status |
|---|---|
| Admin appointments queue + force-status override (3 endpoints) | ✅ Done |
| Admin detailer verifications queue (approve / reject with reason) | ✅ Done |
| Admin payments — ledger + 4-card revenue summary | ✅ Done |
| Web dashboard: `/appointments`, `/verifications`, `/payments` + sidebar update | ✅ Done |
| Shared mobile component system (Button, Card, StatusBadge, EmptyState, SectionHeader, Typography, AnimatedInput) | ✅ Done |
| Semantic theme tokens (`Colors.bg/textColor/border/status`, `Spacing`, `Radius`, `TypographyScale`) | ✅ Done |
| 21 screens refactored — 50+ inline buttons eliminated, padding/fontWeight/borderRadius standardized | ✅ Done |

### Pending (Sprint 10)

- TOTP / 2FA for admin accounts
- Mechanic vertical: `ServiceCategory` enforcement, provider type on `ProviderProfile`, category-specific onboarding
- Frontend: category-selection screen before matching
- Test coverage for Sprint 9 admin endpoints (appointments / verifications / payments)
- Public marketing site (`marketing/` Next.js 16 + next-intl workspace)
- Fix remaining edge-case test failures (vehicles, detailers, matching)

---

## Known pitfalls (save yourself debugging time)

- **VehicleSize is never stored** — derived from `body_class` at runtime. Do not add a `size` column to Vehicle.
- **Two Axios clients** — `authClient` for `/auth`, `apiClient` for `/api/v1`. Never mix.
- **WS auth** — JWT in query param (`?token=`). Headers not available post-handshake.
- **Soft deletes** — always filter `Model.is_deleted == False`. Never hard-delete.
- **Social-only users** — have unusable bcrypt hash. Check `google_id`/`apple_id` before attempting password login.
- **Advisory lock scope** — per-detailer, transaction-scoped. Must be inside `async with session.begin()`.
- **estimated_price is immutable** — set once at creation. Never update after.
- **Timestamps are UTC** — convert to local only for display. All DB values are UTC.
- **Prices are cents** — always integer cents. Display: `/ 100`. Never floats.
- **CORS** — frontend on port 8081, backend allows this by default. Update `ALLOWED_ORIGINS` for production.

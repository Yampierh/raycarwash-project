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

---

## Profile system — Architectural Decision Records (Phase 0+)

Materialized from `~/.claude/plans/estoy-construyendo-una-app-composed-kahan.md`.
Each ADR is dated, status-tagged, and references the plan section it implements.

### ADR-001: Strict separation `/api/v1/auth/*` vs `/api/v1/users/me/*`

- **Status**: Accepted (2026-05-14).
- **Context**: legacy endpoints fragment user data across `/auth/me`, `/auth/update`, `/api/v1/detailers/me`, `/api/v1/vehicles`, `/api/v1/notifications/device-token`. Frontend hits 3-4 endpoints just to open the profile screen.
- **Decision**: split into two domains. `/api/v1/auth/*` owns credentials, sessions, passkeys, 2FA, and password change. `/api/v1/users/me/*` owns persona, preferences, vehicles, addresses, payment methods, GDPR, and provider sub-resources.
- **Consequences**:
  - (+) Strict SRP; independent testability; clean OpenAPI tags.
  - (+) Frontend talks to one domain per intent.
  - (-) Helpers must be cross-domain (e.g. `security` block in Profile Hub delegates to auth's `AuthBlockProvider`). Mitigated by composition, not inheritance.
  - (-) Legacy endpoints stay live 2 sprints with `Deprecation` + `Sunset` headers (RFC 8594) before returning 410.
- **Rejected alternatives**: aliasing `/users/me/security/*` to `/auth/*` (dilutes responsibility); aggregator namespace `/api/v1/profile/*` over the fragmented domains (still fragmented underneath).

### ADR-002: `?include=` opt-in for sub-resources (superseded by ADR-002b)

- **Status**: Accepted 2026-05-14, **Superseded by ADR-002b on 2026-05-15**.
- **Context**: `GET /users/me` was growing into a pile of optional fields (`stats`, `security_summary`, `defaults`, ...) with COUNTs that made the default response slow.
- **Decision**: default response is minimal; clients opt in to extras via `?include=stats,security_summary,defaults,provider_private,recent_activity`.
- **Consequences**: fast default Hub, no breaking changes when new tokens ship, granular cache keys. Two requests in flight if both base + extras needed (React Query handles dedup).

### ADR-002b: Profile Hub with composite block shape

- **Status**: Accepted (2026-05-15). **Supersedes ADR-002.**
- **Context**: ADR-002's payload was flat (loose fields). Scaling to 11+ sub-resources made the response hard to render block-by-block on the frontend.
- **Decision**: `data` is a composite object — `{user, verification_badges, profile?, vehicles?, favorites?, sessions?, security?, provider?, addresses?, payment_methods?, preferences?, notifications?, stats?}`. Only `user` and `verification_badges` are always present. All others are opt-in via `?include=`. `meta.includes` echoes what was actually returned. Step-up applies to the sensitive tokens (`security`, `sessions`); `?on_step_up=skip` opts into degraded responses instead of 401.
- **Consequences**:
  - (+) Predictable, self-contained blocks; trivial to cache and render.
  - (+) Frontend asks per-screen for exactly what it needs (`profile,stats` on launch; `security,sessions` only on SecurityScreen).
  - (+) Granular step-up — sensitive tokens gate independently.
  - (+) Future-friendly: `?fields[block]=...` (sparse fieldsets) can ship later without breaking changes.
  - (-) Slightly heavier orchestration in `ProfileHubService` — mitigated with `to_hub_block(user)` adapters on each sub-service.
- **Rejected alternatives**: flat shape (ADR-002 — does not scale visually); separate endpoints per block (`/users/me/profile`, `/users/me/security`) — re-introduces N+1 calls and breaks caching.

### ADR-003: Refresh rotation on active-role switch

- **Status**: Accepted (2026-05-14).
- **Context**: `PATCH /users/me/active-role` changes the JWT `role` claim. Without rotation, a refresh stolen before the switch could keep issuing access tokens for the old role for up to `REFRESH_TOKEN_EXPIRE_DAYS` (7).
- **Decision**: rotate the refresh token family on every successful switch — same flow as password change. New access + refresh are returned together.
- **Consequences**:
  - (+) Closes the stolen-refresh window for cross-role escalation.
  - (-) Frontend must persist both new tokens to `SecureStore` after the call — same flow already used after `/auth/password/change`.
- **Rejected alternatives**: leave refresh untouched (unacceptable risk); bump `token_version` (kills every session, too invasive for a routine switch).

### ADR-004: Step-up auth with Redis primary + DB fallback

- **Status**: Accepted (2026-05-14).
- **Context**: `require_step_up()` reads a `last_auth_at` timestamp ≤5min old to decide whether to grant sensitive operations. Sole-Redis storage would mean a Redis outage blocks email/phone change, 2FA changes, and payment method add — even for users who literally just authenticated.
- **Decision**: dual-layer. Redis key `auth:stepup:{user_id}` is primary (TTL = `STEP_UP_TTL_MINUTES`); column `users.last_step_up_at` is populated on every successful auth (login, password verify, OAuth verify, passkey verify) as fallback. The dependency tries Redis first, then DB.
- **Consequences**:
  - (+) Availability: Redis outage does not lock users out of profile operations they just authenticated for.
  - (+) Same TTL threshold in both layers — no behavioral drift.
  - (-) Every successful auth runs one extra `UPDATE users` — negligible.

### ADR-005: Specialized histories beat a single feed

- **Status**: Accepted (2026-05-14).
- **Context**: a single `/users/me/activity` mixing appointments, payments, reviews, profile changes, and security events would force every consumer to filter by `type` and would resist DB indexing (each row type has different optimal indexes).
- **Decision**: five specialized endpoints with purpose-built indexes:
  - `/api/v1/auth/history` (logins + security AuditLog filtered)
  - `/api/v1/users/me/appointments/history`
  - `/api/v1/users/me/payments/history`
  - `/api/v1/users/me/vehicles/history`
  - `/api/v1/users/me/profile-changes`

  Plus an optional `/api/v1/users/me/activity` *summary* that aggregates the first four — capped, not deep-paginatable.
- **Consequences**:
  - (+) Each list gets its own index; cursor pagination stays efficient.
  - (+) Filters are first-class (`?status=`, `?vehicle_id=`, `?action=`).
  - (+) Frontend renders one type per screen — no big if/elif tables.
  - (-) More routes to maintain; mitigated by sharing the underlying services.
- **Important**: the unified `/activity` feed *excludes* security events to keep `/auth/history` the single source of truth for that data.

### ADR-006: Append-only audit_log with 90-day redaction

- **Status**: Accepted (2026-05-14).
- **Context**: `audit_logs.old_value` / `new_value` are JSONB and may contain PII (old email, old phone, old address) for every mutation. Left unbounded the table grows fast and violates GDPR data-minimization.
- **Decision**: three retention tiers:
  - 0-90 days → full JSONB.
  - 90 days-3 years → sensitive fields redacted (`old_value` and `new_value` rewritten with a `{"redacted": true, "fields": [...]}` marker); structural fields (`action`, `entity_type`, `entity_id`, `actor_id`, `created_at`, `ip_address`) survive.
  - >3 years → non-security/non-financial rows archived to Glacier and deleted from Postgres. Security and financial rows are retained indefinitely for compliance.
- **Consequences**:
  - (+) GDPR-compatible while keeping forensic chain.
  - (+) Postgres `audit_logs` size stays bounded.
  - (-) Forensics past 90 days requires restoring from Glacier.
- **Worker**: `workers/audit_log_redactor.py` (Phase 9 or earlier).

### ADR-007: Response envelope is explicit, not middleware

- **Status**: Accepted (2026-05-14).
- **Context**: the `{data, meta, links}` envelope could be applied either as a global middleware that wraps any return value, or declared on each endpoint via `response_model=Envelope[T]`.
- **Decision**: explicit `response_model=Envelope[T]` on every endpoint under `/api/v1/users/me/*` and Phase 0+ auth endpoints. Enforcement at startup via `EnvelopeRouter` (`app/core/envelope_router.py`) — registering a route without a compliant `response_model` raises `EnvelopeContractError` before the app boots. A CI test (`tests/test_envelope_compliance.py`) walks `app.router.routes` and fails if any non-legacy route slips through.
- **Consequences**:
  - (+) OpenAPI mirrors the wire shape with concrete types.
  - (+) No per-request middleware overhead.
  - (+) Mistakes fail loud and early.
  - (-) Boilerplate per endpoint — mitigated by generics.

### ADR-008: Two S3 buckets, separated by data sensitivity

- **Status**: Accepted (2026-05-14).
- **Decision**: two logical buckets behind `FileStorageAdapter`:
  - `public-assets`: avatars, cover images, vehicle photos, provider portfolio. CloudFront-fronted, signed URLs valid 24 h.
  - `private-docs`: KYC docs, insurance, data exports. SSE-KMS encrypted, no CDN, presigned URLs valid 1 h.

  In development both map to `STORAGE_LOCAL_PATH/{bucket}/{key}` via `LocalStorageAdapter`. The dev `/dev/upload` endpoint validates an HMAC signature before writing.
- **Consequences**:
  - (+) PCI/PII surface contained to the private bucket and never crosses the CDN.
  - (+) Public assets served fast through CloudFront without backend round-trips.
  - (-) Two storage pipelines to provision — both share the same adapter interface, so no code duplication.

---

## Phase 0 implementation notes (2026-05-14)

Phase 0 ships in four chunks on branch `feat/profile-phase0`:

- **Chunk A** (`7d28ec4`): `Envelope[T]` generics, `app/core/{cursor,idempotency,step_up,deprecation,envelope_router}.py`, `app/middleware/{request_id,structured_logging,audit_context}.py`, `app/exception_handlers.py`, `main.py` middleware order, `tests/test_envelope_compliance.py` (3 passing).
- **Chunk B** (`a1ee16d`): Alembic `m_001..m_001d` (audit_log + `users.last_step_up_at` + `user_login_history` table), `AuditAction` enum extended to 50 values, `AuditLog.metadata_/old_value/new_value/ip/UA/request_id`, `UserLoginHistory` model, `AuthService.authenticate_user` hook populating login history on every outcome, exception handler scoped to `/api/v1/*` only (legacy `/auth/*` keeps `{"detail": ...}` for backwards compat).
- **Chunk C** (`928bf11`): `FileStorageAdapter` Protocol, `LocalStorageAdapter`, `POST /dev/upload` sink with HMAC validation, `app/core/dependencies.py` (`get_public_storage` / `get_private_storage`), `/storage` static mount — all gated on `RAYCARWASH_ENV != "production"`.
- **Chunk D** (`7748353`): `rq` + `rq-scheduler` in requirements, `backend/Dockerfile`, expanded `docker-compose.yml` (postgres, redis, mailhog, rq-worker/scheduler under `workers` profile), `.env.example` documenting all Phase 0+ vars and TODO blocks for prod.

Test impact: 72/72 `test_auth`, 28/28 `test_admin`, 19/19 `test_appointments`, 3/3 `test_envelope_compliance` pass on this branch. One pre-existing failure in `test_register_onboarding_token_blocked_on_regular_endpoints` is unchanged — same failure on `master`.

Phase 1 begins implementation of the Profile Hub (`/api/v1/users/me`) on a new branch.

---

## Phase 1 implementation notes (2026-05-15)

Profile Hub (`/api/v1/users/me`) ships on `feat/profile-phase1`, merged via PR #3.

- **Chunk G** (`2937975`): Alembic `m_002..m_004` adding 22 columns across `users`, `client_profiles`, and `provider_profiles`. Includes the EncryptedType-backed `insurance_policy_number_encrypted` / `tax_id_encrypted` on ProviderProfile, denormalized counters (`total_appointments_count`, `total_spent_cents`, `total_services_completed`, `earnings_lifetime_cents`), and the `active_role` column that Phase 6's role-switch endpoint will read.
- **Chunk H** (`d55e1c6`): `domains/users/{hub_schemas,include_spec,hub_service}.py` + `router.py`. `GET /api/v1/users/me?include=` returns the composite-block response (per ADR-002b), `PATCH /api/v1/users/me` updates first/last/pronouns/language/timezone. 9 tests in `tests/test_users_hub.py` cover default + every include variant + step-up + role-mismatch silently-dropped tokens.
- **Chunk I-foundation** (`12662e3`): React Query wiring (`frontend/src/lib/react-query.ts`), Hub client (`services/users.service.ts`), `useMe(includes)` hook + `prefetchMe` (`hooks/useMe.ts`). `App.tsx` gains the `QueryClientProvider`.
- **Chunk I-screens** (`d63e09f`): mobile `ProfileScreen` / `EditProfileScreen` / `DetailerProfileScreen` migrated to `useMe`. Legacy fetches retained where the Hub doesn't yet expose the data (detailer-specific stats, phone change).
- **Chunk J** (`a18ad63`): admin web (`web/lib/hub.ts`) + marketing web (`marketing/lib/api/users-hub.ts` + `useMeHub`) Hub clients. Existing legacy `useMe()` hook + page coexist with the new Hub client during the migration window.

Test impact: 12 new tests, all green. Pre-existing suites (`test_auth`, `test_admin`, `test_appointments`, `test_envelope_compliance`) unchanged.

## Phase 2 implementation notes (2026-05-15)

Avatar + cover upload flow ships on `feat/profile-phase2`, merged via PR #4.

- **Chunk K** (`e363a72`): `domains/users/{avatar_schemas,avatar_service,avatar_router}.py`. Six endpoints (`POST /users/me/avatar/upload-url`, `POST /users/me/avatar`, `DELETE /users/me/avatar`, plus the three cover equivalents gated to detailers). `AvatarService` HEAD-verifies the uploaded bytes against the declared mime/size, swaps the column, audits `AVATAR_CHANGED`. 8 tests in `tests/test_users_avatar.py` cover happy path, foreign s3_key rejection, 404 on missing upload, 204 on delete.
- **Chunk L** (`71b6a69`): mobile `AvatarPicker` (Expo ImagePicker + ImageManipulator with 1024px clamp + JPEG re-encode), `s3-uploader.ts` helper handling both absolute (S3) and relative (LocalStorageAdapter `/dev/upload`) URLs, `avatar.service.ts` orchestrating the full presigned → bytes → confirm sequence. Wired into `EditProfileScreen` with React Query cache invalidation.
- **Quality pass** (`2350a15`): codified the "fix or TODO" convention in plan §0.5, fixed pre-existing TS errors in `DetailerHomeScreen`/`DetailerSelectionScreen`, widened `Card.style` to `StyleProp<ViewStyle>`, refined every Hub placeholder with `TODO(phase N <resource>)`.

S3StorageAdapter remains TODO in `app/core/dependencies.py` with a 4-step recipe; LocalStorageAdapter handles everything in dev.

## Phase 3 implementation notes (2026-05-15)

Contact verification + Security center + workers ship on `feat/profile-phase3`, merged via PR #5.

- **Chunk M** (`ed4c323`): Alembic `m_005` (`pending_contact_changes`) + `m_005b` (`totp_credentials`). Both tables CASCADE on user delete. Models in `domains/users/pending_contact_change.py` and `domains/auth/totp_credential.py`; TotpCredential intentionally skips `TimestampMixin` because DELETE removes the row outright (no soft delete).
- **Chunk N** (`98c50f4`): `/users/me/email/{change-request,change-confirm}` + `/phone/{change-request,change-verify}`. `ContactChangeService` validates current password, anti-enumerates new emails (generic 202 ack), enforces 5-attempt OTP cap (locks via row deletion), bumps `token_version` + revokes all refresh tokens on confirm. SMS adapter Protocol + `ConsoleSmsAdapter` (dev) + `TwilioSmsAdapter` stub (raises until prod wires it). Pre-existing bug fix: `require_step_up` now resolves `get_current_user` via Depends instead of expecting `request.state.user` to be pre-populated. 10 tests in `tests/test_users_contact_change.py`.
- **Chunk O** (`6182dfc`): `/auth/security`, `/auth/history`, `/auth/two-fa/{enroll,verify,backup-codes/regenerate}`, `DELETE /auth/two-fa`, `GET/PATCH/DELETE /auth/passkeys`. `TotpService` uses `pyotp` with `valid_window=1` (±30s drift) and accepts backup codes as a fallback for TOTP. Backup codes are SHA-256 hashed at rest; the plain set is returned exactly once during enrollment + regeneration. 9 tests in `tests/test_auth_security.py`.
- **Chunk P** (`fae777b`): `workers/pending_contact_cleanup.py` (cron hourly) drops expired+unconsumed rows, keeps expired+consumed for audit. `workers/login_history_purger.py` (cron monthly) enforces 365 d / 90 d retention per ADR-005. `workers/schedule.py` registers both via rq-scheduler. Each worker split into `_*_with_session(session)` + `_run_once()` so tests can drive the inner helper without spinning up a fresh `AsyncSessionLocal` (which would bind to a different event loop than the test fixture). 3 tests in `tests/test_workers.py`.
- **Chunk Q** (`1e4323f`): mobile `services/{auth-security,contact-change}.service.ts`, `hooks/useAuthSecurity.ts` (React Query bindings + mutations), `SecurityScreen` with General/Activity tabs, `ChangeEmailScreen` + `ChangePhoneScreen` (two-stage state machine, dev_token autofill in dev, force sign-out after success). `AppNavigator` registers Security/ChangeEmail/ChangePhone routes; ChangePassword/TwoFactorSetup/Passkeys/Sessions reserved as TODO routes.

Test impact across Phase 3: 22 new tests (10 + 9 + 3), all green. Migration chain extends to `m_005b`. Pre-existing 102/102 from Phase 0-2 remain green.

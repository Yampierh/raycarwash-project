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

---

## Hotfix sprint — Phase 0 hardening (2026-05-17)

Mid-Phase-4 audit surfaced three production-blocking issues in code already on `master`. Branch `hotfix/phase0-hardening` was cut from `master`, all four fixes landed independently revertable, then merged back via `aae8aa2`. **No schema migrations.**

- **`7dfb037` — RFC** documenting the three findings and the deferred Phase 9 backfill / monitoring threshold items (see `docs/rfc_auth_idempotency_and_appointments_system_hardening.md`).
- **`d6d5772` — H1 atomic refresh rotation.** `rotate_refresh_token` used `get_by_raw` → `mark_used` non-atomically; two concurrent rotations of the same single-use refresh could both win and emit fresh token pairs. Fixed via `mark_used_atomic` (`UPDATE … WHERE used_at IS NULL` + `rowcount`); the loser revokes the family + 401. 5 new tests in `tests/test_refresh_concurrency.py`.
- **`c4d1b84` — H2 idempotency body hash.** Cache key was `idempotency:{user}:{method}:{path}:{key}` — same-key-different-body collisions could return the wrong cached response on `POST /payment-methods/setup-intent`. Now binds a 16-char SHA-256 prefix of the body. **Critically** the middleware re-attaches the consumed body via `request._receive` so downstream handlers can still parse it. 6 new tests in `tests/test_idempotency_body_hash.py`.
- **`aa5a8be` — H3 wire mark_step_up at 6 real auth sites (CRITICAL).** `mark_step_up()` existed in `app/core/step_up.py` but was **never invoked from production**. Every Phase 3 step-up-gated endpoint silently 401'd real users. Fixed with `AuthService.record_step_up_success(request, user, db, auth_method=...)` called from: `/auth/login`, `/auth/token` (OAuth2 password flow), `/auth/verify` (identifier-first + password), `/auth/google`, `/auth/apple`, `/auth/webauthn/authenticate/complete`, `/auth/two-fa/verify`. Explicitly NOT wired to `/auth/refresh` — refresh is "still authenticated", not "re-authenticated"; extending step-up there would let stolen refresh tokens bypass step-up walls forever. The boundary is pinned by `test_refresh_does_NOT_extend_step_up_window`. 5 new e2e tests in `tests/test_step_up_wiring.py`.
- **`1327861` + `3a30bb3` — H4 AuditContext follow-up.** Initial H4 commit duplicated a dataclass that already lived in `app/middleware/audit_context.py` (with better X-Forwarded-For handling). `3a30bb3` dropped the duplicate; Phase 4+ routers consume `get_audit_context(request)` from the canonical module.
- **`1a94f56` — test alignment.** Three Phase 3 tests asserted 401 step_up_required on the pre-H3 accidental NULL state. Each now explicitly `_expire_step_up`s the column before the assertion — the security property they guarded is still correct; they just relied on an implementation accident.

Total: 20 new regression tests + 4 tests aligned, 230 → 250 green on master.

Operational note: drop existing `idempotency:*` Redis keys once after deploy so old-format keys don't mask new fixed entries during the 24 h TTL window.

---

## Phase 4 implementation notes (2026-05-17)

Phase 4 ships in five chunks on `feat/profile-phase4`. All run on top of the merged `hotfix/phase0-hardening`. **39 new tests, 255 → 294 green.** Chunk W (frontend mobile screens) still pending.

- **Chunk R** (`219f362`): Alembic `m_006..m_010` + models for the four new sub-resources. `user_addresses` (partial unique on default per user, H3 lookup index), `payment_methods` (Stripe mirror — only non-PCI fields), `client_favorites` (`(user_id, provider_user_id)` UNIQUE for idempotent re-favoring), `vehicle_photos` (sort_order for gallery). `client_profiles.default_address_id` FK deferred to m_010 because `user_addresses` didn't exist yet at m_003. `ClientFavorite` uses explicit `foreign_keys=[user_id]` because both sides point at `users.id`.

- **Chunk S** (`62850df`): `infrastructure/geocoding/{base,nominatim,google}.py` — `GeocodingAdapter` Protocol + `NominatimAdapter` (dev, rate-limited 1.1 s in-process, OSM UA policy) + `GoogleMapsGeocodingAdapter` placeholder that raises at import time with a TODO checklist. `app/core/dependencies.get_geocoding_adapter()` mirrors the storage/SMS factories. Contract: "address not found" returns `None` (not an error); transport failures (timeout, 5xx, 429) raise so the service decides policy. 9 new tests in `tests/test_geocoding_adapter.py`.

- **Chunk T** (`64ed976`): `/api/v1/users/me/addresses` — list, create, get, patch, set-default, delete. `AddressService` calls the geocoding adapter; failures persist the row with `lat/lng/h3=NULL` rather than 503-ing the user (matching engine just skips coord-less rows; backfill worker retries later). Re-geocoding is gated by `AddressUpdateRequest.has_geocodable_change()` — label-only edits don't burn a Nominatim quota slot. First-address-per-user auto-defaults. **Discovered SQLAlchemy 2.0's `update().execute()` defaults to `synchronize_session='auto'`** which mutates the in-memory entity — so the auto-promote-on-default-delete branch had to snapshot `row.is_default` BEFORE calling `soft_delete`. Pinned with `test_deleting_default_promotes_next_address`. Hub `_build_addresses_block` wired. 9 new tests in `tests/test_users_addresses.py`.

- **Chunk U** (`9d88adb`): `/api/v1/users/me/payment-methods` — list, setup-intent (step-up + idempotency forwarded to Stripe), get, set-default, delete (step-up + Stripe detach). Four new webhooks wired into the existing dispatcher: `payment_method.attached`, `.updated`, `.detached`, `setup_intent.succeeded` (fallback when `.attached` lags). New `infrastructure/payments/` package: `PaymentMethodAdapter` Protocol + `StripeTestAdapter` (real SDK with `sk_test_*` or `sk_live_*`) + `StripeStubAdapter` (deterministic IDs for placeholder keys; matches the existing `PaymentService._is_stub_key` escape hatch). Customer minting delegated to `PaymentService._get_or_create_stripe_customer` so two domains can't race and create duplicate `cus_*` IDs. **Local-first soft-delete on remove**: the user-facing list is flipped BEFORE Stripe detach so a Stripe outage doesn't strand a "ghost card" in the UI; webhook `payment_method.detached` reconciles. Hub `_build_payment_methods_block` wired. 11 new tests in `tests/test_users_payment_methods.py`.

- **Chunk V** (`3000f86`): three sub-resources, nine endpoints, two Hub block updates.
  - **Favorites** (`/me/favorites/providers`): list / add / remove. `INSERT … ON CONFLICT DO NOTHING` makes re-favor idempotent at the DB level (third tap returns 201 with the existing row, no duplicate, no audit re-fire). Same 404 for unknown user IDs AND existing-but-not-detailer IDs — no enumeration leak.
  - **Vehicle photos** (`/me/vehicles/{id}/photos`): two-step upload mirroring AvatarService. Per-vehicle cap of 4 enforced at BOTH `prepare_upload` (so the cap-busted client doesn't waste bytes) AND `confirm_upload` (race window: two concurrent uploads at count=3 must not both succeed). Same s3_key anti-spoof prefix check as avatars. `sign_photo_url` exported so the Hub vehicles block uses the same URL builder as the dedicated endpoint.
  - **Client preferences** (`/me/client-preferences`): GET/PUT. PUT validates `default_vehicle_id` and `default_address_id` refer to caller-owned resources before mutating — otherwise we'd silently write a dangling reference and the Hub would render someone else's address as the user's default.
  - Hub `_build_favorites_block` and `_build_vehicles_block` (now carrying the first-photo URL via bulk load) replaced their empty-stub implementations. 19 new tests across `test_users_{favorites,vehicle_photos,client_preferences}.py`.

**Phase 4 backend tally**: 4 new sub-resource domains (`addresses`, `payment_methods`, `favorites`, `vehicle_photos`) + 1 sub-resource extension (`client_preferences` on existing ClientProfile), 5 new Stripe webhook handlers, 6 Hub block stubs replaced with real implementations, 39 new tests (9 + 11 + 19), 0 regressions across the existing 255-test baseline. **Backend at 294/294 green.**

- **Chunk W** (`bfeb32f`): mobile screens consuming the Phase 4 backend surface. Five new `*.service.ts` modules (addresses, payment-methods, favorites, vehicle-photos, client-preferences), one `useProfileResources.ts` hook file bundling 16 React Query hooks — every mutation invalidates BOTH its own list key AND the `["users", "me"]` prefix so any cached Profile Hub include variant refetches the matching block. Six screens (`AddressesScreen` + `AddressFormScreen`, `PaymentMethodsScreen` with a Stripe `<CardField/>` + `confirmSetupIntent` add flow inside a lazy-required SDK shell, `FavoritesScreen`, `ClientPreferencesScreen` with a shared `PickerModal` for vehicle/address/frequency, `VehiclePhotosScreen` with `expo-image-picker` → resize-to-1600px → presigned-upload). Navigator + `RootStackParamList` extended; `ProfileScreen` menu rewired with real handlers for Payment Methods / Addresses / Favorites + a new "Defaults & cadence" row; `VehicleDetailScreen` gets a "Manage photos" CTA. `npx tsc --noEmit` clean.

**Phase 4 complete.** Web tracks (admin + marketing) trail by one phase per the plan §7.7 staging and pick up in Phase 5 or later.

---

## Phase 5 implementation notes (2026-05-18)

Phase 5 ships in seven chunks on `feat/profile-phase5`. Plan §10 ("Recursos del proveedor") plus the §2.12 endpoint catalog. **44 new tests, 338/338 backend green; mobile clean via `tsc --noEmit`.**

- **Chunk Y1** (`ac0f68b`): Alembic `m_011..m_013` + three new models (`Document`, `ProviderPortfolioPhoto`, `ProviderAchievement`). Document keyed on `user_id` (not provider_user_id) so KYC artifacts survive a provider → client-only role switch. Achievements use `(provider_user_id, achievement_type)` UNIQUE for idempotent re-runs. All three model types are free-form Strings (no enums) so adding a new category doesn't need a migration.

- **Chunk Y2** (`bf295fd`): `/users/me/provider-profile` × 4 + `/provider-status`. New `ProviderProfileService` wraps the existing `ProviderRepository` — zero logic duplication from `/api/v1/detailers/me`. Activation grants the `detailer` role + creates a ProviderProfile + audits PROVIDER_MODE_SWITCHED. **Deliberately does NOT bump `token_version`** — `require_role` reads `user.user_roles` via DB on every request, so the new role takes effect on the next call without invalidating the caller's access token. KYC gate on `/provider-status`: flipping `accepting_bookings=True` when `verification_status != "approved"` → 403 `kyc_required`. 10 tests in `tests/test_users_provider_profile.py`.

- **Chunk Y3** (`634d72f`): `/users/me/provider-portfolio` × 4. Two-step upload mirrors `VehiclePhotoService` (Phase 4 chunk V). Per-provider cap of 30 enforced at BOTH `prepare_upload` (so the cap-busted client doesn't waste bytes) AND `confirm_upload` (race window: two concurrent uploads at count=29 must not both succeed). `s3_key` anti-spoof: keys begin `provider_portfolio/{user_id}/` and confirm rejects anything outside that prefix → 403. 6 tests in `tests/test_users_provider_portfolio.py`.

- **Chunk Y4** (`6fbacaa`): `/users/me/provider-documents` × 4 (KYC artifacts). Files land in the PRIVATE bucket (ADR-008), download URLs are 1 h presigned. DELETE is step-up gated — removing a KYC artifact is credential-adjacent. Soft delete: row stays for audit/legal retention, S3 cleanup is best-effort. Model keyed on `user_id` so artifacts persist across role switches. 9 tests in `tests/test_users_provider_documents.py`.

- **Chunk Y5** (`1cc3365`): `/users/me/provider-verification` (POST start + GET status) + `/me/provider-achievements` (read-only). Verification reuses the EXISTING webhook in `domains/payments/webhook_router.py` for the approve/reject path — Y5 just adds the resource-oriented start + status endpoints. Stripe Identity session creation re-implemented inline in the service (vs. calling the legacy `/detailers/verification/start` handler) because invoking a FastAPI route from a service requires manufacturing a Request — 30 lines of duplicated SDK calls is the simpler path, and both paths share the same `STRIPE_SECRET_KEY` dev-bypass check. `has_active_session` field on the status response computed from `(status="pending" AND session_id IS NOT NULL)` so the UI can render "Resume verification" CTA. 9 tests in `tests/test_users_provider_verification.py`.

- **Chunk Y6** (`7da8f97`): two daily workers wired into `workers/schedule.py`:
  - `achievement_evaluator` (02:00 daily) — walks every ProviderProfile and INSERTs `ProviderAchievement` rows for criteria that pass. Catalog: `verified` (status=approved), `first_job` (≥1), `ten_jobs` (≥10), `hundred_jobs` (≥100), `five_star` (avg ≥4.8 AND ≥5 reviews). `ON CONFLICT DO NOTHING` against the UNIQUE makes re-runs no-ops.
  - `document_expiry_checker` (01:00 daily) — scans `Document.expires_at` against bucketed thresholds (30 / 14 / 7 / 1 days) and dispatches a reminder per (doc, bucket) at most once. Idempotency keyed via an `AuditLog` row stamping `{source: "document_expiry_checker", reminder_bucket: <int>}`. Today the "dispatch" is `logger.info` — Phase 7's `NotificationDispatcher` swaps it for real email + push.

  Both workers use the same `_*_with_session(session)` + `_run_once()` + `run()` shape Phase 3 established so tests drive the helper without the `AsyncSessionLocal`-on-different-event-loop trap. 10 tests in `tests/test_workers_y6.py`.

- **Chunk Y7** (`081859b`): 6 mobile screens consuming Y2..Y5. Four service modules + one `useProviderResources.ts` hook file (11 hooks, mutations invalidate both their own keys and the `["users", "me"]` Hub prefix). Screens: `ProviderHubScreen` (central dashboard with KYC-gated accepting-bookings toggle + inline ActivationForm for unactivated users — no dead-end empty state), `ProviderProfileEditScreen` (business + bio + radius + pause CTA), `ProviderPortfolioScreen` (gallery with caption/tag modal, hero/before/after presets, max 30, image-picker → 1600px resize → presigned upload), `ProviderDocumentsScreen` (KYC docs with type chips + optional expires_at; image-only today, TODO marker for `expo-document-picker`), `ProviderVerificationScreen` (status banner + start/resume CTA that routes to existing `DetailerOnboardingScreen` to reuse the `useStripeIdentity` SDK plumbing). Wired into `AppNavigator` + `RootStackParamList`. `ProfileScreen` gets an "EARN → Provider mode" row; `DetailerProfileScreen` gets a "Provider hub" entry at top of Business section. `npx tsc --noEmit` clean.

**Phase 5 backend tally**: 3 new sub-resource domains (Document + PortfolioPhoto + Achievement), 16 new provider endpoints (5 profile/status + 4 portfolio + 4 documents + 3 verification/achievements), 2 daily workers, 44 new tests (10 + 6 + 9 + 9 + 10), 0 regressions across 294-test baseline. **Backend at 338/338 green; frontend at `tsc --noEmit` clean.**

**Phase 5 complete.** Provider hub + KYC + portfolio + verification flow is now end-to-end functional on mobile. The web admin's KYC review tab remains deferred per plan §7.7 staging — picks up in Phase 6 alongside the active-role switcher.

---

## Phase 6 implementation notes (2026-05-18)

ADR-003 in action. `PATCH /api/v1/users/me/active-role` lets a multi-role user swap the role claim that future JWTs carry, with the refresh token rotated in the same call.

- **Endpoint shape** — body is `{role, refresh_token}`. The refresh_token is what closes the ADR-003 attack window: the rotation is atomic on the client's current refresh, so a stolen refresh captured before the switch cannot keep emitting access tokens with the previous role. Response is `{access_token, refresh_token, active_role}`.
- **Validation** — target role must already be in `user.user_roles`; otherwise 403 `permission_denied`. `admin` is rejected at the Pydantic Literal layer (422) so the consumer switcher never touches it. **Deliberate departure from plan §2.3**: no KYC gate on switching to detailer/mechanic. After E1 a user can hold a detailer profile without KYC; blocking the switch would lock them out of their own onboarding dashboard. KYC stays where it belongs — `is_active=true` (booking visibility) on `ProviderProfile`.
- **Token wiring** — service mints the new access token via `AuthService.create_access_token(user.id, target, token_version)` so the `role` claim carries the target. `AuthService.rotate_refresh_token` issues the new refresh in the same family. Side effect: subsequent `/auth/refresh` calls now prefer `user.active_role` over `primary_role`, so a refreshed access token doesn't silently revert to the previous role.
- **Audit** — `AuditAction.ROLE_SWITCHED` already existed; service emits a row with `old_value={"active_role": prev}` and `new_value={"active_role": target}` + the `audit_ctx` (ip / UA / request_id).
- **Mobile** — new `RoleSwitcher` component (`frontend/src/components/RoleSwitcher.tsx`) rendered at the top of `ProfileScreen` and `DetailerProfileScreen` only when `available_roles.length > 1`. On tap: calls `switchActiveRole`, persists both tokens via `saveToken` + `saveRefreshToken`, updates Zustand snapshot, then `navigation.reset` into the destination stack (`Main` for client/mechanic, `DetailerMain` for detailer). Mechanic shell deferred until E3 ships a dedicated UI — falls back to `Main`. Error path surfaces `permission_denied` / `kyc_required` / fallback via `Alert`.

12 endpoint tests in `tests/test_users_active_role.py`: happy path, claim contents, persistence, refresh rotation revoking the old token, /auth/refresh after switch preserving active_role, 403 on unassigned role, 422 on admin or unknown role, 401 without auth or with bad refresh, client target works, audit row format. Frontend `tsc --noEmit` clean.

**Master plan Phases 0–6 complete.** Phases 7 (notifications + privacy + public view), 8 (GDPR + historiales especializados), and 9 (polish + analytics + load tests) remain. Integration plans E0 + E1 also shipped in parallel; E2/E3/E4 + plan 08-hardening remain.

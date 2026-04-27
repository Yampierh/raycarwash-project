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

### Pending (Sprint 7)

- Push notifications (Expo Notifications / FCM)
- Admin dashboard endpoints
- Fix remaining edge-case test failures (vehicles, detailers, matching)
- Multiservice: ServiceCategory model, mechanic vertical, provider type on ProviderProfile
- Category-specific onboarding fields (mechanics need certifications)
- Frontend: category selection screen before matching

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

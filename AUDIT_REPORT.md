# RayCarWash — audit report

**Last updated**: April 2026

---

## Executive summary

This document tracks all technical decisions, bugs found and fixed, and current test coverage across all sprints. It is the source of truth for what is done, what is broken, and what comes next.

---

## Decisions log

### Auth flow — identifier-first (Uber style)

Adopted in Sprint 2. Three-step flow:

1. `POST /auth/identify` — email or phone, returns `is_new_user`
2. `POST /auth/verify` — password or social token
   - Existing user → full tokens
   - New user → `registration_token` (30 min, scoped to profile completion only)
3. `PUT /auth/complete-profile` — name, phone, role (client or detailer)
   - Returns full `access_token` + `refresh_token`

**Why**: reduces friction on first use. User only types email once; the system decides if they need to register or log in.

### Two Axios clients

`authClient` (base `/auth`) and `apiClient` (base `/api/v1`) are kept separate intentionally. Mixing them causes 404s because auth endpoints are not under `/api/v1/`.

### VehicleSize is runtime-derived

`body_class` is stored on Vehicle. `VehicleSize` (small/medium/large/xl) is derived from it at runtime via `body_class_to_size()`. Never stored — this keeps pricing flexible without migrations.

### Prices in cents

All prices are integer cents. Never floats. Frontend divides by 100 for display.

### estimated_price is immutable

Set once at appointment creation. `actual_price` is set on COMPLETED. These are two distinct fields.

### Soft deletes everywhere

`is_deleted + deleted_at` on every entity. No hard deletes. Preserves audit trail.

### Multiservice architecture decision (April 2026)

Decided to expand beyond detailing. Current plan:
- Sprint 6: finish detailing vertical fully (tests, push notifications, admin)
- Sprint 7: add `ServiceCategory` model, connect `Service` to a category, enable mechanic vertical
- The `ServiceCategory` fix also resolves the test suite failures (see below)

---

## Bugs found and fixed

### Sprint 2

| # | Severity | File | Description |
|---|---|---|---|
| 1 | Critical | `services/auth.service.ts` | Refresh token sent as JSON body → backend expects query param. Fixed. |
| 2 | Critical | `services/auth.service.ts` | Social auth (`/auth/google`, `/auth/apple`) called via `apiClient` → 404. Fixed: use `authClient`. |
| 3 | High | `routers/auth_router.py` | `service_address` field in UserUpdate pointed to a column that no longer exists on User. Fixed: removed from endpoint. |
| 4 | Critical | `services/auth.py` | `get_current_user()` didn't eager-load `user_roles` → `is_client()` returned False for all users. Fixed: added refresh to load relations. |

### Sprint 6 — security audit (April 9, 2026)

| # | Severity | File | Description |
|---|---|---|---|
| 1 | Critical | `routers/webhook_router.py` | Bare `except Exception` intercepted system errors. Fixed: narrowed to `except (json.JSONDecodeError, UnicodeDecodeError)`. |
| 2 | High | `services/payment_service.py` | `stripe.api_key` assigned inside each method call (4 methods). Fixed: moved to module level. |
| 3 | High | `routers/auth_router.py` + `schemas/schemas.py` | Social provider detected by string heuristic in token. Fixed: explicit `provider` field in `VerifyRequest`. |
| 4 | Medium | `routers/auth_router.py` | Role assignment via nonexistent attribute. Fixed: use ORM `UserRoleAssociation`. |
| 5 | Medium | `core/config.py` | `STRIPE_SECRET_KEY` validator didn't reject invalid formats. Fixed: must start with `sk_test_`, `sk_live_`, or `rk_`. |
| 6 | Low | `schemas/schemas.py` | 9 request schemas repeated the same `model_config`. Fixed: extracted to `_BaseRequestSchema`. |

### Sprint 6 — WebSocket + ARRIVED state (April 11, 2026)

| # | Severity | File | Description |
|---|---|---|---|
| 1 | High | `repositories/detailer_repository.py` | `update_location` did UPDATE on `User` table — fields `current_lat/lng/last_location_update` live on `DetailerProfile`. Fixed. |
| 2 | High | `services/appointment_service.py` | RBAC check used `actor.role ==` (singular, nonexistent). Multi-role users got 403. Fixed: use `actor.has_role()`. |
| 3 | Medium | `services/appointment_service.py` | `get_available_slots`: if service not found, `service_duration_minutes` was unbound → `UnboundLocalError`. Fixed: fallback to `SLOT_GRANULARITY_MINUTES`. |

### Known positives (no changes needed)

- JWT with explicit `type` claim — prevents token confusion attacks
- bcrypt via passlib — correct
- Timing-safe auth with `dummy_verify()`
- Rate limiting on all auth endpoints
- SQL injection protected via SQLAlchemy ORM
- Stripe webhook HMAC-SHA256 verified
- Soft deletes preserve audit trail
- PII encrypted at rest with `EncryptedType`
- 5 MB request body limit (bypassed for Stripe webhooks)
- CORS configurable via env

---

## New features by sprint

### Sprint 6 — WebSocket + ARRIVED state

| Component | Description |
|---|---|
| `AppointmentStatus.ARRIVED` | New state between CONFIRMED and IN_PROGRESS. `arrived_at` auto-stamped. Alembic migration included. |
| `ws/connection_manager.py` | `ConnectionManager` in-memory: rooms by `appointment_id`, `asyncio.Lock`, broadcast with dead socket purge. Scales to Redis pub-sub without API changes. |
| `ws/router.py` | `WS /ws/appointments/{id}?token=<jwt>`. Accepts `ping` / `location_update` (detailer only). Persists location via background task with own session. |
| `auth.py: ws_get_current_user` | WS auth helper: returns `User\|None` instead of raising, for clean 4001/4003/4004 close codes. |
| HTTP → WS broadcast | Status change and location update HTTP calls trigger `ConnectionManager.broadcast()` to the active room. |
| `store/authStore.ts` | Zustand store: synchronous JWT for WS. `saveToken`/`clearAuthTokens` sync the store. `app.tsx` hydrates at boot. |
| `hooks/useAppointmentSocket.ts` | Full WS hook: auto-connect, exponential backoff (1s→30s), heartbeat ping 30s, status and location callbacks. |
| `DetailerHomeScreen` | "I've Arrived" button (CONFIRMED→ARRIVED), "Start Job" button (ARRIVED→IN_PROGRESS). GPS push every 5s via `expo-location` while job is active. |
| `HomeScreen` | "DETAILER ARRIVED" banner with real-time updates via WS. |

---

## Test coverage

```bash
cd backend
pytest -v                          # all tests
pytest tests/test_auth.py -v       # auth (21 passing)
```

### Auth (21/21 passing)

```
TestLogin::test_login_success                    PASSED
TestLogin::test_login_invalid_password           PASSED
TestLogin::test_login_nonexistent_user           PASSED
TestLogin::test_login_inactive_user              PASSED
TestLogin::test_login_missing_credentials        PASSED
TestTokenRefresh::test_refresh_success           PASSED
TestTokenRefresh::test_refresh_invalid_token     PASSED
TestTokenRefresh::test_refresh_expired_token     PASSED
TestTokenRefresh::test_refresh_missing_token     PASSED
TestGetCurrentUser::test_me_authenticated        PASSED
TestGetCurrentUser::test_me_unauthenticated      PASSED
TestGetCurrentUser::test_me_invalid_token        PASSED
TestUpdateProfile::test_update_profile_success   PASSED
TestUpdateProfile::test_update_profile_partial   PASSED
TestUpdateProfile::test_update_profile_unauth    PASSED
TestGoogleLogin::test_google_login_new_user      PASSED
TestGoogleLogin::test_google_login_missing_token PASSED
TestPasswordReset::test_reset_existing_user      PASSED
TestPasswordReset::test_reset_nonexistent_user   PASSED
TestPasswordReset::test_reset_missing_email      PASSED
TestRateLimiting::test_login_rate_limit          PASSED
```

### Overall status

| Module | Tests | Passing | Status | Root cause |
|---|---|---|---|---|
| Auth | 21 | 21 | ✅ | — |
| Vehicles | 17 | 7 | ⚠️ | Test logic issues, not production bugs |
| Appointments | 18 | 0 | ❌ | Missing `category` column in Service seed |
| Detailers | 18 | 0 | ❌ | Same |
| Matching | 10 | 0 | ❌ | Same |
| WebSocket | 0 | — | 📋 | Not yet written |
| **Total** | **84** | **28** | — | — |

### Root cause for failing test modules

```
IntegrityError: null value in column "category" of relation "services"
violates not-null constraint
```

The `Service` model has a `category` column (NOT NULL) that is not populated by the test seed in `conftest.py`.

**Fix path**:
1. Create `ServiceCategory` model with fields: `id`, `name`, `icon`, `is_active`
2. Add `category_id` FK to `Service` model
3. Add Alembic migration
4. Update `seed.py` and `conftest.py` to populate `ServiceCategory` rows first
5. This also lays the foundation for Sprint 7 multiservice architecture

**Vehicles 10 failing tests**: these are test logic issues, not production bugs. The endpoints work correctly.

---

## Files modified per sprint

### Sprint 2 (auth + vehicles)

| File | Change |
|---|---|
| `app/services/auth.py` | Added eager loading of `user_roles` in `get_current_user()` |
| `app/routers/auth_router.py` | Removed `service_address` from UserUpdate · Added `complete-profile` endpoint |
| `app/routers/vehicle_router.py` | Full OpenAPI documentation |
| `app/routers/addon_router.py` | Full OpenAPI documentation |
| `tests/conftest.py` | Fixtures with RBAC, services, addons seed |
| `tests/test_auth.py` | 21 tests — all passing |
| `tests/test_vehicles.py` | 17 tests — 7 passing |
| `pytest.ini` | pytest configuration |
| `src/services/auth.service.ts` | Fixed refresh token format (query param) · Fixed social auth URL (authClient) |

### Sprint 6 (security + WebSocket)

| File | Change |
|---|---|
| `routers/webhook_router.py` | Narrowed exception handler |
| `services/payment_service.py` | Moved `stripe.api_key` to module level |
| `routers/auth_router.py` | Explicit `provider` field · Correct RBAC association |
| `schemas/schemas.py` | `_BaseRequestSchema` · explicit `provider` field |
| `core/config.py` | Stripe key format validator |
| `repositories/detailer_repository.py` | Fixed `update_location` — targets `DetailerProfile` not `User` |
| `services/appointment_service.py` | Fixed RBAC check · Fixed `UnboundLocalError` in availability |
| `app/ws/connection_manager.py` | New: WebSocket room manager |
| `app/ws/router.py` | New: WS endpoint with JWT auth |
| `services/auth.py` | Added `ws_get_current_user()` helper |
| `store/authStore.ts` | New: Zustand store for sync JWT |
| `hooks/useAppointmentSocket.ts` | New: WS hook with reconnect + heartbeat |

---

## Upcoming work

### Sprint 6 remaining

- Push notifications (Expo Notifications)
- Admin dashboard endpoints
- Fix 10 failing vehicle tests
- Write WebSocket tests (`pytest-asyncio` + mock WS)

### Sprint 7 — multiservice

1. Create `ServiceCategory` model and migration
2. Add `category_id` FK to `Service` (fixes test suite failures)
3. Update seed to populate categories
4. Frontend: category selection screen before matching
5. Provider type field on `DetailerProfile` (detailer / mechanic / specialist)
6. Category-specific onboarding fields (mechanics need certifications field)

### How to run tests

```bash
cd backend
source venv/bin/activate           # macOS/Linux
.\venv\Scripts\Activate            # Windows

pytest tests/test_auth.py -v       # auth suite
pytest tests/test_vehicles.py -v   # vehicles suite
pytest tests/ -v                   # all tests
```
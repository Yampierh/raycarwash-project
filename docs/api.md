# API Reference

**Base URL**: `http://localhost:8000`
**Swagger**: `/docs` · **ReDoc**: `/redoc` · **Health**: `/health`

---

## Two Axios clients — critical

```
authClient  →  base: /auth      (identify, verify, complete-profile, social, refresh, sessions)
apiClient   →  base: /api/v1    (everything else)
```

Never use `apiClient` for auth endpoints — they live at `/auth`, not `/api/v1/auth`.

---

## Auth (`/auth`)

### Identifier-first flow (Uber style)

#### Step 1 — Identify

```
POST /auth/identify
{ "identifier": "user@example.com" }    // email or phone
```

```json
{ "is_new_user": false, "available_methods": ["password", "passkey"] }
```

#### Step 2 — Verify

**Existing user:**

```
POST /auth/verify
{ "identifier": "user@example.com", "password": "..." }
```

```json
{ "access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer" }
```

**New user** (same endpoint):

```json
{ "onboarding_token": "eyJ...", "next_step": "complete_profile" }
```

**Social login:**

```
POST /auth/verify
{ "identifier": "user@example.com", "provider": "google", "token": "<google_token>" }
```

Provider values: `"google"` | `"apple"`

#### Step 3 — Complete profile (new users only)

Use `onboarding_token` as Bearer. Expires in 30 min.

```
PUT /auth/complete-profile
Authorization: Bearer <onboarding_token>
{ "full_name": "John Doe", "phone_number": "+12345678901", "role": "client" }
```

Role values: `"client"` | `"detailer"`

Returns `access_token` + `refresh_token`. After this, route by role:

- `client` → Main tabs
- `detailer` → `DetailerOnboarding` if no profile, else `DetailerMain`

---

### Other auth endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/token` | — | OAuth2 password login (form: `username`, `password`) |
| POST | `/auth/refresh` | — | Rotate refresh token (query param: `?refresh_token=…`) |
| GET | `/auth/me` | Bearer | Current user profile |
| PUT | `/auth/update` | Bearer | Update `full_name`, `phone_number`, `profile_photo_url` (all optional) |
| POST | `/auth/logout` | Bearer | Revoke refresh token family |
| GET | `/auth/sessions` | Bearer | List active sessions |
| DELETE | `/auth/sessions` | Bearer | Revoke all sessions |
| DELETE | `/auth/sessions/{family_id}` | Bearer | Revoke one session |
| POST | `/auth/register` | — | Quick register (returns onboarding_token, same as identify+verify for new users) |
| POST | `/auth/login` | — | Quick login (returns tokens) |
| POST | `/auth/password-reset` | — | Request reset email (always 200 — no enumeration) |
| POST | `/auth/password-reset/confirm` | — | Confirm reset with token + new password |
| POST | `/auth/email/verify` | — | Verify email address with token |
| POST | `/auth/email/resend-verification` | Bearer | Resend verification email |
| POST | `/auth/google` | — | Google token exchange (shortcut for `/auth/verify` with provider) |
| POST | `/auth/apple` | — | Apple token exchange |
| POST | `/auth/webauthn/register/begin` | Bearer | Start passkey registration |
| POST | `/auth/webauthn/register/complete` | Bearer | Finish passkey registration |
| POST | `/auth/webauthn/authenticate/begin` | — | Start passkey login |
| POST | `/auth/webauthn/authenticate/complete` | — | Finish passkey login |
| GET | `/auth/webauthn/credentials` | Bearer | List registered passkeys |
| PATCH | `/auth/webauthn/credentials/{id}` | Bearer | Rename passkey |
| DELETE | `/auth/webauthn/credentials/{id}` | Bearer | Delete passkey |

---

## Users (`/api/v1/users`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/users` | — | Register (legacy — prefer `/auth/register`) |

### Profile Hub (Phase 1)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/users/me?include=` | Bearer | Composite-block Profile Hub. Tokens: `profile`, `stats`, `vehicles`, `addresses`, `payment_methods`, `favorites`, `preferences`, `notifications`, `security`, `sessions`, `provider`. `security` and `sessions` require step-up; `?on_step_up=skip` omits them with a `meta.skipped_due_to_step_up` marker instead of 401. |
| PATCH | `/api/v1/users/me` | Bearer | Update first/last/pronouns/language/timezone. |

### Avatar + cover (Phase 2)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/users/me/avatar/upload-url` | Bearer | Step 1: declare mime+size, get presigned URL. |
| POST | `/api/v1/users/me/avatar` | Bearer | Step 2: confirm `s3_key` after upload, HEAD-verified server-side. |
| DELETE | `/api/v1/users/me/avatar` | Bearer | Drop avatar + storage object. |
| POST | `/api/v1/users/me/cover/upload-url` | Bearer(detailer) | Same flow, cover gated to detailers. |
| POST | `/api/v1/users/me/cover` | Bearer(detailer) | |
| DELETE | `/api/v1/users/me/cover` | Bearer(detailer) | |

### Contact change (Phase 3)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/users/me/email/change-request` | step-up | Anti-enum 202 ack; emails new+old. |
| POST | `/api/v1/users/me/email/change-confirm` | (token) | Consume one-time link; bumps `token_version`, revokes all refresh. |
| POST | `/api/v1/users/me/phone/change-request` | step-up | Send OTP via SMS adapter. |
| POST | `/api/v1/users/me/phone/change-verify` | Bearer | 5-attempt OTP cap; lock-by-delete on miss. |

### Addresses (Phase 4 chunk T)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/users/me/addresses` | Bearer | List active addresses (newest first). |
| POST | `/api/v1/users/me/addresses` | Bearer | Create; geocodes via Nominatim/Google. Failures persist with `lat/lng=NULL`. First address auto-defaults. |
| GET | `/api/v1/users/me/addresses/{id}` | Bearer | Detail. |
| PATCH | `/api/v1/users/me/addresses/{id}` | Bearer | Partial update. Re-geocodes only on line/city/state/zip/country change. |
| PATCH | `/api/v1/users/me/addresses/{id}/default` | Bearer | Atomic default pivot. |
| DELETE | `/api/v1/users/me/addresses/{id}` | Bearer | Soft-delete; auto-promotes next address as default. |

### Payment methods (Phase 4 chunk U)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/users/me/payment-methods` | Bearer | List active (Stripe mirror, non-PCI only). |
| POST | `/api/v1/users/me/payment-methods/setup-intent` | step-up | Returns Stripe `client_secret` + publishable key. Honors `Idempotency-Key` header (forwarded to Stripe). |
| GET | `/api/v1/users/me/payment-methods/{id}` | Bearer | Detail. |
| PATCH | `/api/v1/users/me/payment-methods/{id}/default` | Bearer | Atomic default pivot. |
| DELETE | `/api/v1/users/me/payment-methods/{id}` | step-up | Local-first soft-delete + Stripe detach. |

Webhooks consumed by `POST /webhooks/stripe`: `payment_method.attached`, `.updated`, `.detached`, `setup_intent.succeeded`.

### Favorites (Phase 4 chunk V)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/users/me/favorites/providers` | Bearer(client) | List favorited providers (joined w/ ProviderProfile). |
| POST | `/api/v1/users/me/favorites/providers/{provider_user_id}` | Bearer(client) | Pin. Idempotent: re-favor returns 201 with existing row. 404 on unknown OR non-detailer ID. |
| DELETE | `/api/v1/users/me/favorites/providers/{provider_user_id}` | Bearer(client) | Unpin. Idempotent. |

### Vehicle photos (Phase 4 chunk V)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/users/me/vehicles/{id}/photos` | Bearer(owner) | List ordered by `sort_order`. |
| POST | `/api/v1/users/me/vehicles/{id}/photos/upload-url` | Bearer(owner) | Step 1. 409 if vehicle is at the 4-photo cap. |
| POST | `/api/v1/users/me/vehicles/{id}/photos` | Bearer(owner) | Step 2: confirm s3_key + caption. |
| DELETE | `/api/v1/users/me/vehicles/{id}/photos/{photo_id}` | Bearer(owner) | Drop row + storage object. |

### Client preferences (Phase 4 chunk V)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/users/me/client-preferences` | Bearer | default_vehicle_id, default_address_id, marketing_opt_in, frequency_preference. |
| PUT | `/api/v1/users/me/client-preferences` | Bearer | Replace. Validates default_vehicle_id / default_address_id are caller-owned before mutating (404 otherwise). |

---

## Vehicles (`/api/v1/vehicles`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/vehicles` | Bearer(client) | Create vehicle |
| GET | `/api/v1/vehicles` | Bearer(client) | List own vehicles |
| PUT | `/api/v1/vehicles/{id}` | Bearer(client) | Update vehicle |
| DELETE | `/api/v1/vehicles/{id}` | Bearer(client) | Soft delete |
| GET | `/api/v1/vehicles/lookup/{vin}` | Bearer | NHTSA VIN decode |

**Create vehicle body:**

```json
{
  "make": "Toyota",
  "model": "Camry",
  "year": 2023,
  "color": "Silver",
  "license_plate": "ABC123",
  "body_class": "Sedan",
  "vin": "1HGBH41JXMN109186"
}
```

`body_class` is required. `VehicleSize` is derived from it at runtime — never sent by client.

**VIN lookup response:**

```json
{
  "make": "Toyota",
  "model": "Camry",
  "year": 2023,
  "body_class": "Sedan",
  "suggested_size": "small"
}
```

---

## Services & Addons

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/services` | — | List all active services |
| GET | `/api/v1/services/{id}` | — | Service detail |
| GET | `/api/v1/addons` | — | List all active add-ons |

**Service response:**

```json
{
  "id": "uuid",
  "name": "Full Detail",
  "base_price_cents": 12000,
  "price_small": 12000,
  "price_medium": 14400,
  "price_large": 18000,
  "price_xl": 24000,
  "base_duration_minutes": 180,
  "duration_small_minutes": 180,
  "duration_medium_minutes": 216,
  "duration_large_minutes": 270,
  "duration_xl_minutes": 360
}
```

**Addon response:**

```json
{ "id": "uuid", "name": "Clay Bar Treatment", "price_cents": 3000, "duration_minutes": 45 }
```

---

## Detailers (`/api/v1/detailers`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/detailers` | — | Search detailers by geo + filters |
| GET | `/api/v1/detailers/me` | Bearer(detailer) | Own profile + stats |
| PUT | `/api/v1/detailers/me` | Bearer(detailer) | Upsert own profile |
| PATCH | `/api/v1/detailers/me/status` | Bearer(detailer) | Toggle `is_accepting_bookings` |
| GET | `/api/v1/detailers/me/services` | Bearer(detailer) | Catalogue with toggle state |
| PATCH | `/api/v1/detailers/me/services/{id}` | Bearer(detailer) | Toggle service + optional custom price |
| GET | `/api/v1/detailers/{id}/availability` | — | Available 30-min slots |
| POST | `/api/v1/detailers/location` | Bearer(detailer) | GPS update |
| GET | `/api/v1/detailers/{id}/profile` | — | Public profile |
| POST | `/api/v1/detailers/verification/start` | Bearer(detailer) | Start Stripe Identity |
| GET | `/api/v1/detailers/verification/status` | Bearer(detailer) | Verification status |
| POST | `/api/v1/detailers/verification/submit` | Bearer(detailer) | Submit verification docs |

**Search query params:**

```
GET /api/v1/detailers?lat=41.0793&lng=-85.1394&radius_miles=25&min_rating=4.0&page=1&page_size=20
```

**Upsert profile body:**

```json
{
  "bio": "5 years of professional detailing",
  "years_of_experience": 5,
  "service_radius_miles": 25,
  "timezone": "America/Indiana/Indianapolis",
  "working_hours": {
    "monday": { "start": "08:00", "end": "18:00", "enabled": true },
    "tuesday": { "start": "08:00", "end": "18:00", "enabled": true }
  }
}
```

**Availability query:**

```
GET /api/v1/detailers/{id}/availability?request_date=2027-06-15&service_id={uuid}&vehicle_size=medium
```

Response: array of `{ start_time, end_time, is_available }` (30-min slots).

---

## Matching (`/api/v1/matching`)

```
GET /api/v1/matching
Authorization: Bearer <client_token>
```

| Param | Type | Required | Description |
|---|---|---|---|
| `lat` | float | ✅ | Client latitude |
| `lng` | float | ✅ | Client longitude |
| `date` | string | ✅ | `YYYY-MM-DD` |
| `service_id` | UUID | ✅ | Requested service |
| `vehicle_sizes` | string | ✅ | Comma-separated: `"small,medium"` |
| `addon_ids` | string | — | Comma-separated UUIDs |
| `radius_miles` | float | — | Default 25 |

Response: ranked list of detailers with `distance_miles`, `estimated_price`, `estimated_duration`, `available_slots`.

**Sort order:** date specified → `rating DESC, distance ASC` · ASAP → `distance ASC, rating DESC`.

---

## Appointments (`/api/v1/appointments`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/appointments` | Bearer(client) | Create booking |
| GET | `/api/v1/appointments/mine` | Bearer | List own (paginated) |
| GET | `/api/v1/appointments/{id}` | Bearer | Detail |
| PATCH | `/api/v1/appointments/{id}/status` | Bearer | Status transition |

**Create — single vehicle:**

```json
{
  "detailer_id": "uuid",
  "vehicle_id": "uuid",
  "service_id": "uuid",
  "scheduled_time": "2027-06-15T14:00:00Z",
  "service_address": "123 Main St, Fort Wayne, IN",
  "service_latitude": 41.0793,
  "service_longitude": -85.1394,
  "client_notes": "Please ring doorbell"
}
```

**Create — multi-vehicle:**

```json
{
  "detailer_id": "uuid",
  "scheduled_time": "2027-06-15T14:00:00Z",
  "service_address": "123 Main St",
  "service_latitude": 41.0793,
  "service_longitude": -85.1394,
  "vehicles": [
    { "vehicle_id": "uuid1", "service_id": "uuid", "addon_ids": ["addon_uuid"] },
    { "vehicle_id": "uuid2", "service_id": "uuid" }
  ]
}
```

**Status update:**

```json
{ "status": "confirmed", "actual_price": 14400, "detailer_notes": "On my way" }
```

**Valid transitions:**

| From | To | Who |
|---|---|---|
| PENDING | CONFIRMED | Detailer / Admin |
| PENDING | CANCELLED_BY_CLIENT | Client / Admin |
| CONFIRMED | ARRIVED | Detailer / Admin |
| CONFIRMED | IN_PROGRESS | Detailer / Admin |
| CONFIRMED | CANCELLED_BY_CLIENT | Client / Admin |
| CONFIRMED | CANCELLED_BY_DETAILER | Detailer / Admin |
| ARRIVED | IN_PROGRESS | Detailer / Admin |
| IN_PROGRESS | COMPLETED | Detailer / Admin |
| IN_PROGRESS | NO_SHOW | Detailer / Admin |

---

## Payments

```
POST /api/v1/payments/create-intent
Authorization: Bearer <client_token>
{ "appointment_id": "uuid" }
```

```json
{ "client_secret": "pi_xxx_secret_xxx", "appointment_id": "uuid", "amount_cents": 14400 }
```

Use `client_secret` with Stripe SDK to confirm payment on frontend.

---

## Fares (`/api/v1/fares`)

```
POST /api/v1/fares/estimate
```

Returns `estimated_price_cents`, `surge_multiplier`, `fare_token` (HMAC-signed, used in `/api/v1/rides/request`).

---

## Reviews (`/api/v1/reviews`)

```
POST /api/v1/reviews
Authorization: Bearer <client_token>
{ "appointment_id": "uuid", "rating": 5, "comment": "Excellent!" }
```

Appointment must be COMPLETED. One review per appointment.

```
GET /api/v1/reviews/detailer/{id}
```

---

## Notifications (`/api/v1/notifications`)

Push notifications via the Expo Push API — tokens have format `ExponentPushToken[…]`.

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/notifications/device-token` | Bearer | Register / refresh the current device's push token. Call after login |
| DELETE | `/api/v1/notifications/device-token` | Bearer | Unregister a push token. Call on logout |

Body (both verbs):

```json
{ "token": "ExponentPushToken[…]", "platform": "ios" | "android" }
```

Event-bus → push triggers (in `domains/notifications/handlers.py`):

| Event | Recipient | Notification |
|---|---|---|
| appointment.created (PENDING) | detailer | "New booking request" |
| CONFIRMED | client | "Booking confirmed!" |
| ARRIVED | client | "Your detailer has arrived" |
| IN_PROGRESS | client | "Service in progress" |
| COMPLETED | client | "All done! ⭐" |
| CANCELLED_BY_CLIENT | detailer | "Appointment cancelled" |
| CANCELLED_BY_DETAILER | client | "Appointment cancelled" |

---

## Admin (`/api/v1/admin/*`)

All endpoints require a Bearer token whose user has the `admin` role. Responses always go through `require_role("admin")`.

### Stats / Users / Roles / Permissions

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/admin/stats` | Platform-wide counters (`total_users`, `total_detailers`, `pending_verification`, …) |
| GET | `/api/v1/admin/users?page&per_page&search&role` | Paginated user list |
| GET | `/api/v1/admin/users/{id}` | User detail with roles + effective permissions |
| PATCH | `/api/v1/admin/users/{id}` | Set `is_active` (ban/unban) |
| GET | `/api/v1/admin/users/{id}/roles` | List roles for the user |
| POST | `/api/v1/admin/users/{id}/roles` | Assign role — `{ role_id }` |
| DELETE | `/api/v1/admin/users/{id}/roles/{role_id}` | Revoke role |
| GET | `/api/v1/admin/roles` | All roles with permissions |
| POST | `/api/v1/admin/roles` | Create role — `{ name, description }` |
| PATCH | `/api/v1/admin/roles/{id}` | Update role (non-system only) |
| DELETE | `/api/v1/admin/roles/{id}` | Soft-delete role (non-system only) |
| POST | `/api/v1/admin/roles/{id}/permissions` | Assign permission — `{ permission_id }` |
| DELETE | `/api/v1/admin/roles/{id}/permissions/{permission_id}` | Revoke permission |
| GET | `/api/v1/admin/permissions` | Permission catalog (18 seeded) |
| POST | `/api/v1/admin/permissions` | Create permission — `{ name, resource, action, description }` |
| DELETE | `/api/v1/admin/permissions/{id}` | Delete permission (removes from all roles) |

### Appointments (Sprint 9)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/admin/appointments?page&per_page&status&start_date&end_date&search` | Paginated cross-tenant list |
| GET | `/api/v1/admin/appointments/{id}` | Full detail |
| PATCH | `/api/v1/admin/appointments/{id}/status` | Force status — `{ new_status }` — bypasses FSM but writes audit record |

### Verifications (Sprint 9 — detailer KYC queue)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/admin/verifications?verification_status=pending\|approved\|rejected` | Verification queue |
| POST | `/api/v1/admin/verifications/{provider_id}/approve` | Approve KYC |
| POST | `/api/v1/admin/verifications/{provider_id}/reject` | Reject — `{ reason }` |

### Payments (Sprint 9)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/admin/payments/summary?start_date&end_date` | 4-card summary (gross, refunds, payouts, commission) |
| GET | `/api/v1/admin/payments/ledger?page&per_page&entry_type&start_date&end_date` | Append-only ledger entries (`entry_type`: `CAPTURE \| REFUND \| PAYOUT \| CHARGE_COMMISSION \| AUTHORIZATION`) |

---

## Stripe Webhook

```
POST /webhooks/stripe
Stripe-Signature: <hmac>
```

Handles: `payment_intent.succeeded` · `payment_intent.payment_failed` · `identity.verification_session.verified`.

---

## WebSocket

```
WS /ws/appointments/{appointment_id}?token=<access_token>
```

JWT goes in query param — WS connections cannot send headers after handshake.

**Access**: must be client, detailer, or admin on that appointment.

**Close codes:**

| Code | Meaning |
|---|---|
| 4001 | Unauthorized — bad/missing token |
| 4003 | Forbidden — not a participant |
| 4004 | Appointment not found |

**Client → server:**

```json
{ "type": "ping" }
{ "type": "location_update", "lat": 41.0793, "lng": -85.1394 }
```

`location_update` is only processed when sent by the detailer.

**Server → client:**

```json
{ "type": "pong" }
{ "type": "status_change", "status": "arrived", "appointment_id": "uuid", "ts": "…" }
{ "type": "location_update", "lat": 41.0793, "lng": -85.1394, "ts": "…" }
```

---

## Error format

```json
{ "detail": "Human-readable error message" }
```

| Code | Meaning |
|---|---|
| 400 | Bad request |
| 401 | Unauthorized — missing or invalid token |
| 403 | Forbidden — insufficient role |
| 404 | Not found |
| 409 | Conflict — slot already taken, duplicate resource |
| 413 | Payload too large (> 5 MB) |
| 422 | Validation error |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Rate limits

| Endpoint | Limit |
|---|---|
| POST `/auth/identify` | 10/min per IP |
| POST `/auth/verify` | 10/min per IP |
| POST `/auth/token` | 10/min per IP |
| POST `/auth/refresh` | 5/min per IP |
| POST `/auth/google` | 5/min per IP |
| POST `/auth/apple` | 5/min per IP |

---

## Data formats

| Type | Format |
|---|---|
| Timestamps | ISO 8601 UTC — `2027-06-15T14:00:00Z` |
| Prices | Integer cents — `$29.00` → `2900`. Display: `/ 100` |
| Coordinates | Decimal degrees — lat `-90..90`, lng `-180..180` |
| Pagination | `?page=1&page_size=20` → `{ items, total, page, page_size }` |

**Vehicle size multipliers:**

| Size | Examples | Multiplier |
|---|---|---|
| `small` | Sedan, Coupe, Hatchback | ×1.0 |
| `medium` | SUV, Crossover | ×1.2 |
| `large` | Pickup Truck | ×1.5 |
| `xl` | Van, Minivan, Sprinter | ×2.0 |

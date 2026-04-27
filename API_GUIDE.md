# RayCarWash API guide

Complete reference for frontend integration.

**Base URL**: `http://localhost:8000`
**Docs**: `/docs` (Swagger) · `/redoc`

---

## Two API clients — critical

The frontend uses two separate Axios instances:

```
authClient  → base URL: /auth       (login, identify, verify, social, refresh)
apiClient   → base URL: /api/v1     (everything else)
```

Never call auth endpoints through `apiClient` — they live at `/auth`, not `/api/v1/auth`.

---

## Authentication flow (identifier-first, Uber style)

### Step 1 — Identify

```
POST /auth/identify
{ "identifier": "user@example.com" }   // email or phone
```

Response:
```json
{
  "is_new_user": false,
  "available_methods": ["password", "passkey"]
}
```

---

### Step 2 — Verify

**Existing user (password)**:
```
POST /auth/verify
{ "identifier": "user@example.com", "password": "YourPassword" }
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**New user** (same endpoint):
```json
{
  "registration_token": "eyJ...",
  "needs_profile_completion": true
}
```

**Social login**:
```
POST /auth/verify
{ "identifier": "user@example.com", "provider": "google", "token": "google_access_token" }
```

Provider values: `"google"` | `"apple"`

---

### Step 3 — Complete profile (new users only)

Use `registration_token` as Bearer token. Expires in 30 minutes.

```
PUT /auth/complete-profile
Authorization: Bearer <registration_token>

{
  "full_name": "John Doe",
  "phone_number": "+12345678901",
  "role": "client"
}
```

Role values: `"client"` | `"detailer"`

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

After this call, store both tokens and route by role:
- `client` → Main tabs
- `detailer` → `DetailerOnboarding` if no profile exists, else `DetailerMain` tabs

---

### Token refresh

Tokens expire in 30 minutes. Refresh token lasts 7 days.

```
POST /auth/refresh?refresh_token=eyJ...
```

Response:
```json
{
  "access_token": "new_access_token",
  "refresh_token": "new_refresh_token",
  "token_type": "bearer"
}
```

---

### Password reset

```
POST /auth/password-reset
{ "email": "user@example.com" }
```

Always returns 200 (prevents email enumeration).

---

### Get current user

```
GET /auth/me
Authorization: Bearer <access_token>
```

---

### Update profile

```
PUT /auth/update
Authorization: Bearer <access_token>

{
  "full_name": "John Doe",
  "phone_number": "+12345678901",
  "profile_photo_url": "https://..."
}
```

All fields optional — partial update supported.

---

## Endpoints reference

### Vehicles (`/api/v1/vehicles`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/vehicles` | Bearer(client) | Create vehicle |
| GET | `/api/v1/vehicles` | Bearer(client) | List own vehicles |
| GET | `/api/v1/vehicles/{id}` | Bearer(client) | Vehicle detail |
| PUT | `/api/v1/vehicles/{id}` | Bearer(client) | Update vehicle |
| DELETE | `/api/v1/vehicles/{id}` | Bearer(client) | Soft delete |
| GET | `/api/v1/vehicles/lookup/{vin}` | Bearer | NHTSA VIN decode |

**Create vehicle**:
```json
{
  "make": "Toyota",
  "model": "Camry",
  "year": 2023,
  "color": "Silver",
  "license_plate": "ABC123",
  "vin": "1HGBH41JXMN109186"
}
```

`body_class` is returned from NHTSA and stored. `VehicleSize` is derived from it at runtime — never sent by the client.

---

### Services (`/api/v1/services`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/services` | — | List all active services |
| GET | `/api/v1/services/{id}` | — | Service detail |

Response fields:
```json
{
  "id": "uuid",
  "name": "Full Detail",
  "description": "Complete interior and exterior",
  "base_price_cents": 12000,
  "price_small": 12000,
  "price_medium": 14400,
  "price_large": 18000,
  "price_xl": 24000,
  "base_duration_minutes": 180,
  "duration_small": 180,
  "duration_medium": 216,
  "duration_large": 270,
  "duration_xl": 360
}
```

---

### Addons (`/api/v1/addons`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/addons` | — | List all active add-ons |

```json
[
  {
    "id": "uuid",
    "name": "Clay Bar Treatment",
    "description": "Remove embedded contaminants",
    "price_cents": 3000,
    "duration_minutes": 45
  }
]
```

---

### Detailers (`/api/v1/detailers`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/detailers` | — | Search by geo + filters |
| GET | `/api/v1/detailers/me` | Bearer(detailer) | Own profile + stats |
| PUT | `/api/v1/detailers/me` | Bearer(detailer) | Upsert own profile |
| PATCH | `/api/v1/detailers/me/status` | Bearer(detailer) | Toggle accepting bookings |
| GET | `/api/v1/detailers/me/services` | Bearer(detailer) | Catalog with detailer toggle state |
| PATCH | `/api/v1/detailers/me/services/{id}` | Bearer(detailer) | Toggle service + custom price |
| GET | `/api/v1/detailers/{id}/availability` | — | Available slots |
| POST | `/api/v1/detailers/location` | Bearer(detailer) | Update GPS position |
| GET | `/api/v1/detailers/{id}/profile` | — | Public profile |

**Search query params**:
```
GET /api/v1/detailers?lat=41.0793&lng=-85.1394&radius_miles=25&min_rating=4.0&page=1&page_size=20
```

**Upsert own profile**:
```json
{
  "bio": "5 years of professional detailing",
  "years_of_experience": 5,
  "service_radius_miles": 25,
  "working_hours": {
    "monday": { "start": "08:00", "end": "18:00" },
    "tuesday": { "start": "08:00", "end": "18:00" }
  }
}
```

**Availability query**:
```
GET /api/v1/detailers/{id}/availability?request_date=2025-12-20&service_id={uuid}&vehicle_size=medium
```

---

### Matching (`/api/v1/matching`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/matching` | Bearer(client) | Ranked detailers + available slots |

Query params:
```
lat           float    required
lng           float    required
date          string   required (YYYY-MM-DD)
service_id    UUID     required
vehicle_sizes string   required (comma-sep: "small,medium")
addon_ids     string   optional (comma-sep UUIDs)
radius_miles  float    optional (default 25)
```

Response includes `distance_miles`, `estimated_price`, `estimated_duration`, and `available_slots` per detailer.

---

### Appointments (`/api/v1/appointments`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/appointments` | Bearer(client) | Create booking |
| GET | `/api/v1/appointments` | Bearer | List own (paginated) |
| GET | `/api/v1/appointments/{id}` | Bearer | Detail |
| PATCH | `/api/v1/appointments/{id}/status` | Bearer | Status transition |

**Create (single vehicle)**:
```json
{
  "detailer_id": "uuid",
  "vehicle_id": "uuid",
  "service_id": "uuid",
  "scheduled_time": "2025-12-20T14:00:00Z",
  "service_address": "123 Main St, Fort Wayne, IN",
  "service_latitude": 41.0793,
  "service_longitude": -85.1394,
  "client_notes": "Please arrive on time"
}
```

**Create (multi-vehicle)**:
```json
{
  "detailer_id": "uuid",
  "scheduled_time": "2025-12-20T14:00:00Z",
  "service_address": "123 Main St",
  "service_latitude": 41.0793,
  "service_longitude": -85.1394,
  "vehicles": [
    { "vehicle_id": "uuid1", "service_id": "uuid", "addon_ids": ["addon_uuid"] },
    { "vehicle_id": "uuid2", "service_id": "uuid" }
  ]
}
```

**Status update**:
```json
{
  "status": "confirmed",
  "detailer_notes": "On my way"
}
```

**Valid transitions**:

| From | To | Who |
|---|---|---|
| PENDING | CONFIRMED | Detailer / Admin |
| PENDING | CANCELLED_BY_CLIENT | Client / Admin |
| CONFIRMED | ARRIVED | Detailer / Admin |
| CONFIRMED | IN_PROGRESS | Detailer / Admin |
| CONFIRMED | CANCELLED_BY_CLIENT | Client / Admin |
| CONFIRMED | CANCELLED_BY_DETAILER | Detailer / Admin |
| ARRIVED | IN_PROGRESS | Detailer / Admin |
| IN_PROGRESS | COMPLETED | Detailer / Admin (requires `actual_price`) |
| IN_PROGRESS | NO_SHOW | Detailer / Admin |

Auto-stamped timestamps: `arrived_at` on ARRIVED · `started_at` on IN_PROGRESS · `completed_at` on COMPLETED.

---

### Payments (`/api/v1/payments`)

```
POST /api/v1/payments/create-intent
Authorization: Bearer <client_token>

{ "appointment_id": "uuid" }
```

Response:
```json
{
  "client_secret": "pi_xxx_secret_xxx",
  "appointment_id": "uuid",
  "amount_cents": 14400
}
```

Use `client_secret` with Stripe SDK on the frontend to confirm the payment.

---

### Reviews (`/api/v1/reviews`)

```
POST /api/v1/reviews
Authorization: Bearer <client_token>

{
  "appointment_id": "uuid",
  "rating": 5,
  "comment": "Excellent service!"
}
```

Appointment must be in COMPLETED state. One review per appointment.

```
GET /api/v1/reviews/detailer/{id}
```

---

### Webhooks

```
POST /webhooks/stripe
Stripe-Signature: <hmac>
```

Handles: `payment_intent.succeeded`, `payment_intent.payment_failed`, `identity.verification_session.verified`.

---

## WebSocket

```
WS /ws/appointments/{appointment_id}?token=<access_token>
```

JWT in query param — WS connections cannot send headers after handshake.

**Access**: must be client, detailer, or admin on the appointment.

**Close codes**:
| Code | Meaning |
|---|---|
| 4001 | Unauthorized (bad/missing token) |
| 4003 | Forbidden (not a participant) |
| 4004 | Appointment not found |

**Client → server**:
```json
{ "type": "ping" }
{ "type": "location_update", "lat": 41.0793, "lng": -85.1394 }
```

`location_update` is only processed when sent by the detailer.

**Server → client**:
```json
{ "type": "pong" }
{ "type": "status_change", "status": "arrived", "appointment_id": "uuid", "ts": "2026-04-11T..." }
{ "type": "location_update", "lat": 41.0793, "lng": -85.1394, "ts": "2026-04-11T..." }
```

**Frontend hook** (`useAppointmentSocket`):
```ts
const { sendLocationUpdate } = useAppointmentSocket({
  appointmentId: appt.id,
  onStatusChange: (status) => setStatus(status),
  onLocationUpdate: ({ lat, lng }) => setMarker({ lat, lng }),
});
```

Hook handles: auto-connect, exponential backoff (1s → 30s max), heartbeat ping every 30s. `WS_BASE_URL` in `api.ts` replaces `http(s)://` with `ws(s)://` automatically.

---

## Error format

All errors:
```json
{ "detail": "Human-readable error message" }
```

| Code | Meaning |
|---|---|
| 400 | Bad request |
| 401 | Unauthorized — missing or invalid token |
| 403 | Forbidden — not authorized for this action |
| 404 | Not found |
| 409 | Conflict — e.g. slot already taken |
| 422 | Validation error |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Rate limits

| Endpoint | Limit |
|---|---|
| POST /auth/identify | 10/min per IP |
| POST /auth/verify | 10/min per IP |
| POST /auth/token | 10/min per IP |
| POST /auth/refresh | 5/min per IP |
| POST /auth/google | 5/min per IP |
| POST /auth/apple | 5/min per IP |

---

## Formats

**Timestamps**: ISO 8601 UTC — `2025-12-20T14:00:00Z`

**Prices**: integer cents — `$29.00` → `2900`. Display: `price_cents / 100`.

**Coordinates**: decimal degrees — lat `-90` to `90`, lng `-180` to `180`.

**Vehicle sizes**:

| Size | Examples | Price multiplier |
|---|---|---|
| small | Sedan, Coupe | ×1.0 |
| medium | SUV, Crossover, Compact Pickup | ×1.2 |
| large | Crew Cab Pickup, Large SUV | ×1.5 |
| xl | Van, Sprinter | ×2.0 |
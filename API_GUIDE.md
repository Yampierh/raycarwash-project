# RayCarWash API Guide

Complete API reference for frontend integration.

**Base URL**: `http://localhost:8000`
**Version**: `v1`

---

## Authentication Flow

### 1. Login (Email/Password)

```
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=email@example.com&password=YourPassword
```

**Response** (200):
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**Usage**: Include in all subsequent requests:
```
Authorization: Bearer <access_token>
```

---

### 2. Token Refresh

Tokens expire in 30 minutes. Use refresh token to get new pair.

```
POST /auth/refresh
Content-Type: application/json

{ "refresh_token": "eyJ..." }
```

**Response** (200):
```json
{
  "access_token": "new_access_token",
  "refresh_token": "new_refresh_token",
  "token_type": "bearer"
}
```

---

### 3. Social Login

**Google**:
```
POST /auth/google
{ "access_token": "google_oauth_access_token" }
```

**Apple**:
```
POST /auth/apple
{ "identity_token": "apple_identity_token", "full_name": "John Doe" }
```

---

### 4. Password Reset

```
POST /auth/password-reset
{ "email": "user@example.com" }
```

**Note**: Always returns 200 (prevents email enumeration).

---

## Endpoints Reference

### Auth Endpoints (`/auth`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/token` | ❌ | Login with email/password |
| POST | `/auth/refresh` | ❌ | Refresh access token |
| GET | `/auth/me` | ✅ | Get current user profile |
| PUT | `/auth/update` | ✅ | Update user profile |
| POST | `/auth/google` | ❌ | Google OAuth login |
| POST | `/auth/apple` | ❌ | Apple OAuth login |
| POST | `/auth/password-reset` | ❌ | Request password reset |

---

### User Endpoints (`/api/v1/users`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/users` | ❌ | Register new user |

**Register Request**:
```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "phone_number": "+1234567890",
  "role_names": ["client"]  // or ["detailer"]
}
```

---

### Vehicle Endpoints (`/api/v1/vehicles`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/vehicles` | ✅ Client | Create vehicle |
| GET | `/api/v1/vehicles` | ✅ Client | List own vehicles |
| GET | `/api/v1/vehicles/lookup/{vin}` | ✅ | Decode VIN via NHTSA |
| PUT | `/api/v1/vehicles/{id}` | ✅ Owner | Update vehicle |
| DELETE | `/api/v1/vehicles/{id}` | ✅ Owner | Soft-delete vehicle |

**Create Vehicle**:
```json
{
  "make": "Toyota",
  "model": "Camry",
  "year": 2023,
  "license_plate": "ABC123",
  "color": "Silver",
  "vin": "1HGBH41JXMN109186"  // optional
}
```

---

### Service Endpoints (`/api/v1/services`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/services` | ❌ | List all services |
| GET | `/api/v1/services/{id}` | ❌ | Get service detail |

**Response**:
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

### Addon Endpoints (`/api/v1/addons`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/addons` | ❌ | List all active add-ons |

**Response**:
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

### Detailer Endpoints (`/api/v1/detailers`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/detailers` | ❌ | Search detailers (geo-filter) |
| GET | `/api/v1/detailers/me` | ✅ Detailer | Get own profile |
| PUT | `/api/v1/detailers/me` | ✅ Detailer | Create/update profile |
| PATCH | `/api/v1/detailers/me/status` | ✅ Detailer | Toggle accepting bookings |
| GET | `/api/v1/detailers/me/services` | ✅ Detailer | List services |
| PATCH | `/api/v1/detailers/me/services/{id}` | ✅ Detailer | Toggle service |
| GET | `/api/v1/detailers/{id}/availability` | ❌ | Get available slots |
| POST | `/api/v1/detailers/location` | ✅ Detailer | Update GPS location |
| GET | `/api/v1/detailers/{id}/profile` | ❌ | Get public profile |

**Search Query Params**:
```
GET /api/v1/detailers?lat=41.0793&lng=-85.1394&radius_miles=25&min_rating=4.0&page=1&page_size=20
```

**Availability Query**:
```
GET /api/v1/detailers/{id}/availability?request_date=2025-12-20&service_id={uuid}&vehicle_size=medium
```

---

### Matching Endpoints (`/api/v1/matching`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/matching` | ✅ Client | Smart matching |

**Query Params**:
```
lat: float (required)
lng: float (required)
date: string (YYYY-MM-DD, required)
service_id: UUID (required)
vehicle_sizes: string (comma-separated: "small,medium", required)
addon_ids: string (comma-separated UUIDs, optional)
radius_miles: float (default 25, optional)
```

**Response**:
```json
[
  {
    "user_id": "uuid",
    "full_name": "John Detailer",
    "bio": "Professional detailer",
    "years_of_experience": 5,
    "service_radius_miles": 25,
    "is_accepting_bookings": true,
    "average_rating": 4.8,
    "total_reviews": 50,
    "distance_miles": 5.2,
    "estimated_price": 14400,
    "estimated_duration": 216,
    "available_slots": [
      { "start_time": "2025-12-20T10:00:00Z", "end_time": "2025-12-20T10:30:00Z", "is_available": true }
    ]
  }
]
```

---

### Appointment Endpoints (`/api/v1/appointments`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/appointments` | ✅ Client | Create appointment |
| GET | `/api/v1/appointments/mine` | ✅ | List own appointments |
| GET | `/api/v1/appointments/{id}` | ✅ Participant | Get detail |
| PATCH | `/api/v1/appointments/{id}/status` | ✅ Participant | Update status |

**Create (Single Vehicle)**:
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

**Create (Multi-Vehicle - Sprint 5)**:
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
  ],
  "client_notes": "Two vehicles"
}
```

**Status Update**:
```json
{
  "status": "confirmed",
  "detailer_notes": "Will arrive on time"
}
```

**Valid Status Transitions**:
| From | To | Who |
|------|----|----|
| PENDING | CONFIRMED | Detailer/Admin |
| PENDING | CANCELLED_BY_CLIENT | Client/Detailer/Admin |
| CONFIRMED | IN_PROGRESS | Detailer/Admin |
| CONFIRMED | CANCELLED_BY_CLIENT | Client/Detailer/Admin |
| IN_PROGRESS | COMPLETED | Detailer/Admin (requires actual_price) |
| IN_PROGRESS | NO_SHOW | Detailer/Admin |

---

### Payment Endpoints (`/api/v1/payments`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/payments/create-intent` | ✅ Client | Create Stripe PaymentIntent |

**Request**:
```json
{ "appointment_id": "uuid" }
```

**Response**:
```json
{
  "client_secret": "pi_xxx_secret_xxx",
  "appointment_id": "uuid",
  "amount_cents": 14400
}
```

---

### Review Endpoints (`/api/v1/reviews`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/reviews` | ✅ Client | Submit review |
| GET | `/api/v1/reviews/detailer/{id}` | ❌ | List detailer reviews |

**Create Review**:
```json
{
  "appointment_id": "uuid",
  "rating": 5,
  "comment": "Excellent service!"
}
```

---

### Webhook Endpoints (`/webhooks`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/webhooks/stripe` | Stripe-Signature | Receive Stripe events |

---

## Error Responses

All errors follow this format:

```json
{ "detail": "Human-readable error message" }
```

| HTTP Code | Meaning |
|-----------|---------|
| 400 | Bad request - invalid body |
| 401 | Unauthorized - missing/invalid token |
| 403 | Forbidden - not authorized |
| 404 | Not found |
| 409 | Conflict - e.g., slot taken |
| 422 | Validation error |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| POST /auth/token | 10/min per IP |
| POST /auth/refresh | 5/min per IP |
| POST /auth/google | 5/min per IP |
| POST /auth/apple | 5/min per IP |

---

## Date/Time Format

All timestamps are in ISO 8601 UTC format:
- `2025-12-20T14:00:00Z` (appointment scheduling)
- `2025-12-20T10:30:00Z` (slot times)

---

## Prices

All prices are in **USD cents** (integer):
- `$29.00` → `2900`
- `$144.00` → `14400`

To display: `price_cents / 100`

---

## Vehicle Sizes

| Size | Vehicles | Multiplier |
|------|----------|------------|
| small | Sedan, Coupe | ×1.0 |
| medium | SUV, Crossover, Compact Pickup | ×1.2 |
| large | Crew Cab Pickup, Large SUV | ×1.5 |
| xl | Van, Sprinter | ×2.0 |

---

## Testing Checklist

- [ ] Login returns access + refresh token
- [ ] Token refresh works
- [ ] Protected endpoints reject without token
- [ ] Vehicles CRUD works for clients
- [ ] Detailer search by location works
- [ ] Availability returns correct slots
- [ ] Appointment creation calculates correct price
- [ ] Status transitions follow state machine
- [ ] PaymentIntent created successfully

---

## Frontend Integration Notes

1. **Auth Client vs API Client**:
   - `authClient` → base `/auth` (login, refresh, social)
   - `apiClient` → base `/api/v1` (all other endpoints)

2. **Token Storage**:
   - Access token: short-lived (30 min)
   - Refresh token: longer (7 days)
   - Store securely (expo-secure-store on mobile)

3. **Error Handling**:
   - 401 triggers token refresh
   - If refresh fails → redirect to login

4. **Coordinate Format**:
   - Use decimal degrees (41.0793, -85.1394)
   - Latitude: -90 to 90
   - Longitude: -180 to 180
# 21 — API Contracts: Track 3 — Customer Dashboard Endpoints

> **Status:** Contract — approved for implementation
> **Priority:** High
> **Design source:** `raycarwash/project/Customer Dashboard.html` + `cdash.css` (614 lines)
> **Domain:** `backend/domains/users/` + `backend/domains/appointments/`

---

## Overview

6 new endpoints for the customer dashboard. The frontend components (`cdash-*.jsx`) are **not yet built** — these contracts define the backend first. Frontend will be built in a subsequent pass after Claude Design finalizes the UI.

Existing client endpoints already cover: appointments list, vehicles, addresses, payment methods, favorites, matching, booking flow.

---

## 1. `GET /api/v1/customers/me/dashboard`

Home view — next booking + aggregated stats.

```
Auth: JWT (role: client)
```

### Response

```typescript
// Envelope<CustomerDashboardResponse>
{
  "next_appointment": {
    "id": "uuid",
    "service_name": "Full detail",
    "status": "confirmed",
    "scheduled_at": "2026-05-20T14:00:00Z",
    "eta_min": 22,
    "detailer": {
      "name": "Marcus Tate",
      "initials": "MT",
      "rating": 4.92,
      "total_jobs": 312,
      "avatar_url": null
    },
    "address": "123 Lake Ave, Fort Wayne, IN"
  },
  "stats": {
    "total_bookings": 14,
    "total_spent_cents": 198600,
    "member_since": "Jan 2024",
    "saved_detailers": 3,
    "active_subscriptions": 1
  },
  "subscriptions": [
    {
      "id": "uuid",
      "plan_name": "Monthly full detail",
      "price_cents": 14900,
      "next_date": "2026-06-01",
      "status": "active"
    }
  ],
  "recommended_services": [
    { "name": "Pet hair removal", "price_cents": 2500, "popular": true }
  ]
}
```

### Data sources

| Field | Source |
|---|---|
| `next_appointment` | First upcoming appointment via `GET /appointments/mine` filtered |
| `stats.total_bookings` | `SELECT COUNT(*) FROM appointments WHERE client_id = ?` <!-- FIX D3 --> |
| `stats.total_spent` | Sum of completed appointment prices |
| `stats.member_since` | User's `created_at` formatted |
| `stats.saved_detailers` | Count from `favorites` |
| `subscriptions` | New `subscriptions` table (future) |
| `recommended_services` | Based on add-ons not yet purchased |

---

## 2. `POST /api/v1/appointments/{id}/cancel`

<!-- FIX D8 + Cancel Overlap Decision (May 2026): este endpoint es un **wrapper** de la lógica FSM existente (`PATCH /api/v1/appointments/{id}/status`), NO la reemplaza.
- Resuelve el target_status automáticamente basado en el rol del JWT: `client` → `CANCELLED_BY_CLIENT`. El detailer continúa cancelando vía PATCH (transición a `CANCELLED_BY_DETAILER`).
- Delega al mismo servicio FSM que ya enforza VALID_TRANSITIONS (zero duplicación de reglas de estado).
- Agrega refund + idempotency-key (cosas que PATCH /status no hace).
- Response normaliza el enum a `"status": "canceled"` como **alias UI**: el frontend no necesita conocer `cancelled_by_client` vs `cancelled_by_detailer`. -->

Cancel appointment with refund calculation. Customer-only entry point — detailers cancelling continue to use `PATCH /api/v1/appointments/{id}/status`.

```
Auth: JWT (role: client)
Idempotency-Key: REQUIRED  (financial — prevents double refund)
```

### Request

```json
{
  "reason": "string (optional, max 500)"
}
```

### Response — 200

```json
{
  "id": "uuid",
  "status": "canceled",
  "refund_cents": 14900,
  "refund_pct": 100,
  "refund_note": "Full refund — cancelled more than 24h before appointment"
}
```

> `status: "canceled"` is a normalized UI alias. The DB enum value persisted is `cancelled_by_client` (British spelling, split by actor — see [appointments/models.py](../../backend/domains/appointments/models.py)).

### Refund calculation

| Time before appointment | Refund % |
|---|---|
| >= 24 hours | 100% |
| 2 – 24 hours | 50% |
| < 2 hours | 0% |

### Side effects

1. FSM transition via existing service: current → `cancelled_by_client` (validates VALID_TRANSITIONS — never bypassed)
2. Refund processed via Stripe inside the same DB transaction as the FSM transition
3. Audit log entry (action: `appointment.canceled`, metadata includes `refund_cents`, `refund_pct`, `previous_status`)
4. Notification to detailer (if already assigned)
5. WebSocket event broadcast to appointment room

---

## 3. `GET /api/v1/customers/me/rewards`

```
Auth: JWT (role: client)
```

### Response

```typescript
{
  "tier": "Gold",
  "points": 2840,
  "next_tier": "Platinum",
  "points_to_next": 1160,
  "progress_pct": 71,
  "perks": [
    { "name": "Priority scheduling", "unlocked": true },
    { "name": "Free add-on monthly", "unlocked": true },
    { "name": "VIP support", "unlocked": false }
  ]
}
```

### Data source

New `rewards` table / service. Points calculated from:
- 100 points per dollar spent
- 500 points per review submitted
- 1000 bonus points on referral

### Tier thresholds

| Tier | Points required | Perks |
|---|---|---|
| Silver | 0 | Base |
| Gold | 2000 | Priority scheduling, free add-on monthly |
| Platinum | 4000 | All above + VIP support |

---

## 4. `GET /api/v1/users/me/notification-preferences`

## 5. `PUT /api/v1/users/me/notification-preferences`

```
Auth: JWT
```

### Shared schema

```typescript
{
  "push": {
    "appointment_reminders": true,
    "status_updates": true,
    "promotions": false
  },
  "email": {
    "appointment_reminders": true,
    "receipts": true,
    "promotions": true,
    "newsletter": false
  },
  "sms": {
    "appointment_reminders": true,
    "eta_updates": true
  }
}
```

### Data source

New `notification_preferences` table (user_id → JSONB).

---

## 6. `POST /api/v1/users/me/referrals` (post-MVP)

```
Auth: JWT (role: client)
```

### Request

```json
{
  "code": "FRIEND20"
}
```

### Response — 200

```json
{
  "valid": true,
  "discount_cents": 2000,
  "expires_at": "2026-06-19"
}
```

### Response — invalid

```json
{
  "valid": false,
  "reason": "Code expired"
}
```

---

## Existing endpoints — already cover these views

| Customer Dashboard view | Existing endpoint |
|---|---|
| Bookings list | `GET /api/v1/appointments/mine` |
| Booking detail | `GET /api/v1/appointments/{id}` |
| Track (live status) | `PATCH /api/v1/appointments/{id}/status` + WebSocket `/ws/appointments/{id}` |
| Garage — vehicles | `GET /api/v1/vehicles` + `POST/DELETE` |
| Garage — favorites | `GET /api/v1/users/me/favorites/providers` |
| Account — addresses | `GET /api/v1/users/me/addresses` |
| Account — payment methods | `GET /api/v1/users/me/payment-methods` |
| Account — profile | `GET /api/v1/users/me` + `PATCH /api/v1/users/me` |

---

## Implementation Order

### Phase 1 (backend only)
1. Cancel appointment endpoint (2) — highest impact for current client app
2. Notification preferences (4, 5) — needed for settings views
3. Customer dashboard aggregate (1)

### Phase 2 (backend + design)
4. Rewards system (3) — needs domain model + tier logic
5. Referrals (6) — post-MVP, lowest priority

### Frontend (after Claude Design)
The 10 cdash-*.jsx components will be built in a separate pass once the UI design is finalized.

---

## 7. Operational Requirements

### 7.1 Rate Limiting

| Endpoint | Method | Limit | Burst | Notes |
|----------|--------|-------|-------|-------|
| `/customers/me/dashboard` | GET | 30/min per user | 50 | Aggregate query across appointments + rewards |
| `/appointments/{id}/cancel` | POST | **3/min per user** | 5 | Financial — prevents accidental flood |
| `/customers/me/rewards` | GET | 30/min per user | 50 | — |
| `/users/me/notification-preferences` | GET | 30/min per user | 50 | — |
| `/users/me/notification-preferences` | PUT | 10/min per user | 15 | — |
| `/users/me/referrals` | POST | 5/min per user | 8 | Post-MVP |

### 7.2 Idempotency Requirements

| Endpoint | Idempotency-Key | Rationale |
|----------|----------------|-----------|
| `POST /appointments/{id}/cancel` | **Required** | **Prevents double-refund** — CRITICAL. Refund calculation runs once only |
| `POST /users/me/referrals` | Recommended | Prevents double-referral credit |
| `PUT /users/me/notification-preferences` | Recommended | Prevents duplicate settings update |

**CRITICAL NOTE for cancel:** The idempotency middleware must include `user_id` in cache key (see audit finding H1 in Plan 22). Without this, one customer's cancel response could be returned to another customer using the same key.

### 7.3 Effective Validation Constraints

| Endpoint | Field | Constraint | Additional |
|----------|-------|-----------|------------|
| `POST /appointments/{id}/cancel` | `reason` | max_length=500, strip, optional | XSS-sanitized |
| `POST /appointments/{id}/cancel` | path param `id` | UUID format | Valid appointment belonging to user |
| `POST /users/me/referrals` | `code` | max_length=50, alphanumeric + underscore | uppercase normalized |
| All `PUT` body fields | All strings | max_length=255, strip_whitespace=True | — |

### 7.4 Required HTTP Headers

| Header | Source | Details |
|--------|--------|---------|
| `X-Request-ID` | Middleware (existing) | All responses |
| `X-Process-Time` | Middleware | All responses (ms precision) |
| `Idempotency-Key` | Request | **Required** on cancel; recommended on others |
| `Retry-After` | Response | On 429 rate-limited responses |
| `Cache-Control` | Response | `no-store` on all (user-specific data) |

### 7.5 Required Database Indexes

<!-- FIX D3: la columna de fk al cliente en `appointments` es `client_id` (no `user_id`). El índice debe usar el nombre real. -->

```sql
-- Customer dashboard aggregate: upcoming appointment
CREATE INDEX CONCURRENTLY ix_appointments_client_status_time
  ON appointments(client_id, status, scheduled_time)
  WHERE is_deleted = FALSE;

-- Rewards lookup (rewards.user_id is correct here — rewards is a NEW table
-- and references users.id directly, not appointments)
CREATE INDEX CONCURRENTLY ix_rewards_user_id
  ON rewards(user_id)
  WHERE is_deleted = FALSE;

-- Notification preferences (single row per user)
-- Uses existing users.id PK
```

### 7.6 Refund Calculation Idempotency Guard

<!-- FIX D6 + Cancel Overlap Decision: la columna real es `stripe_payment_intent_id` (no `payment_intent_id`). El cancel se delega al servicio FSM existente — no se setea `appointment.status` inline; se llama `fsm_service.transition(..., target_status=AppointmentStatus.CANCELLED_BY_CLIENT)` que ya enforza VALID_TRANSITIONS y dispara los efectos (audit, websocket, notifications). -->

The cancel endpoint's refund logic must be protected against double-execution at two layers:

```python
# Pseudocode for refund safety (wrapper delegating to FSM service)
async def cancel_appointment(
    appointment_id: UUID,
    body: CancelRequest,
    current_user: User = Depends(require_role("client")),
    _idempotency: None = Depends(resolve_idempotency),  # post-auth guard (see H1 fix)
):
    # 1. Idempotency middleware + post-auth dep catches duplicate request (HTTP-level)
    # 2. App-level guard inside FSM service transaction:
    async with session.begin():
        appointment = await repo.get_for_update(appointment_id)
        if appointment.client_id != current_user.id:
            raise HTTPException(403, "Not your appointment")
        if appointment.status in TERMINAL_STATUSES:
            raise HTTPException(409, "Already in terminal state")

        # 3. FSM transition (validates VALID_TRANSITIONS internally)
        await fsm_service.transition(
            appointment=appointment,
            target_status=AppointmentStatus.CANCELLED_BY_CLIENT,
            actor=current_user,
            reason=body.reason,
        )

        # 4. Refund inside same transaction
        refund = calculate_refund(appointment)
        if refund.cents > 0 and appointment.stripe_payment_intent_id:
            await stripe_client.create_refund(
                payment_intent=appointment.stripe_payment_intent_id,
                amount_cents=refund.cents,
            )

        # 5. Audit log (FSM service already emits one for the transition;
        #    this one is additional with refund metadata)
        await audit_log.write(
            action="appointment.canceled",
            entity_id=str(appointment.id),
            metadata={
                "refund_cents": refund.cents,
                "refund_pct": refund.pct,
                "reason": body.reason,
            },
        )

    return CancelResponse(
        id=appointment.id,
        status="canceled",  # UI alias — see contract note above
        refund_cents=refund.cents,
        refund_pct=refund.pct,
        refund_note=refund.note,
    )
```

### 7.7 Observability (Prometheus Metrics)

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `customer_cancel_requests_total` | Counter | reason | Cancel endpoint usage |
| `customer_refund_total_cents` | Counter | refund_pct | Total refunds issued |
| `rewards_points_earned_total` | Counter | tier | Points earned across all customers |
| `notification_pref_updates_total` | Counter | channel | Notification preference changes |

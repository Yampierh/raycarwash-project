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

---

## 10. Design Reconciliation — cdash-* Views (May 2026)

> **Added 2026-05-19** after reading the Claude Design handoff bundle
> (`raycarwash/project/Customer Dashboard.html` + 10 `cdash-*.jsx` files).
> The original Plan 21 contract specified 6 endpoints; the design exposes
> richer data needs across 6 dashboard views. This section catalogues
> the gaps and the tables/endpoints required to close them.

### 10.1 View → Backend Endpoint Mapping

| View | What the design shows | Endpoints needed |
|------|------------------------|------------------|
| **Home** (`cdash-home.jsx`) | Hero: next appointment + detailer card. Rewards mini-card. Quick-book popular services. Recent bookings table (last 4). "For you" recommendations (3 cards). Vehicles list. Favorite detailers grid. | ✓ `GET /customers/me/dashboard` (§1) — extend to also return `vehicles_summary`, `favorites_summary`. <br>✓ Existing `GET /api/v1/appointments/mine?limit=4` for "Recent bookings". <br>✓ Existing `GET /api/v1/services` for "Quick book". <br>🔥 NEW `GET /customers/me/recommendations` for "For you". |
| **Bookings** (`cdash-bookings.jsx`) | List view with tabs (upcoming/past/canceled). Inline booking widget — service picker + 7-day grid + time slots. | ✓ Existing `GET /api/v1/appointments/mine?status=...`. <br>🔥 NEW `GET /api/v1/availability?service_id=X&date_from=Y&date_to=Z` — returns the day/slot grid (currently the matching domain handles single-shot matching, not browsing). |
| **Track** (`cdash-track.jsx`) | Live map (currently a placeholder SVG). Step timeline: `booking_confirmed → en_route → arrived & started → service_complete → payment & receipt`. Active detailer card. ETA. | ✓ Existing WebSocket `/ws/appointments/{id}` for live updates. <br>🔥 NEW `GET /api/v1/appointments/{id}/timeline` — returns the 5-step state history derived from FSM transitions in the audit log. <br>✓ Existing detailer location in `provider_profiles` for ETA computation. |
| **Garage** (`cdash-garage.jsx`) | Vehicles (manage). Active subscription plans. Favorite detailers grid. | ✓ Existing `GET /api/v1/vehicles`. <br>🔥 NEW `GET /customers/me/subscriptions` — needs new `subscriptions` table. <br>✓ Existing `GET /api/v1/users/me/favorites/providers`. |
| **Rewards** (`cdash-rewards.jsx`) | Tier badge + points header. Perks catalog (locked/unlocked). Activity ledger (earned/redeemed history). Referral CTA. | ✓ `GET /customers/me/rewards` (§3) — already returns tier + perks. <br>🔥 NEW `GET /customers/me/rewards/history?page=1&per_page=20` — paginated ledger from a new `rewards_ledger` table. <br>🔥 NEW `POST /customers/me/rewards/redeem` (perk_id) — atomic redemption. |
| **Account** (`cdash-account.jsx`) | Addresses, payment methods, profile, notification preferences, help. | ✓ All existing: `/api/v1/users/me/{addresses,payment-methods}`, `/api/v1/users/me`. <br>✓ §4/§5 notification-preferences from the original Plan 21. |

### 10.2 New Tables Required

| # | Table | Purpose | Used by | Migration |
|---|-------|---------|---------|-----------|
| **T1** | `rewards_ledger` | append-only history of every points event (earned, redeemed, bonus, expired). PK uuid; FK `user_id`; `delta_points INT NOT NULL`; `kind` enum (earn/redeem/bonus/expire); `description TEXT`; `reference_id` (optional FK to appointments/referrals); `balance_after_points` (denormalised running total). | Rewards view "Activity" tab + `GET /customers/me/rewards/history`. The current `points` field on a hypothetical `rewards` row is derived as the sum of `delta_points` (or read from `balance_after_points` on the latest row). | Future M21 |
| **T2** | `subscriptions` | recurring service plans ("Monthly full detail"). Columns: id, user_id, vehicle_id (optional), service_id, cadence (enum: weekly/biweekly/monthly), next_billing_date, status (active/paused/canceled), stripe_subscription_id, created_at. | Garage view "Active plans" section + `/customers/me/subscriptions`. Also surfaces in `/customers/me/dashboard` (already declared in Plan 21 §1 response schema). | Future M22 |
| **T3** | `recommendations` (or computed) | Personalised cards on Home view ("Time for an interior detail", "Spring ceramic special", "Add your Tesla to a plan"). Could be: <br>**Option A** — materialised view refreshed daily from rules over appointments + subscriptions. <br>**Option B** — config-driven (admin enters 3-5 cards, served as static list). <br>**Recommendation:** Start with Option B (admin CMS), upgrade to Option A once we have enough data. | `/customers/me/recommendations` | Future M23 (static config table) |
| **T4** | `appointment_status_history` (or use existing `audit_logs`) | Required for the Track view's 5-step timeline. The Appointment FSM already mutates `status` in-place; we need the historical sequence. The existing `audit_logs` table captures FSM transitions — extend the timeline endpoint to query it filtered by `entity_type='appointment' AND entity_id=...`. **No new table needed** if audit-log query performance is acceptable. | `GET /appointments/{id}/timeline` | None — reuse audit_logs |

### 10.3 New Endpoints Beyond the Original Plan 21

| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `/api/v1/customers/me/recommendations` | GET | client | Returns 3-5 personalised cards. Start as static config; upgrade later. |
| `/api/v1/availability` | GET | client | Query `?service_id=X&date_from=Y&date_to=Z`. Returns the day-grid + slot-grid shapes the design's booking widget uses. May overlap with `/api/v1/matching` — evaluate before duplication. |
| `/api/v1/appointments/{id}/timeline` | GET | client/detailer/admin | Returns FSM transition history (audit-log-derived) as the 5-step timeline. |
| `/api/v1/customers/me/subscriptions` | GET | client | List active subscription plans for the user. |
| `/api/v1/customers/me/subscriptions` | POST | client | Create a new subscription (creates Stripe Subscription too). |
| `/api/v1/customers/me/subscriptions/{id}` | PATCH | client | Pause/resume/cancel a subscription. |
| `/api/v1/customers/me/rewards/history` | GET | client | Paginated `rewards_ledger` query. |
| `/api/v1/customers/me/rewards/redeem` | POST | client | Idempotency-Key required. Atomic: deducts points + creates `appointments.discount_cents` or applies promo code to next booking. |

### 10.4 Out of Scope for This Sprint

Items the design surfaces but that we explicitly defer:

- **Live map rendering** — design uses an SVG placeholder; real-time GPS streaming to the customer is a follow-up that depends on `/ws/appointments/{id}` already broadcasting location updates from the detailer's mobile app. Plan 23 (auth hardening) is a higher priority.
- **Surge pricing display** — `days` array in `cdashData` has `state: "surge"` for some days. Pricing isn't currently surged in the codebase; this is a future product decision.
- **In-app notifications inbox** (`notifs` in cdashData) — Plan 21 §4/§5 covers notification *preferences*, not the inbox. The inbox would need a `user_notifications` table separate from `device_tokens`. Deferred.

### 10.5 Implementation Order

| Step | Endpoint(s) | Status |
|---|---|---|
| **A** | `POST /appointments/{id}/cancel` | ✅ **Done** — commit `70c31f8`. 8 tests pass. Reuses `AppointmentService.transition_status`; refund preview mirrors the FSM service's own branch logic. |
| **B** | `GET /customers/me/dashboard` | ⏳ Pending. Aggregate of existing data (appointments + favorites + vehicles). Subscriptions and recommendations fields stay empty arrays until T2/T3 land. |
| **C** | `GET /appointments/{id}/timeline` | ⏳ Pending. Reuses audit_logs; unlocks the Track view. |
| **D** | `GET /api/v1/users/me/notification-preferences` + `PUT` | ⏳ Pending. §4/§5 of original Plan 21. New small table `notification_preferences (user_id PK, push JSONB, email JSONB, sms JSONB)`. |
| **E** | `GET /customers/me/rewards` (basic) | ⏳ Pending. Returns tier + points + perks. Without `rewards_ledger` yet, points are a placeholder until T1 lands. |
| **F+** | T1/T2/T3 tables + their endpoints | ⏳ Pending. Full feature parity with the design. |

Step A landed in commit `70c31f8`; steps B onwards remain to be implemented.

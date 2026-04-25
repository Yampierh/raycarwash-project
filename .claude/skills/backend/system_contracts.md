---
name: system-contracts
description: SYSTEM CONTRACT DEFINITIONS — Defines all cross-domain lifecycles, state transitions, and inter-domain contracts. Every domain skill MUST implement against these contracts. Load after architecture_orchestrator.
depends_on:
  - architecture_orchestrator
preconditions:
  - architecture_orchestrator loaded
  - Domain models understood
outputs:
  - Appointment lifecycle state machine
  - Payment lifecycle
  - Request lifecycle
  - Worker lifecycle
  - Cross-domain contracts
conflicts:
  - Never violates lifecycle state transitions
  - Never modifies financial fields post-creation
execution_priority: 1
---

# System Contracts

**Skill Priority: 1**  
**Applies to:** All domain implementations, cross-domain coordination

## Overview

This skill defines the **canonical state machines and contracts** that every domain skill must implement against. These are the system-wide invariants — violations cause production incidents.

## Lifecycle Taxonomy

```
4 System Lifecycles:
  1. Request Lifecycle     — HTTP request → response
  2. Appointment Lifecycle — Booking → Completion/Cancel
  3. Payment Lifecycle    — Intent → Capture/Refund
  4. Worker Lifecycle     — Start → Run → Shutdown

2 Cross-Domain Contracts:
  5. Matching Contract    — Client → Detailer assignment
  6. Realtime Contract    — Worker → Client push
```

---

## Contract 1: Request Lifecycle

### Flow

```
Client ──HTTP──→ Router ──validate──→ Service ──transact──→ Repository
                │                         │
                │                    ┌────┴─────┐
                │                    ▼           ▼
                │              Audit Log    Realtime Event
                │                    │           │
                │               ┌────┴─────────┴────┐
                │               ▼                    ▼
                │          WebSocket ──────────── Worker
                │               │                    │
                └──────Response◄────────────────────┘
```

### Contract Rules

| Phase | Rule | Who Enforces |
|-------|------|-------------|
| Entry | JWT validated | Router (`get_current_user`) |
| Validation | Schema validated | Pydantic |
| Business | State machine checked | Service |
| Transaction | Atomic commit | Service (`db.begin()`) |
| Side Effect | Audit log inside transaction | Service |
| Response | Schema response | Router |
| Push | WebSocket event after commit | Worker |

### States

```
PENDING_VALIDATION
  ↓ (schema pass)
PENDING_AUTH
  ↓ (token valid)
PENDING_BUSINESS
  ↓ (state machine pass)
COMMITTED
  ↓ (response sent)
PUSHED
  ↓ (WS event sent)
DONE
```

---

## Contract 2: Appointment Lifecycle

### State Machine (Canonical Source)

**Source of truth:** `domains/appointments/models.py` → `VALID_TRANSITIONS`

```python
VALID_TRANSITIONS: dict[AppointmentStatus, dict[AppointmentStatus, frozenset[str]]] = {
    PENDING: {
        CONFIRMED:             {"detailer", "admin"},
        CANCELLED_BY_CLIENT:   {"client",   "admin"},
        CANCELLED_BY_DETAILER: {"detailer", "admin"},
    },
    CONFIRMED: {
        ARRIVED:               {"detailer", "admin"},
        IN_PROGRESS:           {"detailer", "admin"},
        CANCELLED_BY_CLIENT:   {"client",   "admin"},
        CANCELLED_BY_DETAILER: {"detailer", "admin"},
    },
    ARRIVED: {
        IN_PROGRESS:           {"detailer", "admin"},
        CANCELLED_BY_CLIENT:   {"client",   "admin"},
        CANCELLED_BY_DETAILER: {"detailer", "admin"},
    },
    IN_PROGRESS: {
        COMPLETED:             {"detailer", "admin"},
        NO_SHOW:              {"detailer", "admin"},
    },
    # Terminal states — no further transitions
    COMPLETED:              {},
    CANCELLED_BY_CLIENT:    {},
    CANCELLED_BY_DETAILER:  {},
    NO_SHOW:               {},
}
```

### Appointment Lifecycle Events

| Event | Trigger | Side Effect |
|-------|---------|------------|
| `APPOINTMENT_CREATED` | Router → Service | Audit + WS push |
| `APPOINTMENT_CONFIRMED` | Detailer accepts | Audit + WS push |
| `APPOINTMENT_STATUS_CHANGED` | Any transition | Audit + WS push + (if COMPLETED) payment capture |
| `APPOINTMENT_CANCELLED` | Client/Detailer | Audit + WS push + refund if eligible |
| `PAYMENT_CAPTURED` | Stripe webhook | Audit + ledger entry |
| `REFUND_ISSUED` | Cancellation | Audit + ledger entry |

### Immutability Contract

```
┌─────────────────────────────────────────────────────────────┐
│ IMMUTABLE after creation:                                   │
│   estimated_price  ← Never modified                        │
│   created_at      ← Never modified                        │
│   client_id       ← Never changed                        │
│   service_id      ← Never changed                        │
├─────────────────────────────────────────────────────────────┤
│ MUTABLE once only:                                          │
│   actual_price    ← Set ONLY when status → COMPLETED         │
│   arrived_at     ← Set when status → ARRIVED              │
│   started_at     ← Set when status → IN_PROGRESS          │
│   completed_at  ← Set when status → COMPLETED            │
└─────────────────────────────────────────────────────────────┘
```

### Cancellation Refund Contract

| Hours before appt | Refund |
|-------------------|--------|
| ≥ 24h | 100% of `estimated_price` |
| 2–24h | 50% of `estimated_price` |
| < 2h | 0% |

---

## Contract 3: Payment Lifecycle

### Flow (Two-Stage)

```
Phase 1: AUTHORIZATION
  Client ──POST /payments/create-intent──→ API
    │
    │ Stripe PaymentIntent created
    │ amount = estimated_price (cents)
    │ status = requires_payment_method
    │
    ▼
  Ledger Entry: AUTHORIZATION (amount = estimated_price)

Phase 2: CAPTURE
  Stripe ──POST /webhooks/stripe───────────�� Webhook handler
    │
    │ payment_intent.succeeded event
    │
    ▼
  Appointment status → COMPLETED
    │
    │ actual_price set from event.amount
    │
    ▼
  Ledger Entry: CAPTURE (amount = actual_price)

Phase 3: PAYOUT (async, separate process)
  Ledger Entry: PAYOUT (amount = net after commission)
  Ledger Entry: CHARGE_COMMISSION
```

### Ledger Contract (Append-Only)

```python
class LedgerContract:
    APPEND_ONLY = True          # No UPDATE, no DELETE
    ENTRY_TYPES = [
        "AUTHORIZATION",
        "CAPTURE",
        "REFUND",
        "PAYOUT",
        "CHARGE_COMMISSION",
    ]
    AMOUNT_SIGN:                # Always positive integers
        AUTHORIZATION = +
        CAPTURE = +
        REFUND = -
        PAYOUT = -
        CHARGE_COMMISSION = +  # Commission is positive from platform perspective
    METADATA_REQUIRED_ON = ["REFUND", "PAYOUT"]
```

### Stripe Webhook Contract

```python
class StripeWebhookContract:
    SIGNATURE_VERIFIED = True    # Always verify
    IDEMPOTENT = True          # processed_webhooks table
    HANDLED_EVENTS = [
        "payment_intent.succeeded",
        "payment_intent.payment_failed",
        "charge.refunded",
    ]
    IGNORED_EVENTS = []        # All others logged and acknowledged
```

---

## Contract 4: Worker Lifecycle

### Worker States

```
STOPPED ──start──→ STARTING ──init──→ RUNNING
   ▲                              │
   │                              ▼
   │                          CANCELLED ←──cancel──┐
   │                                                  │
   └──────────────────ERROR◄─────────────────────────┘
```

### Worker Contract Rules

| Rule | Specification |
|------|--------------|
| Startup | `asyncio.create_task(worker(app.state))` in lifespan |
| Shutdown | `task.cancel()` + `await task` in lifespan |
| Error handling | Log + backoff, never re-raise |
| Heartbeat | Log INFO every N intervals |
| Config | All intervals from `settings`, never hardcoded |
| Redis pub/sub | For cross-worker and multi-instance communication |

### Worker Types and Intervals

| Worker | Trigger | Interval |
|--------|---------|----------|
| `location_worker` | GPS push | `LOCATION_POLL_INTERVAL` |
| `assignment_worker` | Redis event | Event-driven |
| `ledger_seal_worker` | Daily | Midnight trigger |
| `token_cleanup_worker` | TTL | Hourly |

---

## Contract 5: Matching Contract (Client → Detailer)

### Assignment Flow

```
1. Client searches detailers
     → GET /api/v1/matching?service_id=&lat=&lng=&date=
     → Returns ranked detailers + available slots

2. Client selects detailer + time
     → POST /api/v1/appointments (status = PENDING)

3. Assignment offer sent
     → Worker emits "assignment_offered" event
     → Detailer has ASSIGNMENT_TIMEOUT_SECONDS to respond

4. Detailer accepts/declines/times out
     → Worker processes response
     → Status → CONFIRMED or back to SEARCHING

5. Assignment confirmed
     → Both client and detailer receive WS notification
     → Appointment status → CONFIRMED
```

### Matching Sort Order

| Scenario | Sort Priority |
|----------|-------------|
| ASAP (no `date`) | Distance ASC, Rating DESC |
| With `date` | Rating DESC, Distance ASC |

---

## Contract 6: Realtime Contract (Worker → Client)

### WebSocket Room Architecture

```
Room ID pattern: appt:{appointment_id}
Roles in room:  client, detailer
Events emitted: status_update, location_update, eta_update, assignment_event
```

### Event Schema Contract

```python
class WSMessageContract:
    REQUIRED_FIELDS = ["type", "data", "timestamp"]
    TYPE_VALUES = [
        "status_update",
        "location_update",
        "eta_update",
        "assignment_event",
        "error",
    ]
    data: dict  # Event-specific payload
    timestamp: ISO8601 string
```

### Cross-Instance Contract

```python
class RealtimeContract:
    SINGLE_INSTANCE = Redis pub/sub  # Workers publish to Redis
    MULTI_INSTANCE = True            # Redis channel subscription
    FALLBACK = "in-memory if Redis unavailable (dev mode)"
```

---

## Inter-Domain Contract Violations

These are system-level bugs — never acceptable:

| Violation | Severity |
|-----------|---------|
| `estimated_price` modified after creation | CRITICAL — Financial corruption |
| Appointment transitioned without role check | CRITICAL — Authorization bypass |
| Ledger entry modified or deleted | CRITICAL — Audit failure |
| Webhook processed without idempotency | HIGH — Duplicate charge |
| Worker running without Redis pub/sub | MEDIUM — Breaks multi-instance |
| WS event sent before DB commit | HIGH — Inconsistent state |
| Cross-domain service import | MEDIUM — Coupling violation |

---

## Success Criteria

- All 4 lifecycles have documented state machines
- Immutability contract enforced by `system_contracts.md`
- Cross-domain contracts use events, not service imports
- Ledger append-only enforced
- Webhook idempotency enforced
- Worker lifecycle managed via `app.state` + lifespan
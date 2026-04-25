---
name: backend-stripe-integration
description: Stripe payments and webhook integration patterns. Use when working on payment intents, webhooks, refunds, or ledger entries. Covers idempotency, signature verification, and the dual-write pattern.
depends_on:
  - architecture_orchestrator
  - system_contracts
  - failure_modes
  - state_machine
preconditions:
  - Webhook signature verified first
  - processed_webhooks idempotency check before processing
  - Amounts always in integer cents
outputs:
  - PaymentIntent creation
  - Webhook handler
  - Ledger entry
  - Audit log
conflicts:
  - Ledger never updated or deleted (append-only)
  - Amount never as float
  - Webhook never processed without idempotency
execution_priority: 2
---

# Stripe Integration

**Priority: CRITICAL**  
**Applies to:** Payment creation, webhook handling, refunds, ledger entries

## Two-Stage Payment Flow

```
1. Client  → POST /payments/create-intent      → PaymentIntent created
2. Stripe  → POST /webhooks/stripe (capture)  → Ledger entry written
```

## Payment Intent Creation

```python
# domains/payments/service.py
import stripe
from app.core.config import get_settings

settings = get_settings()
stripe.api_key = settings.STRIPE_SECRET_KEY


async def create_payment_intent(
    appointment: Appointment,
    return_url: str,
) -> dict:
    intent = stripe.PaymentIntent.create(
        amount=appointment.estimated_price,  # cents
        currency="usd",
        metadata={
            "appointment_id": str(appointment.id),
            "client_id": str(appointment.client_id),
        },
        return_url=return_url,
        automatic_payment_methods={"enabled": True},
    )
    return {
        "client_secret": intent.client_secret,
        "payment_intent_id": intent.id,
    }
```

## Webhook Handler

### Signature Verification

```python
# domains/payments/router.py
from stripe import Webhook.construct_event
from app.core.config import get_settings


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")

    # Check idempotency
    processed_repo = ProcessedWebhookRepository(db)
    if await processed_repo.exists(event.id):
        return JSONResponse({"status": "already_processed"})

    # Handle event
    await handle_stripe_event(db, event)

    # Mark as processed
    await processed_repo.mark_processed(event.id, event.type)
    await db.commit()

    return JSONResponse({"status": "ok"})
```

## Event Handling

```python
async def handle_stripe_event(db: AsyncSession, event: StripeEvent) -> None:
    match event.type:
        case "payment_intent.succeeded":
            await _handle_capture(db, event)
        case "payment_intent.payment_failed":
            await _handle_failure(db, event)
        case "charge.refunded":
            await _handle_refund(db, event)
        case _:
            pass  # Ignore unhandled events


async def _handle_capture(db: AsyncSession, event: StripeEvent) -> None:
    appointment_id = UUID(event.data.object.metadata["appointment_id"])
    appt_repo = AppointmentRepository(db)
    appt = await appt_repo.get_by_id(appointment_id)
    if not appt:
        return

    # 1. Update appointment status
    appt.status = AppointmentStatus.COMPLETED
    appt.actual_price = event.data.object.amount  # cents
    appt.completed_at = datetime.now(timezone.utc)

    # 2. Write ledger entry
    from domains.payments.models import PaymentLedger, EntryType
    ledger = PaymentLedger(
        appointment_id=appointment_id,
        entry_type=EntryType.CAPTURE,
        amount_cents=event.data.object.amount,
        stripe_payment_intent_id=event.data.object.id,
        currency=event.data.object.currency,
    )
    db.add(ledger)

    # 3. Audit log
    await AuditRepository(db).log(
        action=AuditAction.PAYMENT_CAPTURED,
        entity_type="appointment",
        entity_id=str(appointment_id),
        metadata={"amount_cents": event.data.object.amount},
    )
```

## Ledger Entry Rules

The `payment_ledger` table is **append-only**. No updates, no deletes.

```python
# Valid entry types
class EntryType(str, Enum):
    AUTHORIZATION = "AUTHORIZATION"
    CAPTURE = "CAPTURE"
    REFUND = "REFUND"
    PAYOUT = "PAYOUT"
    CHARGE_COMMISSION = "CHARGE_COMMISSION"
```

- `amount_cents` must always be **positive integers**
- `appointment_id` is the FK — never null
- Idempotency via `processed_webhooks` table

## Refund Flow

```python
async def process_refund(
    appointment: Appointment,
    refund_amount: int,
    reason: str,
) -> dict:
    # 1. Create Stripe refund
    refund = stripe.Refund.create(
        payment_intent=appointment.stripe_payment_intent_id,
        amount=refund_amount,
        reason="requested_by_customer",
    )

    # 2. Write ledger entry
    ledger = PaymentLedger(
        appointment_id=appointment.id,
        entry_type=EntryType.REFUND,
        amount_cents=refund_amount,
        stripe_payment_intent_id=refund.payment_intent,
        metadata={"reason": reason},
    )
    db.add(ledger)

    # 3. Audit log
    await AuditRepository(db).log(
        action=AuditAction.REFUND_ISSUED,
        entity_type="appointment",
        entity_id=str(appointment.id),
        metadata={"amount_cents": refund_amount, "reason": reason},
    )
```

## Anti-Patterns

```python
# ❌ BAD: No webhook signature verification
async def webhook(request: Request):
    data = await request.json()
    # Anyone can forge events

# ✅ GOOD: Verified signature
event = Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)

# ❌ BAD: No idempotency check
async def webhook(request: Request):
    await process_event(request)
    # Duplicate processing on retry

# ✅ GOOD: Idempotency via processed_webhooks
if await processed_repo.exists(event.id):
    return JSONResponse({"status": "already_processed"})

# ❌ BAD: Updating a ledger entry
PaymentLedger.amount_cents = new_amount  # Append-only!

# ✅ GOOD: Add a new entry for corrections
new_ledger = PaymentLedger(
    appointment_id=appointment_id,
    entry_type=EntryType.REFUND,
    amount_cents=correction,
)

# ❌ BAD: Floating point for amounts
amount=estimated_price * 1.05  # float precision errors

# ✅ GOOD: Integer cents
amount_cents=int(estimated_price * Decimal("1.05"))
```

## Success Criteria

- Webhook signature verified with `Webhook.construct_event`
- `processed_webhooks` table prevents duplicate processing
- All amounts in **cents** (integers)
- Ledger is append-only — no updates/deletes
- Both payment and refund create ledger entries
- Audit log on every payment event
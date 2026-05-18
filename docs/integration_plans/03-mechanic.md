# 03 — Basic Mechanic Services

## 1. Overview

**Target Profile:** `ProviderType.MECHANIC`  
**Pricing Model:** Fixed price per service (not by vehicle size)  
**Status:** New vertical — full implementation required.

### Core Services

| Service | Description | Est. Price |
|---|---|---|
| Oil Change | Oil drain + filter replacement + fluid top-off | $49.99 |
| Brake Service | Brake inspection + pad replacement (per axle) | $89.99 |
| Tire Repair | Flat tire repair (patch/plug) | $19.99 |
| Tire Rotation | Rotate all 4 tires + pressure check | $29.99 |
| Tire Replacement | Mount + balance (per tire, client provides tire) | $19.99 |
| Battery Replacement | Battery test + replacement (client provides battery) | $19.99 |

## 2. Service Catalog

### ServiceCategory Enum

Add new values to `ServiceCategory`:

```python
class ServiceCategory(str, enum.Enum):
    # Existing detailing...
    
    # New mechanic
    OIL_CHANGE = "oil_change"
    BRAKE_SERVICE = "brake_service"
    TIRE_REPAIR = "tire_repair"
    TIRE_ROTATION = "tire_rotation"
    TIRE_REPLACEMENT = "tire_replacement"
    BATTERY_REPLACEMENT = "battery_replacement"
```

### Service Pricing Model

Mechanic services use `ServicePriceType.FIXED_PRICE`:

```python
class Service(Base):
    # Existing fields...
    price_type: ServicePriceType  # FIXED_PRICE
    fixed_price_cents: int | None  # e.g., 4999 for $49.99
```

Vehicle size is not a pricing factor for basic mechanic services (an oil change costs the same for a sedan and an SUV).

### Addons

| Addon | Price |
|---|---|
| Synthetic oil upgrade | +$20.00 |
| Premium brake pads (ceramic) | +$40.00 |
| Tire disposal fee (per tire) | $5.00 |
| Shop supplies fee | $10.00 |
| Mobile call-out fee (outside radius) | $25.00 |

## 3. Mechanic Profile

A Mechanic (`ProviderType.MECHANIC`) manages:

| Feature | Implementation |
|---|---|
| Services offered | Via `ProviderService` table (enable/disable + custom price) |
| Custom pricing | Override `fixed_price_cents` per service |
| Availability | `is_active` + `working_hours` (per-profile) |
| Service radius | Miles willing to travel |
| Specialties | Oil, brakes, tires, diagnostics via `Specialty` |

### Equipment Notes

The provider is expected to bring their own tools and parts. No legal verification for now.

| Service | Minimum Tools |
|---|---|
| Oil Change | Jack + stands, drain pan, wrenches, funnel, gloves |
| Brake Service | Jack + stands, lug wrench, C-clamp, torque wrench |
| Tire Service | Jack, lug wrench, tire iron, patch kit, air compressor |
| Battery | Multimeter, basic wrench set |

## 4. Combos

### Fixed Combos

| Combo | Included | Discount |
|---|---|---|
| **Tune-Up Basic** | Oil Change + Tire Rotation | 15% |
| **Safety Check** | Brake Inspection + Tire Rotation + Fluid Top-Off | 20% |
| **Full Service** | Oil Change + Brake Service + Tire Rotation | 25% |

Custom combos use the shared system defined in `02-detailing.md`.

### Parts Handling

For this initial version: **provider brings parts, included in the fixed price.**

Recording parts used on appointment completion is optional but recommended:

```python
class AppointmentPart(Base):
    __tablename__ = "appointment_parts"
    id: UUID
    appointment_id: UUID → FK appointments.id
    name: str  # e.g., "Mobil 1 5W-30"
    quantity: int
    unit_price_cents: int
```

This enables future features: parts billing, warranty tracking, inventory management.

## 5. Appointment Flow

Same FSM as detailing:

```
PENDING → CONFIRMED → ARRIVED → IN_PROGRESS → COMPLETED
```

**Differences from detailing:**

| Aspect | Detailing | Mechanic |
|---|---|---|
| Duration | By vehicle size | Fixed duration per service |
| Pricing | By vehicle size | Fixed price |
| Parts | Consumables only | Parts + consumables |
| Vehicle state | Clean/dirty | Diagnostics needed |

### Appointment Notes

Mechanic appointments may require structured notes:

```json
{
  "oil_type_used": "Mobil 1 5W-30",
  "oil_filter_brand": "Fram",
  "brake_pad_condition_before": "3mm",
  "brake_pad_condition_after": "12mm",
  "tire_pressure_before": {"FL": 28, "FR": 27, "RL": 29, "RR": 28},
  "tire_pressure_after": {"FL": 32, "FR": 32, "RL": 32, "RR": 32},
  "notes": "Customer reported squeaking. Resolved with pad replacement."
}
```

Implementation: extend `Appointment` with `service_notes: dict | None` (JSONB).

## 6. API Changes

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/services?type=mechanic` | Filter services by provider type |
| `GET` | `/api/v1/providers?type=mechanic` | List mechanic providers |
| `POST` | `/api/v1/providers/profiles` | Create mechanic profile (type=`MECHANIC`) |
| `POST` | `/api/v1/appointments` | Book mechanic service (accepts `service_notes`) |
| `PATCH` | `/api/v1/appointments/{id}/parts` | Record parts used on completion |

## 7. Prerequisites

> :warning: **Hard prerequisite**: [`08-hardening.md`](../plans/08-hardening.md) Phases 0-4 must be complete before implementing this plan.

Un vertical completamente nuevo (mecanico) requiere la base mas solida posible. Todos los fixes de hardening deben estar aplicados: infraestructura, service layer, DB migrations, y tests.

| Prerrequisito | Plan | Estatus |
|--------------|------|---------|
| Backend hardening Phases 0-4 | `08-hardening.md` | Draft |
| Multi-Profile System | `00-user.md` -> `01-profiles.md` | Planning |
| Appointment FSM tests completos | H10 en hardening Phase 4 | Draft |
| Combos system | `02-detailing.md` | Planning |

## 8. Implementation Order

| Step | Description | Depends On |
|---|---|---|
| 1 | User model + Multi-Profile System | `00-user.md` -> `01-profiles.md` |
| 2 | Add mechanic categories + services to seed data | Step 1 |
| 3 | Implement `FIXED_PRICE` pricing model | Step 2 |
| 4 | Add `service_notes` field to Appointment model | — |
| 5 | Build mechanic profile UI (web + mobile) | Step 1 |
| 6 | Matching with `provider_type` filter | Step 1 |
| 7 | Combos (shared system from detailing) | `02-detailing.md` Step 2 |
| 8 | Appointment parts recording | Optional — Step 4 |

## 9. Deferred Features

These are identified for future phases, not implemented now:

| Feature | Reason |
|---|---|
| Legal/licensing/insurance verification | Out of scope per product decision |
| OBD-II diagnostic report upload | Requires hardware integration |
| Parts inventory management | Complex — requires supplier integration |
| Parts billing (separate line item) | Simplifies initial launch |
| Warranty tracking | Legal dependency |
| ASE certification badges | Legal/trust — deferred |

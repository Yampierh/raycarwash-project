# 02 — Detailing Services

## 1. Overview

**Target Profile:** `ProviderType.DETAILER`  
**Pricing Model:** By vehicle size (small, medium, large, XL)  
**Status:** Existing vertical — this plan documents, extends, and standardizes the offering.

## 2. Service Categories

| Enum | Description |
|---|---|
| `basic_wash` | Exterior wash + dry + windows + tire shine |
| `interior_detail` | Vacuum, wipe-down, shampoo carpets, leather conditioning |
| `full_detail` | Basic wash + interior detail (comprehensive) |
| `ceramic_coating` | Ceramic/protective coating (multi-year) |
| `paint_correction` | Paint correction, polishing, swirl removal |

## 3. Service Pricing

Each service has prices and durations per vehicle size. This model stays unchanged:

| Field | Example (Full Detail) |
|---|---|
| `price_small` | 12000 ($120.00) |
| `price_medium` | 15000 ($150.00) |
| `price_large` | 19000 ($190.00) |
| `price_xl` | 25000 ($250.00) |
| `duration_small_minutes` | 120 |
| `duration_medium_minutes` | 150 |
| `duration_large_minutes` | 180 |
| `duration_xl_minutes` | 240 |

## 4. Addons

| Addon | Price | Duration |
|---|---|---|
| Pet hair removal | +$25.00 | +20 min |
| Clay bar treatment | +$40.00 | +30 min |
| Headlight restoration | +$35.00 | +25 min |
| Odor removal (ozone) | +$30.00 | +20 min |
| Engine bay cleaning | +$45.00 | +30 min |
| Fabric protection | +$50.00 | +15 min |
| Paint sealant | +$60.00 | +20 min |

## 5. Combos

Combos are package deals combining multiple services or services + addons at a discount.

### Fixed Combos (Pre-defined by platform)

| Combo | Included | Discount | Duration |
|---|---|---|---|
| **Express Wash** | Basic Wash + Tire Shine | 0% | base + 5min |
| **Weekend Detail** | Basic Wash + Interior Detail | 10% | sum |
| **Full Makeover** | Full Detail + Clay Bar + Headlight Restore | 15% | sum + 30min |
| **Showroom Ready** | Full Detail + Paint Correction + Ceramic Coating | 20% | sum |

### Custom Combos (User-defined)

Any client can select multiple services and addons. A dynamic discount applies (e.g., 10% when booking 2+ items, 15% for 3+).

### Backend Model

```python
class Combo(Base):
    __tablename__ = "combos"
    id: UUID
    name: str
    description: str | None
    is_custom: bool  # False = fixed, True = user-customized
    discount_percent: int
    is_active: bool

class ComboItem(Base):
    __tablename__ = "combo_items"
    id: UUID
    combo_id: UUID  → FK combos.id
    service_id: UUID | None  → FK services.id (nullable — could be addon)
    addon_id: UUID | None    → FK addons.id
    quantity: int = 1
```

### Pricing Logic

```python
combo_total = sum(all_items_full_price) * (1 - discount_percent / 100)
```

## 6. Appointment Flow

Existing FSM applies without changes:

```
PENDING → CONFIRMED → ARRIVED → IN_PROGRESS → COMPLETED
```

Appointment model additions:

| Field | Type | Purpose |
|---|---|---|
| `combo_id` | UUID? | Links to combo if booked as package |
| `provider_id` | UUID | Renamed from `detailer_id` |

## 7. Provider Features

Each Detailer profile can configure:

| Feature | Implementation |
|---|---|
| Services offered | Via `ProviderService` table (enable/disable + custom price) |
| Custom pricing | Override `base_price_cents` per service |
| Specialties | Via `Specialty` + `ProviderSpecialty` (e.g., "ceramic coating expert") |
| Availability | `is_active` + `working_hours` |
| Service radius | Miles willing to travel |
| Portfolio | Gallery of before/after photos (future) |
| Business name | `display_name` on profile |

## 8. API Extensions

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/combos` | List fixed combos |
| `POST` | `/api/v1/combos/custom` | Create a custom combo |
| `GET` | `/api/v1/combos/{id}/price` | Calculate combo price |
| `POST` | `/api/v1/appointments` | Accept `combo_id` param |

## 8. Prerequisites

> :warning: **Hard prerequisite**: [`08-hardening.md`](../plans/08-hardening.md) Phases 0 + 4 must be complete before implementing this plan.

Combos requieren `AppointmentService` sin SQL inline y tests de FSM completos (11 transiciones faltantes). Sin tests de cancellacion/double-booking, los combos multiplican el riesgo financiero.

| Prerrequisito | Plan | Estatus |
|--------------|------|---------|
| Backend hardening Phases 0 + 4 | `08-hardening.md` | Draft |
| AppointmentService limpio | C1 en hardening Phase 2 | Draft |
| FSM + refund + double-booking tests | C5, C6, H10 en hardening Phase 4 | Draft |
| Multi-Profile System | `00-user.md` -> `01-profiles.md` | Planning |

## 9. Implementation Order

| Step | Description | Depends On |
|---|---|---|
| 1 | User model + Multi-Profile System | `00-user.md` -> `01-profiles.md` |
| 2 | Combo model + seed data | — |
| 3 | Combo pricing API | Step 2 |
| 4 | Portfolio/gallery for detailers | Future phase |
| 5 | Enhanced booking UI with combos | Steps 2-3 |

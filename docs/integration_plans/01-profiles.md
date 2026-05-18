# 01 — Multi-Profile System

## 1. Overview

**Goal:** Allow a single User to hold multiple provider profiles (Detailer + Mechanic) side by side. Each profile is independent with its own availability, specialties, services, and pricing.

**Key Design (from `00-user.md`):**
- `User` = shared identity (name, email, phone, avatar, language, timezone)
- `Address` = separate model for clients only (providers use GPS)
- `ProviderProfile` = role-specific data (type, bio, availability, pricing)

## 2. Data Model Changes

### 2.1 User → ProviderProfile: 1:N

Current relationship (1:1):

```python
# User currently has only ONE provider slot
provider_profile: Mapped[ProviderProfile | None]
```

Proposed (1:N):

```python
# User can have multiple provider profiles
provider_profiles: Mapped[list[ProviderProfile]] = relationship(
    "ProviderProfile", back_populates="user",
    lazy="selectin",
)
```

### 2.2 ProviderProfile Field Changes

| Field | Change | Reason |
|---|---|---|
| `user_id` | **Remove unique constraint** | One user = multiple profiles |
| `provider_type` | **New enum**: `DETAILER`, `MECHANIC` | Identifies the vertical |
| `is_active` | **Rename** from `is_accepting_bookings` | Clearer intent |
| `display_name` | **Keep per-profile** | "John's Detailing" vs "John's Mobile Mechanic" |
| `bio` | **Keep per-profile** | Different pitch per service type |

**New unique constraint:** `(user_id, provider_type)` — prevents duplicate profiles of same type.

**New index:** `(provider_type, is_active)` for fast listing.

### 2.3 ProviderServiceCategory (Many-to-Many)

Convert `service_category_id` (single FK) to many-to-many:

```python
class ProviderServiceCategory(Base):
    __tablename__ = "provider_service_categories"
    provider_id: UUID  → FK provider_profiles.id
    category_id: UUID  → FK service_categories.id
```

This lets a Detailer profile offer `basic_wash`, `interior_detail`, and `full_detail` simultaneously — no artificial single-category limit.

### 2.4 Rename DetailerService → ProviderService

| Current | New |
|---|---|
| Table `detailer_services` | `provider_services` |
| Column `detailer_id` | `provider_id` |

Now service listings are provider-type agnostic. A Mechanic profile uses the same table to list oil changes and brake services.

## 3. Shared-vs-Specific Resolution

When an API returns a provider profile, fields are resolved in cascade order:

```
1. Does ProviderProfile have a value? → use it
2. No? Does User have a value? → use it
3. No → use default / null
```

### Field Source Table

| API Field | Source |
|---|---|
| `id` | ProviderProfile |
| `provider_type` | ProviderProfile |
| `display_name` | ProviderProfile ?? User.full_name |
| `bio` | ProviderProfile ?? "" |
| `is_active` | ProviderProfile |
| `working_hours` | ProviderProfile |
| `service_radius_miles` | ProviderProfile |
| `full_name` | User (always) |
| `email` | User (always) |
| `phone` | User (always) |
| `avatar_url` | User (always) |
| `language` | User (always) |
| `timezone` | User (always) |

## 4. Availability

Each profile has independent availability:

```python
class ProviderProfile(Base):
    is_active: bool = True          # Master toggle for this profile
    working_hours: dict             # Per-profile schedule (JSONB)
    service_radius_miles: int       # Per-profile radius
```

A user with both Detailer and Mechanic profiles can:

- Pause Detailer (`is_active = false`) while keeping Mechanic active
- Set different working hours (weekdays for mechanic, weekends for detailing)
- Set different service areas (25mi radius for detailing, 15mi for mechanic)

## 5. Profile Creation & Management

### Creation Flow

```text
User registers → role "client" assigned by default
    ↓
User onboards as provider
    ↓
POST /api/v1/providers/profiles  { provider_type: "detailer" }
    → creates ProviderProfile (type=DETAILER)
    → assigns role "detailer" if not already held
    ↓
POST /api/v1/providers/profiles  { provider_type: "mechanic" }
    → creates second ProviderProfile (type=MECHANIC)
    → assigns role "mechanic" if not already held
```

### API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/providers/profiles` | Create new profile of given type |
| `GET` | `/api/v1/providers/profiles` | List my profiles |
| `PATCH` | `/api/v1/providers/profiles/{id}` | Update a specific profile |
| `DELETE` | `/api/v1/providers/profiles/{id}` | Soft-delete a profile |
| `GET` | `/api/v1/providers?type=mechanic` | Public listing filtered by type |

### Frontend Profile Switcher

The provider dashboard should allow switching between profiles:

```
[ User Avatar ]  Juan Pérez
                  ▼
    ┌──────────────────────┐
    │ 🔧 Mechanic (active) │ ← green dot
    │ 🧼 Detailer (paused) │ ← yellow dot
    │ ⚙️ Manage profiles   │
    └──────────────────────┘
```

## 6. RBAC Changes

| Role | Assigned | Permissions |
|---|---|---|
| `admin` | Seed only | Full access |
| `client` | On registration | Book, vehicles, reviews |
| `detailer` | On detailer profile creation | Detailing services + profile mgmt |
| `mechanic` | On mechanic profile creation | Mechanic services + profile mgmt |

One user can hold `[client, detailer]`, `[client, mechanic]`, or `[client, detailer, mechanic]` simultaneously.

## 7. Migration Plan

| Step | Description | Depends On |
|---|---|---|
| 1 | Add `provider_type` column (default `DETAILER`) | — |
| 2 | Remove unique constraint on `provider_profiles.user_id` | Step 1 |
| 3 | Add composite unique `(user_id, provider_type)` | Step 1 |
| 4 | Update `User.is_provider()` to check both roles | — |
| 5 | Create `provider_service_categories` table, migrate data | — |
| 6 | Rename `detailer_services` → `provider_services` | — |
| 7 | Rename `is_accepting_bookings` → `is_active` | — |
| 8 | Update `User.provider_profile` → `User.provider_profiles` (list) | Steps 1-3 |

## 8. Prerequisites

> :warning: **Hard prerequisite**: [`08-hardening.md`](../plans/08-hardening.md) Phases 0-2 must be complete before implementing this plan.

El refactor `ProviderProfile` 1:1 -> 1:N requiere Service Layer estable (AdminService extraido, repos ausentes creados). Ademas, `User.is_provider()` debe actualizarse sobre un modelo `User` ya saneado por hardening.

| Prerrequisito | Plan | Estatus |
|--------------|------|---------|
| Backend hardening Phases 0-2 | `08-hardening.md` | Draft |
| Service Layer reorg | C1, C2, H5 en hardening | Draft |
| 00-user base | `00-user.md` | Planning |
| Envelope compliance | M1 en hardening Phase 1B | Draft |

## 9. Dependencies

| Plan | Depends On |
|---|---|
| `01-profiles.md` | `00-user.md` (User model shared fields) |
| `02-detailing.md` | `01-profiles.md` (detailer profile type) |
| `03-mechanic.md` | `01-profiles.md` (mechanic profile type) |

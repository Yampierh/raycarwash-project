# 00 — User Model (Shared Profile)

## 1. Overview

**Goal:** Define the `User` model as the universal shared profile for all roles (client, detailer, mechanic). Fields on `User` are available to everyone. Role-specific data lives in dedicated profiles (`ProviderProfile`).

**Principle:** `User` = what every person on the platform has. `ProviderProfile` = what a provider adds on top. `Address` = client location storage.

## 2. Current State

### User Model (`domains/users/models.py`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `email` | String(254) | unique, indexed |
| `full_name` | EncryptedType | PII, nullable |
| `phone_number` | EncryptedType | PII, nullable |
| `password_hash` | String(255) | Required |
| `is_active` | Boolean | Default true |
| `is_verified` | Boolean | Default false |
| `failed_login_attempts` | Integer | For lockout |
| `locked_until` | DateTime | Nullable |
| `onboarding_status` | String(30) | PENDING_PROFILE / PENDING_VERIFICATION / COMPLETED |
| `token_version` | Integer | Refresh rotation |
| `phone_hash` | String(64) | Unique, HMAC'd phone |
| `stripe_customer_id` | String(64) | Nullable |
| `last_step_up_at` | DateTime | DB fallback for step-up |
| `avatar_s3_key` | String(255) | Nullable |
| `cover_s3_key` | String(255) | Nullable |
| `pronouns` | String(20) | Nullable |
| `preferred_language` | String(10) | Default "en" |
| `preferred_timezone` | String(64) | Default "America/Indiana/Indianapolis" |
| `last_active_at` | DateTime | Nullable |
| `active_role` | String(20) | Nullable, for dual-role users |

### Current Provider Relationship

```python
# User → ProviderProfile is currently 1:1
provider_profile: Mapped[ProviderProfile | None]
```

This is the main limitation — one user can only have one provider profile today.

### Existing Methods

```python
def is_client(self) -> bool:     # has_role("client")
def is_provider(self) -> bool:   # has_role("detailer") — needs update
def is_detailer(self) -> bool:   # alias for is_provider
def has_role(self, name) -> bool:
def has_permission(self, name) -> bool:
```

Note: `is_provider()` checks for role name `"detailer"`. This must be updated to support both `detailer` and `mechanic` roles.

## 3. Proposed Changes

### 3.1 New Fields on User

| Field | Type | Required | Purpose |
|---|---|---|---|
| `zip_code` | String(10) | No | Quick onboarding hint for location-based matching. No full address needed at signup. |

No other new fields on `User`. Everything else goes to `ProviderProfile` or `Address`.

### 3.2 Address Model (New)

Address is a **separate model** on `user_addresses` table, not on `User`:

```python
class Address(TimestampMixin, Base):
    __tablename__ = "user_addresses"

    id: UUID, PK
    user_id: UUID, FK → users.id, not nullable, indexed
    label: str | None          # "Home", "Work", "Office"
    street: str                # "123 Main St"
    apt: str | None            # "Apt 4B"
    city: str                  # "Fort Wayne"
    state: str                 # "IN"
    zip_code: str              # "46802"
    lat: float | None          # Geocoded on save
    lng: float | None          # Geocoded on save
    is_primary: bool           # Default false. Only one primary per user
    is_deleted: bool           # Soft delete
```

**Relationships:**
- `User.addresses → [Address]` (one-to-many)
- `ClientProfile.default_address_id → Address.id` (already stubbed in code)

**Usage by role:**

| Role | Address behavior |
|---|---|
| Client | Optional at signup. Can add multiple (home, work). Picks one per booking. |
| Detailer | No address. Uses GPS + `service_radius_miles` for location. |
| Mechanic | Same as Detailer — GPS-based, no stored address needed. |

### 3.3 Shared-vs-Specific Resolution

When an API endpoint returns a provider profile, it resolves fields like this:

```python
# Pseudocode — resolution order:
response.display_name = profile.display_name or user.full_name
response.bio = profile.bio or ""
response.phone = user.phone_number  # Always from User
response.avatar_url = user.avatar_s3_key  # Always from User
response.email = user.email  # Always from User
response.address = None  # Providers don't have stored addresses
```

This means:

| Field | Source for Provider | Source for Client |
|---|---|---|
| `full_name` | User (always) | User |
| `display_name` | ProviderProfile ?? User.full_name | — |
| `bio` | ProviderProfile ?? "" | — |
| `phone` | User | User |
| `email` | User | User |
| `avatar` | User | User |
| `address` | GPS + radius (not stored) | Address model |
| `language` | User | User |
| `timezone` | User | User |

### 3.4 Update `is_provider()` Method

```python
# Current:
def is_provider(self) -> bool:
    return self.has_role("detailer")

# Proposed:
def is_provider(self) -> bool:
    return self.has_role("detailer") or self.has_role("mechanic")
```

### 3.5 RBAC (Role Changes)

The current roles `["admin", "detailer", "client"]` need one addition:

| Role | When assigned | Permissions |
|---|---|---|
| `admin` | Seed only | Full access |
| `client` | On registration (default) | Book services, manage vehicles, review |
| `detailer` | On onboarding (type=DETAILER) | Detailing services + profile management |
| `mechanic` | On onboarding (type=MECHANIC) | Mechanic services + profile management |

A user can hold `client + detailer`, `client + mechanic`, or `client + detailer + mechanic` simultaneously.

## 4. Prerequisites

> :warning: **Hard prerequisite**: [`08-hardening.md`](../plans/08-hardening.md) Phase 0 must be complete before implementing this plan.

Hardening Phase 0 resuelve: `pool_pre_ping`, RBAC `write:permissions`, `create_all` guard, Redis pool config. Sin estos cimientos, agregar `zip_code` al modelo `User` opera sobre una base fragil.

| Prerrequisito | Plan | Estatus |
|--------------|------|---------|
| Backend hardening | `08-hardening.md` Phase 0 | Draft |
| pool_pre_ping + create_all guard | C4, H1 en hardening | Draft |
| RBAC write:permissions fix | C3 en hardening | Draft |

## 5. Dependency

This plan (`00-user.md`) is a **prerequisite** for `01-profiles.md`. All other vertical plans (detailing, mechanic) depend on the multi-profile system defined here and in `01-profiles.md`.

```
00-user.md  ← you are here
  └── 01-profiles.md  (multi-profile system, depends on User model)
        ├── 02-detailing.md  (references profiles)
        └── 03-mechanic.md   (references profiles)
```

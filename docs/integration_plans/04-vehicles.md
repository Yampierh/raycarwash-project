# 04 — Vehicle Catalog + User Vehicles

## 1. Overview

**Goal:** Two-tier vehicle system — `vehicle` (catalog master pre-populated from NHTSA vPIC) and `user_vehicle` (user-owned vehicles). Menus query `vehicle` directly. VIN decode via NHTSA API with vPIC backup fallback.

**Principle:** `vehicle` = all year/make/model/series combos users might select. `user_vehicle` = a specific car someone owns (color, plate, VIN). NHTSA IDs prevent duplicates.

## 2. Current State

### `Vehicle` Model (`domains/vehicles/models.py`)

Single table mixing catalog + ownership:

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `owner_id` | UUID FK | Links to user |
| `vin` | String(17) | Nullable |
| `make` | String(60) | |
| `model` | String(60) | |
| `year` | Integer | |
| `series` | String(60) | Nullable — trim |
| `color` | String(40) | |
| `license_plate` | String(20) | |
| `body_class` | String(60) | Nullable — raw NHTSA name |
| `notes` | Text | Nullable |
| `is_deleted` | Bool | Soft delete |
| `deleted_at` | DateTime | |

Unique: `(owner_id, license_plate)`

### Current Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/vehicles` | Register vehicle |
| GET | `/api/v1/vehicles` | List my vehicles |
| GET | `/api/v1/vehicles/lookup/{vin}` | VIN decode via NHTSA API |
| PUT | `/api/v1/vehicles/{id}` | Update vehicle |
| DELETE | `/api/v1/vehicles/{id}` | Soft delete |

### Current VIN Decode

`infrastructure/nhtsa/client.py` calls `https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json` and maps `BodyClass` → `VehicleSize` via `map_body_to_size()`. No local cache.

### What Exists Outside the App

User maintains a **vPIC Lite 2026.04 dump** (97 tables, 76MB) in a separate PostgreSQL DB. Key tables:

| Table | Rows | Content |
|---|---|---|
| `vpic.defs_make` | 107 | Make definitions |
| `vpic.defs_model` | 2,145 | Model definitions with `includes` (series/trims) |
| `vpic.make` | ~12,216 | Makes |
| `vpic.model` | ~31,762 | Models |
| `vpic.make_model` | ~12k | Make-Model relation |
| `vpic.bodystyle` | ~60 | Body class lookups |
| `vpic.fuel_type` | ~20 | Fuel types |
| `vpic.drive_type` | ~10 | Drive types |
| `vpic.transmission` | ~30 | Transmission types |
| `vpic.engine_configuration` | ~30 | Engine configs (V6, I4, etc.) |
| `vpic.vehiclespecpattern` | 212,310 | Spec patterns including Series (1,694) + Trim (7,439) |
| `vpic.vehiclespecschema_year` | 12,815 | Year-schema links |

## 3. Proposed Changes

### 3.1 New Tables

#### `vehicle` — Catalog Master

Pre-populated from vPIC. Every row is a unique `(year, make, model, series)` combo.

| Column | Type | NHTSA Source | Notes |
|---|---|---|---|
| `id` | UUID PK | — | |
| `year` | int | `vehiclespecschema_year` | NOT NULL |
| `make` | varchar(60) | `defs_make.name` | |
| `model` | varchar(60) | `defs_model.def` | |
| `series` | varchar(200) | `defs_model.includes` (parsed) | trim/version |
| `body_class` | varchar(250) | `vehiclespecpattern` or API | raw NHTSA body style name |
| `vehicle_type` | varchar(20) | `vpic.vehicletype` or API | abbreviated — pricing tier |
| `fuel_type` | varchar(100) | `vehiclespecpattern` or API | |
| `drive_type` | varchar(100) | `vehiclespecpattern` or API | |
| `transmission` | varchar(100) | `vehiclespecpattern` or API | |
| `engine_config` | varchar(100) | `vehiclespecpattern` or API | ej. "V6", "I4" |
| `displacement_cc` | int | `vehiclespecpattern` or API | |
| `nhtsa_make_id` | int | `defs_make.id` | anti-duplicate |
| `nhtsa_model_id` | int | `defs_model.id` | anti-duplicate |
| `created_at` | timestamp | | |
| `updated_at` | timestamp | | |

Indexes:
- `UNIQUE (year, make, model, series)` — primary dedup key
- `(year)` — for year menu
- `(year, make)` — for make filter
- `(year, make, model)` — for model filter

#### `user_vehicle` — User-Owned Vehicles

Refactored from current `vehicles` table. Only ownership data, no specs.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `owner_id` | UUID FK → users | NOT NULL |
| `vehicle_id` | UUID FK → vehicle | NOT NULL |
| `color` | varchar(40) | |
| `plate` | varchar(20) | license plate |
| `vin` | varchar(17) | nullable |
| `notes` | text | nullable |
| `created_at` | timestamp | |
| `updated_at` | timestamp | |
| `is_deleted` | bool | soft delete |
| `deleted_at` | timestamp | |

Indexes:
- `UNIQUE (owner_id, plate)`
- `(owner_id)` — list my vehicles
- `(vehicle_id)` — lookup by catalog entry

### 3.2 NHTSA VehicleType → Pricing Tier

`VehicleSize` is **removed**. Pricing is now per NHTSA `VehicleType`. The API returns `VehicleType` directly; we abbreviate and store it.

| NHTSA Name | Abbreviation (stored) | Code Enum |
|---|---|---|
| Motorcycle | `MC` | `VehicleType.MOTORCYCLE` |
| Passenger Car | `PC` | `VehicleType.PASSENGER_CAR` |
| Truck | `TRUCK` | `VehicleType.TRUCK` |
| Bus | `BUS` | `VehicleType.BUS` |
| Trailer | `TRAILER` | `VehicleType.TRAILER` |
| Multipurpose Passenger Vehicle (MPV) | `MPV` | `VehicleType.MPV` |
| Low Speed Vehicle (LSV) | `LSV` | `VehicleType.LSV` |
| Incomplete Vehicle | `INC` | `VehicleType.INCOMPLETE` |
| Off Road Vehicle | `ORV` | `VehicleType.OFF_ROAD` |

Derivation chain:

```
NHTSA API returns VehicleType + BodyClass
  → VehicleType (abbreviated) stored in vehicle.vehicle_type
  → Used as pricing tier across all services
```

`vehicle_type` is **stored** on the `vehicle` table. The old `map_body_to_size()` is replaced by `get_vehicle_type(raw_vehicle_type: str) → VehicleType` in `infrastructure/nhtsa/client.py`.

**Impact on appointment pricing:**
- `appointment_vehicles.vehicle_size` column → renamed to `vehicle_type`
- `fare_router.py` pricing lookup → keyed by `VehicleType` not `VehicleSize`
- Service pricing tables → 9 cols instead of 4 (per type)

### 3.3 NHTSA ID Dedup Strategy

When inserting into `vehicle`:

- **From seed:** `nhtsa_make_id` and `nhtsa_model_id` are populated. Unique constraint on `(year, make, model, series)` catches duplicates across seed batches.
- **From API VIN decode:** NHTSA API returns numeric Make ID but not Model ID. Check by `(year, make, model, series)` first. `nhtsa_make_id` populated if returned by API; `nhtsa_model_id` may stay NULL until a vPIC match.
- **From vPIC backup:** Full IDs available.

### 3.4 Seed ETL — `scripts/seed_vehicle_catalog.py`

One-time script that:

1. Connects to the user's vPIC backup DB
2. Reads `defs_make` → `vehicle.make` (107 makes)
3. Reads `defs_model` for each make, parses `includes` column:
   - Split by comma → individual series values
   - Expand year range: `from_year` → `to_year`
   - Insert into `vehicle` with `nhtsa_make_id`, `nhtsa_model_id`
4. Joins `vpic.vehicletype` for vehicle_type abbreviation when available
5. Optionally joins `vehiclespecpattern` for structured specs (body_class, fuel, drive, engine)
6. Estimated output: **30k–50k rows**

Script is idempotent — respects unique constraint `(year, make, model, series)`.

### 3.5 Menu Endpoints

All queries target `vehicle` table directly. No external calls.

| Method | Path | SQL |
|---|---|---|
| GET | `/api/v1/catalog/years` | `SELECT DISTINCT year FROM vehicle ORDER BY year DESC` |
| GET | `/api/v1/catalog/makes?year=X` | `SELECT DISTINCT make FROM vehicle WHERE year=X ORDER BY make` |
| GET | `/api/v1/catalog/models?year=X&make=Y` | `SELECT DISTINCT model FROM vehicle WHERE year=X AND make=Y ORDER BY model` |
| GET | `/api/v1/catalog/series?year=X&make=Y&model=Z` | `SELECT DISTINCT series FROM vehicle WHERE year=X AND make=Y AND model=Z ORDER BY series` |
| GET | `/api/v1/catalog/{id}` | Full specs for one catalog entry |

**Frontend (mobile + web):**
- Detailer/Car Wash menu: `year → make → model`
- Mechanic menu: `year → make → model → series` (extra level for trim-dependent pricing)

### 3.6 VIN Decode Endpoint

```
GET /api/v1/catalog/decode/{vin}
```

Flow:

```
1. NHTSA API → DecodeVinValues/{vin}
   ├── Success → upsert vehicle row if new → return specs
   └── 503/404 → vPIC backup DB → upsert vehicle → return specs
```

Response:

```json
{
  "vehicle_id": "uuid",
  "year": 2024,
  "make": "Honda",
  "model": "Civic",
  "series": "LX",
  "body_class": "Sedan",
  "vehicle_type": "PC",
  "fuel_type": "Gasoline",
  "displacement_cc": 1996,
  "drive_type": "FWD",
  "transmission": "Automatic",
  "engine_config": "I4"
}
```

### 3.7 UserVehicle Endpoints

Refactored from current vehicle router:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/user-vehicles` | Add vehicle (vehicle_id from catalog) |
| GET | `/api/v1/user-vehicles` | List my vehicles |
| PUT | `/api/v1/user-vehicles/{id}` | Edit color/plate/vin/notes |
| DELETE | `/api/v1/user-vehicles/{id}` | Soft delete |

### 3.8 Migration Plan

**Phase 1 — Create tables (Alembic):**

```python
# migration
op.create_table("vehicle", ...)
op.create_table("user_vehicle", ...)
```

**Phase 2 — Seed catalog:**

```bash
python scripts/seed_vehicle_catalog.py
```

**Phase 3 — Migrate existing data:**

For each row in `vehicles`:
```sql
INSERT INTO vehicle (year, make, model, series, body_class)
SELECT DISTINCT v.year, v.make, v.model, v.series, v.body_class
FROM vehicles v
WHERE NOT EXISTS (
  SELECT 1 FROM vehicle c
  WHERE c.year=v.year AND c.make=v.make AND c.model=v.model AND c.series IS NOT DISTINCT FROM v.series
);

INSERT INTO user_vehicle (id, owner_id, vehicle_id, color, plate, vin, notes, created_at, updated_at, is_deleted, deleted_at)
SELECT v.id, v.owner_id, c.id, v.color, v.license_plate, v.vin, v.notes, v.created_at, v.updated_at, v.is_deleted, v.deleted_at
FROM vehicles v
JOIN vehicle c ON c.year=v.year AND c.make=v.make AND c.model=v.model AND c.series IS NOT DISTINCT FROM v.series;
```

**Phase 4 — Update FKs:**

| FK | Current → New |
|---|---|
| `appointment_vehicles.vehicle_id` | → `user_vehicle.id` |
| `client_profiles.default_vehicle_id` | → `user_vehicle.id` |
| `vehicle_photos.vehicle_id` | → `user_vehicle.id` |

**Phase 5 — Drop old table + create VehicleType enum:**

```python
op.drop_table("vehicles")
op.execute("DROP TYPE IF EXISTS vehicle_size_enum")
op.execute("""
  CREATE TYPE vehicle_type_enum AS ENUM (
    'MC', 'PC', 'TRUCK', 'BUS', 'TRAILER',
    'MPV', 'LSV', 'INC', 'ORV'
  )
""")
# Update appointment_vehicles.vehicle_size → vehicle_type with new enum
op.alter_column("appointment_vehicles", "vehicle_size",
  new_column_name="vehicle_type",
  type_=sa.Enum("MC","PC","TRUCK","BUS","TRAILER","MPV","LSV","INC","ORV",
                 name="vehicle_type_enum"),
  postgresql_using="vehicle_size::text::vehicle_type_enum",
)
```

**Phase 6 — Rename (optional):**

If desired, rename `user_vehicle` → `vehicles` once old table is gone.

### 3.9 New File Structure

```
backend/
├── domains/
│   └── vehicles/
│       ├── __init__.py
│       ├── models.py            # vehicle + user_vehicle models
│       ├── schemas.py           # VehicleRead, UserVehicleCreate, etc.
│       ├── router.py            # user_vehicle CRUD endpoints
│       ├── catalog_router.py    # NEW — menu + VIN decode endpoints
│       ├── repository.py        # UserVehicleRepository
│       ├── catalog_repository.py # NEW — vehicle catalog queries
│       └── service.py           # get_size_from_body_class
├── infrastructure/
│   └── nhtsa/
│       └── client.py            # get_vehicle_type() replaces map_body_to_size()
├── scripts/
│   └── seed_vehicle_catalog.py  # NEW — ETL from vPIC dump
└── app/
    └── db/
        └── registry.py          # add vehicle + user_vehicle imports
```

### 3.10 Dependencies

| Existing FK | Affected? | Action |
|---|---|---|
| `appointment_vehicles.vehicle_id` → `vehicles.id` | Yes | Point to `user_vehicle.id` |
| `client_profiles.default_vehicle_id` → `vehicles.id` | Yes | Point to `user_vehicle.id` |
| `vehicle_photos.vehicle_id` → `vehicles.id` | Yes | Point to `user_vehicle.id` |
| `appointments.vehicle_id` → `vehicles.id` | Yes | Point to `user_vehicle.id` |

### 3.11 body_class Enrichment (Optional)

If the vPIC `vehiclespecpattern` query provides body_class/fuel/drive/engine for a given `(year, make, model)`, apply it at seed time. Otherwise these fields are populated lazily when a user scans a VIN, and backfilled by a periodic job.

## 4. Prerequisites

> :warning: **Hard prerequisite**: [`08-hardening.md`](../plans/08-hardening.md) Phases 0 + 3 must be complete before implementing this plan.

El refactor completo de `vehicles` -> `vehicle` (catalogo) + `user_vehicle` colisiona con las DB migrations de hardening (rename `estimated_price_cents`, `Integer` -> `BigInteger`). Ambas migraciones tocan columnas en `appointments` y tablas relacionadas.

| Prerrequisito | Plan | Estatus |
|--------------|------|---------|
| Backend hardening Phases 0 + 3 | `08-hardening.md` | Draft |
| DB migrations: `estimated_price_cents` | Phase 3 en hardening | Draft |
| NHTSA infra fix: `map_body_to_size` a `shared/` | M10 en hardening Phase 0 | Draft |
| 00-user base (zip_code) | `00-user.md` | Planning |

## 5. Dependency

```
00-user.md
  `-- 01-profiles.md
        +-- 02-detailing.md
        +-- 03-mechanic.md
        `-- 04-vehicles.md  <- you are here (standalone, referenced by detailing + mechanic)
```

`04-vehicles.md` is standalone — no dependency on profile or service plans. Detailing (02) and mechanic (03) reference `vehicle` and `user_vehicle` for appointment pricing.

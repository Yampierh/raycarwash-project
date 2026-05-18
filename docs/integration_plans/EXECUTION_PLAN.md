# Plan de implementación — `docs/integration_plans/` (00–04) como equipo de devs

> **Status:** Active | **Date:** 2026-05-17 | **Base commit:** `237bedb`
>
> Este documento coordina los 5 planes de integración vertical contra la sesión paralela de `plan.md` (Phases 0–9).  
> Ver [README.md](./README.md) para el índice de planes y orden de dependencias.

---

## Contexto

El directorio [docs/integration_plans/](docs/integration_plans/) contiene 5 specs verticales (`00-user`, `01-profiles`, `02-detailing`, `03-mechanic`, `04-vehicles`) que extienden RayCarWash con: (1) `Address` y multi-rol, (2) `ProviderProfile` 1:N con `provider_type`, (3) catálogo de detailing + combos, (4) vertical mecánico nuevo, (5) catálogo de vehículos basado en NHTSA vPIC.

En **otra sesión** se está ejecutando [plan.md](plan.md). Estado real al 2026-05-17 (commit `237bedb`):

- ✅ **Master**: Phases 0, 1, 2, 3 + Hotfix 0.5 cerrados — envelope, idempotency, step-up (H3 wired en 6 sitios), Profile Hub `/users/me?include=...`, avatar/cover, contact changes, TOTP 2FA, security + history endpoints, passkeys. 250/250 tests verdes en master.
- 🚧 **`feat/profile-phase4`**: chunks R/S/T/U/V/Docs ya en branch — UserAddress + PaymentMethod + ClientFavorite + VehiclePhoto (migrations `m_006..m_010`), Geocoding adapter, 28 endpoints nuevos en `/users/me/{addresses,payment-methods,favorites,vehicle-photos}` + Hub blocks. 294/294 tests verdes. Chunk W (mobile screens) pendiente.
- ⏳ **Phases 5–9 pendientes**: Provider portfolio + documents + Stripe Identity (Phase 5), active role switcher (Phase 6), notifications/privacy/public profile (Phase 7), GDPR (Phase 8), polish/analytics (Phase 9).

Ese trabajo es **infraestructura horizontal** (transversal a User/Provider); los integration_plans son **verticales de producto**. El solapamiento ahora se concentra en **Phase 5 (provider portfolio)** y **Phase 6 (active role)** — ambos NO comenzados, lo que abre una ventana óptima para landear nuestro E1 (multi-profile) ANTES que esas fases arranquen.

**Decisiones de negocio confirmadas:**
1. Trabajo en paralelo con la sesión de `plan.md`, coordinación vía commits.
2. Vehicles: refactor completo + seed NHTSA (no coexistencia).
3. Mecánico: backend + endpoints únicamente; sin UI ni onboarding de proveedores mecánicos hasta validar demanda.

**Objetivo:** entregar los 5 verticales con calidad de producción (estándares, tests, migraciones simétricas, documentación), respetando las convenciones de [plan.md §0.5](plan.md) y la arquitectura DDD-lite ya consolidada. **Aprovechar la ventana de Phases 5–6 pendientes** para que multi-profile aterrice como cimiento, no como refactor posterior.

---

## 1. Estado actual relevante (auditoría rápida, 2026-05-17)

Lo que **ya existe** en el repo (no replicar):

| Elemento | Estado | Ubicación |
|---|---|---|
| `User` con `avatar_s3_key`, `last_step_up_at`, `active_role`, `preferred_language`, `preferred_timezone`, `onboarding_status` | ✅ Implementado | [backend/domains/users/models.py](backend/domains/users/models.py) |
| `UserAddress` (label, street, city, state, zip, lat/lng, is_primary, soft delete) | ✅ Migrado en `m_006` | [backend/domains/users/user_address.py](backend/domains/users/user_address.py) |
| `ClientProfile` con `default_vehicle_id`, `default_address_id` | ✅ Migrado en `m_010` | [backend/domains/users/models.py](backend/domains/users/models.py) |
| `ProviderProfile` (1:1 con User, display_name, business_name, tagline, social_links, verification) | ✅ Implementado, **falta refactor 1:N** | [backend/domains/providers/models.py](backend/domains/providers/models.py) |
| `Vehicle` (single table, `owner_id` FK directo, VehicleSize 4 tiers) | ✅ Existente, **a refactorizar** | [backend/domains/vehicles/models.py](backend/domains/vehicles/models.py) |
| `Service`, `Addon`, `DetailerService`, `Specialty`, `ProviderSpecialty`, `ServiceCategory` | ✅ Catálogo detailing operativo | [backend/domains/services_catalog/models.py](backend/domains/services_catalog/models.py) |
| `Appointment` (state machine, `detailer_id`, `vehicle_id`) | ✅ Maduro | [backend/domains/appointments/models.py](backend/domains/appointments/models.py) |
| Infraestructura: `nhtsa/client.py`, `geocoding/`, `storage/`, `redis/`, `h3/` | ✅ Adapters listos | [backend/infrastructure/](backend/infrastructure/) |
| Auth refactor (routers/ package, RS256, JWKS) | ✅ Completo | [backend/domains/auth/routers/](backend/domains/auth/routers/) |

Lo que **falta** (gaps cubiertos por integration_plans):

- `User.zip_code` (campo simple — 00-user)
- `ProviderProfile`: relación 1:N, columna `provider_type`, unique compuesto, rename `is_accepting_bookings → is_active` (01-profiles)
- Tabla `provider_service_categories` (m2m), rename `detailer_services → provider_services` (01-profiles)
- Modelos `Combo` + `ComboItem` (02-detailing, compartido con 03)
- Categorías mecánico: `OIL_CHANGE`, `BRAKE_SERVICE`, `TIRE_*`, `BATTERY_REPLACEMENT` (03-mechanic)
- `Service.price_type` + `fixed_price_cents`, `Appointment.service_notes` (03-mechanic)
- Tablas `vehicle` (catálogo NHTSA) + `user_vehicle`, refactor de 4 FKs, drop legacy `vehicles`, enum `vehicle_type` reemplazando `vehicle_size` (04-vehicles)
- Script `scripts/seed_vehicle_catalog.py` (vPIC ETL)

---

## 2. Equipo y responsabilidades

| Rol | Responsabilidad principal | Outputs verificables |
|---|---|---|
| **Tech Lead** | Coordinación con sesión paralela, gating de merges, ADRs nuevos, revisión de migraciones | Branch protection rules, semanal sync log, ADR-009..N |
| **Backend (Domain)** | Modelos, repositorios, servicios, schemas, routers por dominio | Cobertura ≥80% por dominio, type-check verde |
| **Backend (Infra/Data)** | Migraciones Alembic, seed NHTSA, integración vPIC, índices, perfiles de query | `alembic upgrade/downgrade head` round-trip OK, seed idempotente |
| **API Designer** | Contratos REST alineados con envelope de plan.md, OpenAPI, idempotency, step-up | OpenAPI publicado, contract tests verdes |
| **Frontend Mobile** (Expo/RN 0.81) | Pantallas detailing extendidas, profile switcher, no UI mecánico | Storybook + screenshots de QA |
| **Frontend Web** (Next.js 15) | Admin dashboard: gestión combos, catálogo vehículos, servicios mecánico | Páginas en `/dashboard/catalog/*` |
| **QA/Test** | Fixtures, contract tests, migración round-trip, e2e crítico | `pytest -m integration` verde, snapshot stable |
| **DevOps** | vPIC dump en dev, Alembic CI gating, secrets rotation | Pipeline verde, runbook de seed |

Una misma persona puede vestir varios sombreros; lo importante es que cada output exista y sea revisable.

---

## 3. Coordinación con sesión paralela de `plan.md` — vía git

**Sí es viable** la coordinación por commits, pero requiere disciplina explícita porque tres entidades son zonas de conflicto: `User`, `ProviderProfile`, y `alembic/versions/`.

### 3.1 Branching strategy

```
master
  ├── feat/profile-hub/*           ← sesión plan.md (Phases 0–9)
  └── feat/integrations/*          ← esta sesión
        ├── feat/integrations/00-user-zipcode
        ├── feat/integrations/01-profiles-multi
        ├── feat/integrations/04-vehicles-catalog
        ├── feat/integrations/02-detailing-combos
        └── feat/integrations/03-mechanic-backend
```

Reglas:
- **Rebase contra `master` antes de cada PR** (no merge). Si plan.md mergeó cambios a `User` o `ProviderProfile`, los integramos vía rebase.
- **Una migración Alembic por PR**, nunca dos pendientes simultáneas en la misma rama; el `down_revision` se actualiza en el rebase final.
- **No tocar archivos "calientes" de plan.md sin handoff:** [backend/domains/users/hub_service.py](backend/domains/users/hub_service.py), [backend/domains/users/hub_schemas.py](backend/domains/users/hub_schemas.py), [backend/domains/auth/](backend/domains/auth/).
- Commits con prefijo: `feat(integrations/0X): ...`, `chore(integrations/0X): migration ...`.

### 3.2 Zonas de conflicto y mitigación

| Archivo | Riesgo | Mitigación |
|---|---|---|
| [backend/domains/users/models.py](backend/domains/users/models.py) `User` | Medio — plan.md agrega columnas Phase 0/3/6; nosotros sólo `zip_code` | PRs pequeños, atomic adds, rebase frecuente |
| [backend/domains/providers/models.py](backend/domains/providers/models.py) `ProviderProfile` | **Alto** — plan.md extiende campos públicos; nosotros pasamos 1:1 a 1:N | Coordinar window: nuestro PR 01-profiles debe mergearse cuando plan.md Phase 5 (provider portfolio) **no esté en flight**. Sync explícito requerido. |
| [backend/domains/vehicles/](backend/domains/vehicles/) | **Alto** — plan.md Phase 4 chunk R agregó `VehiclePhoto`; nosotros migramos `vehicles → user_vehicle` y rompemos FK | Antes del refactor 04, anclar `vehicle_photos.vehicle_id` a la nueva `user_vehicle.id` en la misma migración. |
| [backend/alembic/versions/](backend/alembic/versions/) | **Alto** — numeración lineal | Usar nomenclatura `m_NNN_descripcion.py` y rebase para renumerar. Tech Lead aprueba `down_revision` chain antes de merge. |
| [backend/domains/services_catalog/models.py](backend/domains/services_catalog/models.py) | Bajo — plan.md no toca | Sin restricción especial |

### 3.3 Cadencia

- Diario: rebase de ramas activas contra `master`.
- Antes de PR: `git fetch && git rebase origin/master && pytest && alembic upgrade head && alembic downgrade -1 && alembic upgrade head`.
- Tech Lead revisa PR si toca User/ProviderProfile/migraciones.

---

## 4. Convenciones y estándares (no negociables)

Adoptamos las de [plan.md §0.5](plan.md) y agregamos las específicas de integraciones:

1. **Idioma**: código, comentarios y docstrings en inglés; commits y PRs en español o inglés (consistente por rama).
2. **DDD-lite**: cada vertical en `backend/domains/<name>/` con `models.py`, `schemas.py`, `repository.py`, `service.py`, `router.py`. Routers `/api/v1/<resource>` y prefijos consistentes.
3. **Response envelope**: `Envelope[T]` siempre con `data`, `meta`, `errors`. Aplica el `EnvelopeRouter` del plan.md (no inventar wrapper propio).
4. **Migraciones Alembic**: upgrade y downgrade **ambos** funcionales; CI test de round-trip. Si FK depende de plan paralelo, columna sin constraint + migración aparte.
5. **Adapters**: NHTSA vía `infrastructure/nhtsa/client.py` (ya existe); extender con `get_vehicle_type()` y fallback a vPIC backup. Mantener Protocol.
6. **Seed scripts**: idempotentes, transaccionales, con `--dry-run`. Outputs medidos (rows inserted/skipped).
7. **Tests**: cada endpoint tiene happy path + edge case + permisos; cada migración tiene test de round-trip; cada servicio tiene unit con fixtures de [backend/tests/conftest.py](backend/tests/conftest.py).
8. **TODO marker discipline**: `TODO(integrations/0X): <desc>` cuando se difiere algo dentro del scope; nunca código muerto sin marcar.
9. **Documentación**: cada épica cierra con un changelog en `docs/integration_plans/0X-<name>.md` marcando "Status: DONE — <commit-sha>".
10. **No backward-compat hacks**: si renombramos `detailer_services → provider_services`, los call-sites se actualizan en la misma PR.

---

## 5. Plan de ejecución por épica

Orden de implementación (refleja dependencias del README):

```
Sprint 1   Sprint 2   Sprint 3       Sprint 4   Sprint 5
[00]──────►[01]──────►[04]──────────►[02]──────►[03]
                          (vPIC seed)
```

Mecánico (03) **sólo backend**: modelos, endpoints, seed de servicios. Sin UI ni onboarding.

---

### Épica E0 — `00-user.md` · User shared profile + zip_code

**Owner:** Backend (Domain) · **Sprint 1 · ~3 días**

**Alcance ajustado** (el resto de 00-user ya existe):
- Agregar `User.zip_code: Mapped[str | None]` en [backend/domains/users/models.py](backend/domains/users/models.py)
- Actualizar `User.is_provider()` para chequear `has_role("detailer") OR has_role("mechanic")` (preparando 01)
- Verificar que `Address` (ya `UserAddress`) satisface las expectativas del plan; documentar el mapeo de nombres

**Archivos críticos:**
- [backend/domains/users/models.py](backend/domains/users/models.py) — agregar columna
- [backend/alembic/versions/m_011_user_zipcode.py](backend/alembic/versions/) — migración nueva
- [backend/domains/users/schemas.py](backend/domains/users/schemas.py) — exponer en `UserRead` opcional
- [backend/tests/test_users_hub.py](backend/tests/test_users_hub.py) — incluir en bloque `profile`

**Riesgos:** mínimos. La columna es nullable y aditiva, no rompe nada.

**Verificación:**
- `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` round-trip OK
- `pytest backend/tests/test_users_hub.py -k zipcode`
- Manual: `GET /api/v1/users/me?include=profile` retorna `zip_code` en respuesta cuando está seteado

---

### Épica E1 — `01-profiles.md` · Multi-Profile system

**Owner:** Backend (Domain) + Tech Lead (sync con plan.md) · **Sprint 2 · ~6 días**

**Cambios estructurales (alto impacto):**

1. **Modelo `ProviderProfile`** ([backend/domains/providers/models.py](backend/domains/providers/models.py)):
   - Agregar `provider_type: Mapped[ProviderType]` (enum: `DETAILER`, `MECHANIC`)
   - Quitar unique constraint en `user_id`
   - Agregar unique compuesto `(user_id, provider_type)`
   - Renombrar `is_accepting_bookings → is_active` (mantener default `True`)
   - Índice `(provider_type, is_active)`

2. **Relación `User.provider_profile`** → `User.provider_profiles: list[ProviderProfile]`
   - Lazy strategy: `selectin` (mantenemos el patrón consolidado en auth hardening)
   - **Actualizar todos los call-sites** que asumen 1:1: matching, schemas, services. Grep `provider_profile` y revisar.

3. **Tabla nueva `provider_service_categories`** (m2m, reemplaza `service_category_id` FK):
   - Migración: `INSERT INTO provider_service_categories SELECT id AS provider_id, service_category_id FROM provider_profiles WHERE service_category_id IS NOT NULL;` luego drop columna.

4. **Rename `detailer_services → provider_services`** + columna `detailer_id → provider_id`:
   - Alembic `op.rename_table` + `op.alter_column`
   - Actualizar [backend/domains/services_catalog/models.py](backend/domains/services_catalog/models.py) (`DetailerService → ProviderService`)
   - Grep y actualizar call-sites

**Endpoints nuevos:**
- `POST /api/v1/providers/profiles` — crear perfil de tipo X
- `GET /api/v1/providers/profiles` — listar mis perfiles
- `PATCH /api/v1/providers/profiles/{id}` — actualizar
- `DELETE /api/v1/providers/profiles/{id}` — soft-delete
- `GET /api/v1/providers?type=mechanic` — público filtrado

**Archivos críticos:**
- [backend/domains/providers/models.py](backend/domains/providers/models.py)
- [backend/domains/providers/router.py](backend/domains/providers/router.py)
- [backend/domains/providers/service.py](backend/domains/providers/service.py)
- [backend/domains/services_catalog/models.py](backend/domains/services_catalog/models.py) — `ProviderService` rename
- [backend/domains/matching/service.py](backend/domains/matching/service.py) — filtros por `provider_type`
- [backend/alembic/versions/m_012_provider_multiprofile.py](backend/alembic/versions/) (varias migraciones secuenciales, no monolítica)

**Riesgos:**
- **Crítico**: choque con plan.md Phase 5 (provider portfolio). Sincronizar con Tech Lead antes de merge.
- Romper el Profile Hub bloque `provider` si no actualizamos [backend/domains/users/hub_service.py](backend/domains/users/hub_service.py). Coordinar con sesión paralela: hub debe iterar `provider_profiles` y exponer una lista o filtrar por `active_role`.
- Matching algorithm: si filtra por `User.provider_profile`, hay que migrar a `provider_profiles` o agregar `provider_id` directo.

**Verificación:**
- Test de migración: crear usuario con 1 perfil, migrar, verificar que sigue accesible; crear segundo perfil, verificar unique compuesto rechaza duplicado.
- `pytest backend/tests/test_providers.py backend/tests/test_matching.py`
- Smoke: usuario con dual-role (detailer + mechanic) lista 2 perfiles vía `GET /api/v1/providers/profiles`.

---

### Épica E2 — `04-vehicles.md` · Vehicle catalog + UserVehicle

**Owner:** Backend (Infra/Data) + DevOps · **Sprint 3 · ~8 días**

Trabajo en 6 fases de migración (todas Alembic versionadas):

1. **`m_013_create_vehicle_catalog.py`**: tabla `vehicle` con índices y unique `(year, make, model, series)`
2. **Seed**: `scripts/seed_vehicle_catalog.py` lee vPIC backup PostgreSQL, hace ETL, inserta ~30–50k filas idempotentes
3. **`m_014_create_user_vehicle.py`**: tabla `user_vehicle` (owner_id, vehicle_id FK al catálogo, color, plate, vin, notes, soft delete)
4. **`m_015_migrate_legacy_vehicles.py`**: data migration que (a) inserta entradas de catálogo derivadas de tabla legacy, (b) inserta filas en `user_vehicle` con FK al catálogo
5. **`m_016_update_vehicle_fks.py`**: actualiza FKs en `appointments.vehicle_id`, `appointment_vehicles.vehicle_id`, `vehicle_photos.vehicle_id`, `client_profiles.default_vehicle_id` apuntando a `user_vehicle.id`
6. **`m_017_drop_legacy_vehicles.py`**: drop tabla `vehicles` legacy, crea enum `vehicle_type` (9 tipos NHTSA), rename `vehicle_size_enum → vehicle_type_enum` en `appointment_vehicles`

**Endpoints nuevos:**
- `GET /api/v1/catalog/years|makes|models|series` — drill-down menu
- `GET /api/v1/catalog/{id}` — specs detalladas
- `GET /api/v1/catalog/decode/{vin}` — NHTSA → vPIC fallback
- `POST|GET|PUT|DELETE /api/v1/user-vehicles` — CRUD ownership

**Archivos críticos:**
- Nueva estructura [backend/domains/vehicles/](backend/domains/vehicles/):
  - `models.py` (Vehicle + UserVehicle)
  - `catalog_router.py` (menu + VIN decode)
  - `catalog_repository.py`
  - `router.py` (user-vehicles CRUD existente, adaptado)
- [backend/infrastructure/nhtsa/client.py](backend/infrastructure/nhtsa/client.py) — agregar `get_vehicle_type()`, reemplazar `map_body_to_size()`
- [scripts/seed_vehicle_catalog.py](scripts/) — NUEVO
- [backend/domains/appointments/](backend/domains/appointments/) — actualizar todas las referencias `vehicle_size → vehicle_type` (pricing logic incluida)
- [backend/domains/services_catalog/models.py](backend/domains/services_catalog/models.py) — `Service.price_*` columns adaptadas a 9 tipos (o reestructurar a JSONB `prices_by_type`)

**Riesgos:**
- **Crítico**: pricing de detailing actualmente usa 4 tiers (`VehicleSize`). Mapear a 9 tipos requiere decisión de pricing: la opción más limpia es JSONB `prices: {"PC": 50, "MPV": 60, ...}` con tipos default agrupados. Documentar en ADR-009.
- vPIC backup DB requiere setup local en dev (DevOps runbook).
- Seed largo (~30–50k rows) — usar bulk inserts y `--batch-size`.
- Conflicto con plan.md Phase 4 chunk R (`vehicle_photos`): la migración m_016 toca esa FK.

**Verificación:**
- `python scripts/seed_vehicle_catalog.py --dry-run` reporta counts esperados
- `pytest backend/tests/test_vehicles.py backend/tests/test_appointments.py`
- Manual: VIN decode con VIN real conocido devuelve specs correctos; VIN inválido devuelve 404 con `code: VIN_NOT_FOUND`; NHTSA API down → fallback a vPIC silencioso
- Round-trip Alembic completo: `upgrade head → downgrade base → upgrade head` sin errores

---

### Épica E3 — `02-detailing.md` · Combos system

**Owner:** Backend (Domain) + Frontend Mobile · **Sprint 4 · ~5 días**

Detailing ya es un vertical operativo; sólo agregamos combos y consolidamos.

**Modelos nuevos** en [backend/domains/services_catalog/](backend/domains/services_catalog/):
- `Combo` (id, name, description, is_custom, discount_percent, is_active)
- `ComboItem` (id, combo_id FK, service_id nullable FK, addon_id nullable FK, quantity)
- Check constraint: exactamente uno de `service_id` o `addon_id` debe ser NOT NULL

**Modelo `Appointment`** extendido:
- `combo_id: Mapped[UUID | None]` (FK opcional)

**Endpoints nuevos:**
- `GET /api/v1/combos` — fijos (is_custom=False)
- `POST /api/v1/combos/custom` — usuario crea custom
- `GET /api/v1/combos/{id}/price?vehicle_type=PC` — cálculo con descuento
- `POST /api/v1/appointments` — aceptar `combo_id` opcional

**Seeds:**
- 4 combos fijos (Express, Weekend, Full Makeover, Showroom Ready) en `scripts/seed_combos.py` o extender `scripts/seed_services.py`.

**Archivos críticos:**
- [backend/domains/services_catalog/models.py](backend/domains/services_catalog/models.py)
- [backend/domains/services_catalog/router.py](backend/domains/services_catalog/router.py)
- [backend/domains/services_catalog/service.py](backend/domains/services_catalog/service.py) — `calculate_combo_price()`
- [backend/domains/appointments/service.py](backend/domains/appointments/service.py) — soportar combo
- Frontend Mobile: pantalla de selección de combo (Storybook + integración en booking flow)

**Riesgos:**
- Pricing dinámico de custom combos requiere validar reglas (10% / 15%). Validar con producto antes de hardcodear.
- `combo_id` en `appointments` impacta el response shape — coordinar con sesión paralela si `appointments` está en su scope (no parece).

**Verificación:**
- Test unit: `calculate_combo_price()` con discount 15%, vehicle_type PC, 3 items
- Integration: crear appointment con `combo_id`, verificar precio final correcto
- Mobile: snapshot del nuevo selector

---

### Épica E4 — `03-mechanic.md` · Vertical mecánico (backend-only)

**Owner:** Backend (Domain) · **Sprint 5 · ~5 días**

**Scope reducido confirmado:** modelos, migraciones, endpoints, seed. **Sin UI mobile/web**, sin onboarding de proveedores mecánicos.

**Modelos:**
- `ServiceCategory` enum extender: `OIL_CHANGE`, `BRAKE_SERVICE`, `TIRE_REPAIR`, `TIRE_ROTATION`, `TIRE_REPLACEMENT`, `BATTERY_REPLACEMENT`
- `Service.price_type: Mapped[PriceType]` (enum: `BY_SIZE`, `FIXED_PRICE`) — default `BY_SIZE`
- `Service.fixed_price_cents: Mapped[int | None]`
- `Appointment.service_notes: Mapped[dict | None]` (JSONB) — esquema libre por ahora; documentar shape en docstring
- (opcional) `AppointmentPart` (id, appointment_id, name, quantity, unit_price_cents) — flag TODO para Phase 2 si el equipo lo defiere

**Endpoints:**
- `GET /api/v1/services?type=mechanic` — filtra por categoría mecánico
- `GET /api/v1/providers?type=mechanic` — listing público
- Reutilizar `POST /api/v1/providers/profiles` con `provider_type=MECHANIC`
- `POST /api/v1/appointments` — aceptar `service_notes`
- `PATCH /api/v1/appointments/{id}/parts` — diferido a Phase 2, marcar `TODO(integrations/03-phase2): parts tracking endpoint`

**Seeds:**
- 6 servicios fijos en `scripts/seed_services.py` (extender, no archivo nuevo)
- 3 combos compartidos (Tune-Up, Safety Check, Full Service) reusando `Combo`/`ComboItem` de E3

**Archivos críticos:**
- [backend/domains/services_catalog/models.py](backend/domains/services_catalog/models.py) — agregar enums y columnas
- [backend/domains/services_catalog/service.py](backend/domains/services_catalog/service.py) — lógica de pricing: si `price_type == FIXED_PRICE` usa `fixed_price_cents`, ignora `vehicle_type`
- [backend/domains/appointments/models.py](backend/domains/appointments/models.py) — `service_notes`
- [backend/alembic/versions/m_018_mechanic_vertical.py](backend/alembic/versions/)
- [scripts/seed_services.py](scripts/seed_services.py)

**Riesgos:**
- Sin UI, no podemos testear end-to-end manualmente. Mitigación: smoke con `curl` documentado en `docs/integration_plans/03-mechanic-runbook.md`.
- Si `Service` ya tiene columnas `price_small/medium/large/xl`, agregar `price_type` y `fixed_price_cents` puede dejar columnas inconsistentes — definir invariante en check constraint o en service layer.

**Verificación:**
- `pytest backend/tests/test_services_catalog.py -k mechanic`
- Smoke: `POST /api/v1/providers/profiles {"provider_type": "MECHANIC"}` → `GET /api/v1/providers?type=mechanic` retorna 1 elemento
- `GET /api/v1/services?type=mechanic` retorna 6 servicios fijos sembrados

---

## 6. Verificación end-to-end (épicas completas)

Al cerrar cada épica, ejecutar:

```bash
# Backend
pytest backend/tests/ -v --maxfail=3
mypy backend/
ruff check backend/

# Migraciones (CI-grade)
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# Seed (idempotencia)
python scripts/seed_rbac.py
python scripts/seed_services.py
python scripts/seed_vehicle_catalog.py --batch-size 1000  # solo épica E2
python scripts/seed_combos.py                              # solo épica E3

# Smoke API (via httpie o curl, documentado en runbook por épica)
http POST :8000/api/v1/auth/login email=detailer@test.com password=...
http GET  :8000/api/v1/providers/profiles  Authorization:"Bearer $TOKEN"
http POST :8000/api/v1/providers/profiles  provider_type=MECHANIC Authorization:"Bearer $TOKEN"
http GET  :8000/api/v1/catalog/decode/1HGCM82633A123456
```

Al cerrar las 5 épicas:
- Test e2e que arme: registro de usuario → crear ProviderProfile detailer → crear segundo ProviderProfile mecánico → listar perfiles → crear UserVehicle desde catálogo → crear appointment de detailing con combo → crear appointment de mecánico con `service_notes`.
- Verificar Profile Hub: `GET /api/v1/users/me?include=provider` devuelve lista de perfiles (coordinar con sesión paralela el shape final).

---

## 7. Risks register (resumen)

| Riesgo | Severidad | Mitigación | Owner |
|---|---|---|---|
| Conflicto en `ProviderProfile` con plan.md Phase 5 | **Medio** (downgrade — Phase 5 aún no arranca al 2026-05-17) | Landear E1 ANTES que Phase 5 inicie; comunicar a sesión paralela el shape multi-profile para que Phase 5 lo herede | Tech Lead |
| Multi-perfil rompe diseño de Phase 6 active role switcher | Medio | Coordinar: `active_role` debe poder seleccionar un perfil específico del set 1:N, no sólo un rol RBAC | Tech Lead |
| Migraciones Alembic colisionan en `down_revision` | Alto | Nomenclatura `m_NNN`, rebase ordenado, CI lint del chain | Backend Infra |
| Pricing detailing 4 tiers → 9 tipos NHTSA | Alto | ADR-009 con JSONB `prices_by_type`; mapping default `MPV→medium`, `TRUCK→large`, etc. | API Designer |
| vPIC dump no disponible en CI | Medio | Mock fixture o skip flag `--no-seed-catalog` para CI; full seed sólo en dev/staging | DevOps |
| Frontend mobile no actualiza al renombrar `detailer_id → provider_id` | Medio | Grep `detailer_id` en `frontend/src`; PR coordinado | Frontend Mobile |
| Multi-perfil rompe Profile Hub `provider` block | Medio | Coordinar con sesión paralela el shape (lista vs filtrar por `active_role`) | Tech Lead |
| Combo pricing custom (10%/15%) cambia de regla | Bajo | Aislar en `calculate_combo_price()`; producto confirma reglas antes de seed | Backend Domain |

---

## 8. ADRs nuevos a redactar (durante ejecución)

- **ADR-009**: Pricing de detailing migrado de `VehicleSize` (4 tiers) a `VehicleType` (9 tipos NHTSA) — almacenamiento JSONB con grupos default
- **ADR-010**: `ProviderProfile` 1:N por User+provider_type, con composite unique; cómo encaja en Profile Hub `provider` block
- **ADR-011**: Combos como tabla compartida entre detailing y mecánico, con `ComboItem` polimórfico (service_id XOR addon_id)
- **ADR-012**: vPIC seed pipeline: trigger manual, idempotente, `--dry-run`, batch insert; no se corre en CI

Cada ADR vive en `docs/adrs/` (crear directorio si no existe) y se referencia desde [docs/integration_plans/README.md](docs/integration_plans/README.md).

---

## 9. Definition of Done por épica

Una épica está DONE cuando:

1. ✅ Migraciones aplicadas con round-trip OK
2. ✅ Tests nuevos verdes (unit + integration); cobertura ≥80% del dominio tocado
3. ✅ `mypy` y `ruff` verdes en archivos modificados
4. ✅ OpenAPI regenerado y commiteado si hay endpoints nuevos
5. ✅ Seed script ejecutado en dev y verificado idempotente
6. ✅ Documentación: el archivo `docs/integration_plans/0X-*.md` cierra con `Status: DONE — <date> — <commit-sha>` + changelog de decisiones reales (no las hipótesis del spec)
7. ✅ PR rebased contra master y Tech Lead approved
8. ✅ ADR redactado si la épica generó decisión arquitectural

---

## 10. Próximos pasos inmediatos

1. Tech Lead: abrir issue "Integration Plans coordination" en repo, lista de zonas calientes (sección 3.2), notificar a sesión paralela del `feat/profile-phase4` que multi-profile (E1) debe landearse antes de que Phase 5 arranque.
2. Backend Domain: rama `feat/integrations/00-user-zipcode`, PR pequeño para empezar el flujo con bajo riesgo. Base contra `master`, no contra `feat/profile-phase4` (esa rama tiene chunk W pendiente).
3. DevOps: validar acceso a vPIC dump local; documentar setup en `docs/integration_plans/04-vehicles-runbook.md` antes del Sprint 3.
4. Backend Infra: pre-flight de migraciones — generar `alembic revision --autogenerate` en branch separado para visualizar el diff de modelos sin commitear. La cadena de migraciones de master termina en `m_005b`; las de `feat/profile-phase4` van de `m_006..m_010`. Nuestra E0 (`m_011_user_zipcode`) debe encadenarse después de que `feat/profile-phase4` mergee a master, o anclarse explícitamente a `m_005b` y aceptar rebase posterior.

---

## 11. Recomendación de secuencia con la sesión paralela

Dado que `feat/profile-phase4` está en `m_010` con chunk W (mobile) como único pendiente, y Phases 5–9 aún no arrancan, el orden óptimo es:

1. **Sesión paralela termina chunk W** o pausa Phase 4 (decisión del usuario en su mensaje). Idealmente: mergea `feat/profile-phase4` → master para tener migraciones lineales.
2. **Esta sesión arranca E0 (`00-user.md` zip_code)** sobre master post-merge — riesgo mínimo, valida flujo de coordinación.
3. **E1 (`01-profiles.md` multi-profile)** se prioriza ANTES de que la sesión paralela arranque Phase 5. Esto convierte el riesgo de conflicto en oportunidad: Phase 5 (provider portfolio) construye sobre multi-profile desde el inicio.
4. **E2 (`04-vehicles.md`)** en paralelo con Phase 7 (notifications/privacy) — no se tocan los mismos archivos.
5. **E3 (`02-detailing.md` combos)** y **E4 (`03-mechanic.md` backend)** se ejecutan después, con poco riesgo de colisión con Phases 8/9 (GDPR + polish).

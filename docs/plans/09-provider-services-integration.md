# 09 — Provider Services Integration (Catálogo Configurable)

> **Status:** Planning
> **Priority:** Medium
> **Dependencies:** `plan.md` Phase 5 (provider endpoints exist under `/users/me/`)
> **Audit findings resolved:** H4, H8, M1 (parcial)
> **Modelo:** Catálogo dinámico con variantes — no lista rígida

## 1. Mentalidad

No "tengo car wash, detailing y mecánica". Tengo un sistema que vende **UNIDADES DE SERVICIO configurables**:

```
Servicio = base (services)
         + variantes (service_variants) → pricing por vehículo
         + opciones (service_options)    → addons
         + reglas  (service_rules)      → validaciones
         + customización por provider   → provider_services
```

## 2. Modelo de Datos

### service_categories (organización)
```sql
service_categories (
  id UUID PK,
  name TEXT,          -- "Car Wash", "Detailing", "Mechanic"
  slug TEXT UNIQUE
)
```
✅ Ya existe. Sin cambios.

### services (producto base)
```sql
services (
  id UUID PK,
  category_id UUID FK,
  name TEXT,           -- "Exterior Wash", "Oil Change"
  slug TEXT UNIQUE,
  description TEXT,
  base_price_cents INT,
  base_duration_min INT,
  is_active BOOLEAN
)
```
✅ Ya existe. Sin cambios estructurales.

### service_variants (NUEVO — reemplaza `map_body_to_size`)
```sql
service_variants (
  id UUID PK,
  service_id UUID FK → services.id,
  name TEXT,                -- "Sedan", "SUV", "Truck"
  slug TEXT,                -- "sedan", "suv", "truck"
  price_modifier_cents INT,  -- +0, +1000, +2000
  duration_modifier_min INT, -- +0, +15, +30
  sort_order INT,
  is_active BOOLEAN DEFAULT TRUE
)
```

En runtime: `precio_final = base_price_cents + variant.price_modifier_cents`.

### provider_services (customización por provider)
```sql
provider_services (
  id UUID PK,
  provider_id UUID FK → provider_profiles.id,
  service_id UUID FK → services.id,
  is_active BOOLEAN DEFAULT TRUE,
  custom_price_cents INT NULL,   -- null = precio plataforma
  custom_duration_min INT NULL   -- null = duración plataforma
)
```
Reemplaza `detailer_services` con rename + campo `custom_duration_min` añadido.

### provider_specialties (M:N provider ↔ specialty)
```sql
provider_specialties (
  provider_profile_id UUID FK,
  specialty_id UUID FK,
  added_at TIMESTAMPTZ
)
```
✅ Ya existe como `ProviderSpecialty`. Solo rename de tabla.

### service_options (NUEVO — diferido a Q3 2026)
```sql
service_options (
  id UUID PK,
  service_id UUID FK,
  name TEXT,
  slug TEXT,
  price_cents INT,
  duration_min INT,
  is_required BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE
)

provider_service_options (
  id UUID PK,
  provider_id UUID FK,
  option_id UUID FK,
  custom_price_cents INT NULL
)
```

### service_rules (NUEVO — diferido a Q4 2026+)
```sql
service_rules (
  id UUID PK,
  service_id UUID FK → services.id,
  rule_type TEXT,       -- "requires_option", "vehicle_type_only", "min_year"
  config JSONB
)
```

### service_versions (NUEVO — diferido)
```sql
service_versions (
  id UUID PK,
  service_id UUID FK,
  version INT,
  config JSONB,
  created_at TIMESTAMPTZ
)
```

## 3. Scope

**In scope (Etapas A + B):**
- Migrar `detailer_services` → `provider_services` con rename + campo `custom_duration_min`
- Endpoints `/api/v1/users/me/provider-services` + specialties
- Service layer en `domains/providers/service.py`
- **Nueva tabla `service_variants`** + seed data para detailing
- Reemplazar `map_body_to_size()` por consulta a `service_variants`
- Deprecación del router legacy con headers `Sunset` + `Deprecation`
- Frontend: `ProviderServicesScreen` con toggle, custom price, variantes, specialties
- Frontend: hacer `ProviderHubScreen` reachable
- Tests: `test_users_provider_services.py`

**Out of scope (futuro):**
- `service_options` + `provider_service_options` → Q3 2026
- `service_rules` → Q4 2026+
- `service_versions` → Q4 2026+
- Multi-ciudad → post-expansión
- Multi-profile (1:N) → `01-profiles.md`
- Mechanic vertical → `03-mechanic.md`

## 4. Execution Phases

### Etapa A — Fundación: Migración a Phase 5

| Archivo | Acción |
|---------|--------|
| `domains/providers/models.py` | Renombrar `DetailerService` → `ProviderServiceOffering`, `__tablename__` → `provider_service_offerings` |
| `domains/providers/schemas.py` | Agregar `ProviderServiceOfferingRead`, `ProviderServiceOfferingUpdate`, `ProviderSpecialtyRead`, `ProviderSpecialtiesUpdate` |
| `domains/providers/repository.py` | Agregar `get_provider_services()`, `upsert_service_offering()`, `get_specialties()`, `set_specialties()` |
| `domains/providers/service.py` | Escribir `list_services_with_state()`, `update_service_offering()`, `list_specialties()`, `set_specialties()`, `remove_specialty()` |
| `domains/providers/provider_services_router.py` | **Crear**: `GET /provider-services` + `PATCH /{service_id}` (con EnvelopeRouter) |
| `domains/providers/provider_specialties_router.py` | **Crear**: `GET /provider-specialties` + `PUT` + `DELETE /{specialty_id}` |
| `api/router.py` | Montar ambos routers bajo `/api/v1/users/me/` |
| `domains/providers/router.py` | Agregar headers `Sunset` + `Deprecation` a endpoints legacy |
| Alembic migration | Renombrar tabla `detailer_services` → `provider_service_offerings`, agregar `custom_duration_min` |

### Etapa B — Service Variants (core del modelo escalable)

| Archivo | Acción |
|---------|--------|
| `domains/services_catalog/models.py` | Agregar modelo `ServiceVariant` |
| `domains/services_catalog/schemas.py` | Agregar `ServiceVariantRead` |
| `domains/services_catalog/repository.py` | Agregar `get_variants_for_service()` |
| `infrastructure/nhtsa/` | **Deprecar** `map_body_to_size()` — ya no se usa para pricing |
| `domains/appointments/service.py` | Actualizar cálculo de `estimated_price`: `base_price + variant_modifier` |
| Seed data | Agregar variantes para cada servicio de detailing (sedan, suv, truck) |
| Alembic migration | Crear `service_variants` table |

**Flujo de pricing post-cambio:**
```python
# ANTES (hardcode):
size = map_body_to_size(vehicle.body_class)  # "SUV" → "large"
price = service.base_price_cents * size_multiplier[size]

# DESPUÉS (configurable):
variant = await repo.get_variant(service_id, vehicle.body_class)
price = service.base_price_cents + variant.price_modifier_cents
```

### Etapa C — Frontend

| Archivo | Acción |
|---------|--------|
| `screens/ProviderServicesScreen.tsx` | **Crear**: FlatList de servicios con toggle + custom price inline + variant badges + specialties editables |
| `services/provider-services.service.ts` | **Crear**: `listServices()`, `updateServiceOffering()`, `getSpecialties()`, `setSpecialties()` |
| `hooks/useProviderResources.ts` | Agregar queries: `useServices()`, `useUpdateServiceOffering()`, `useSpecialties()`, `useSetSpecialties()` |
| `navigation/AppNavigator.tsx` | Agregar ruta `ProviderServices` |
| `navigation/types.ts` | Tipar todas las rutas Phase 5 en `RootStackParamList` |
| `screens/ProviderHubScreen.tsx` | Agregar menú "Mis servicios" → `navigation.navigate("ProviderServices")` |
| `screens/ProfileScreen.tsx` | CTA "Modo proveedor" → `ProviderHub` (si rol detailer) |
| `screens/DetailerProfileScreen.tsx` | Botón "Panel de control" → `ProviderHub` |

### Etapa D — Tests

| Archivo | Acción |
|---------|--------|
| `tests/test_users_provider_services.py` | **Crear**: ~12 tests |
| | Listar servicios sin profile → 404 |
| | Listar con profile → 200 + lista |
| | Toggle on/off → 200 |
| | Custom price válido → 200 |
| | Custom price negativo → 422 |
| | `custom_duration_min` se persiste |
| | Specialty CRUD |
| | Cross-user isolation |
| | Variant pricing en appointment creation |

## 5. Verification

- [ ] `GET /users/me/provider-services` retorna `Envelope[ProviderServiceOfferingRead]`
- [ ] `PATCH /users/me/provider-services/{id}` actualiza `is_active`, `custom_price_cents`, `custom_duration_min`
- [ ] `custom_price_cents: null` usa precio plataforma
- [ ] `GET /users/me/provider-specialties` retorna specialties
- [ ] `PUT /users/me/provider-specialties` reemplaza specialties (batch)
- [ ] `POST /appointments` calcula `estimated_price` con variante (`base_price + modifier`)
- [ ] `map_body_to_size()` ya no se llama desde appointment creation
- [ ] Legacy `/detailers/me/services*` responde con headers `Sunset` + `Deprecation`
- [ ] `ProviderServicesScreen` monta FlatList con data real
- [ ] `ProviderHub` reachable desde `ProfileScreen` y `DetailerProfileScreen`
- [ ] `RootStackParamList` tipado completo
- [ ] `test_users_provider_services.py` pasa 12/12
- [ ] `test_users_provider_profile.py` y `test_appointments.py` no se rompen

## 6. Risks

| Riesgo | Mitigación |
|--------|------------|
| Renombrar `DetailerService` rompe imports | Usar alias en Python + mantener backward compat temporal |
| Cambiar cálculo de `estimated_price` altera precios existentes | Versionar: appointments nuevos usan variant, viejos preservan su `estimated_price` inmutable |
| `map_body_to_size()` referenciada en otros lugares | Deprecar con decorador `@deprecated` + audit trail de llamadas |
| Seed data de variantes incompleta para servicios existentes | Script one-off que genera variantes default (sedan:+0) para cada servicio |
| ProviderHub duplica `DetailerProfileScreen` | Aceptar dualidad temporal. Se unifica en Phase 6 (role switcher) |

## 7. Secuencia Recomendada

```
Semana 1: Etapa A — Migración Phase 5 + rename + specialties
Semana 2: Etapa B — Service variants + pricing engine
Semana 3: Etapa C — Frontend (ProviderServicesScreen + wiring)
Semana 4: Etapa D — Tests + compliance + fix bugs
         ↓
Q3 2026: service_options + provider_service_options
Q4 2026: service_rules + service_versions (si demanda lo justifica)
```

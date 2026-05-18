# Database Schema Analysis — Naming, Types & Standards

> **Date**: 2026-05-17
> **Scope**: All 28 SQLAlchemy tables across 17 model files
> **Reviewer**: DB Architect perspective

---

## 1. Table Naming Conventions

### 1.1 Plural vs Singular — Inconsistencia

La convención del proyecto es **plural** para nombres de tabla, pero hay 3 excepciones:

| Table | Convention | Fix |
|-------|-----------|-----|
| `payment_ledger` | ❌ Singular | → `payment_ledger_entries` |
| `user_login_history` | ❌ Singular | → `login_history` o `user_login_records` |
| Todas las demás (28 tables) | ✅ Plural | — |

### 1.2 Tablas Compuestas — Plural Consistente ✅

| Table | Pattern |
|-------|---------|
| `role_permissions` | `{plural}_{plural}` ✅ |
| `user_roles` | `{plural}_{plural}` ✅ |
| `provider_specialties` | `{plural}_{plural}` ✅ |
| `appointment_vehicles` | `{plural}_{plural}` ✅ |
| `appointment_addons` | `{plural}_{plural}` ✅ |
| `appointment_assignments` | `{plural}_{plural}` ✅ |
| `detailer_services` | `{plural}_{plural}` ✅ |

Bien: todas las tablas compuestas (join tables) siguen el patrón `{plural}_{plural}`.

---

## 2. Column Naming — Problemas Principales

### 2.1 🔴 `estimated_price` / `actual_price` sin sufijo `_cents`

**El proyecto entero** usa el sufijo `_cents` para todas las columnas monetarias:

| Column | Suffix | File |
|--------|--------|------|
| `base_price_cents` | ✅ `_cents` | `services`, `fare_estimates` |
| `price_cents` | ✅ `_cents` | `addons`, `appointment_vehicles`, `appointment_addons` |
| `amount_cents` | ✅ `_cents` | `payment_ledger`, `ledger_seals` |
| `total_spent_cents` | ✅ `_cents` | `client_profiles` |
| `earnings_lifetime_cents` | ✅ `_cents` | `provider_profiles` |
| `estimated_price` | ❌ **No suffix** | `appointments` |
| `actual_price` | ❌ **No suffix** | `appointments` |

**El schema de AppointmentRead ya tiene el workaround**:
```python
estimated_price_cents: int = Field(alias="estimated_price")  # ← workaround
actual_price_cents: int | None = Field(default=None, alias="actual_price")
```

**Impacto**: La DB dice una cosa, la API dice otra. Cualquier query SQL directa requiere recordar qué columnas tienen `_cents` y cuáles no. `AppointmentRead` mapea `estimated_price_cents` (schema) → `estimated_price` (DB).

### 2.2 Columnas `Integer` para montos — Riesgo de Overflow

| Table | Column | Current Type | Max (cents) | Max (USD) | Risk |
|-------|--------|-------------|-------------|-----------|------|
| `appointments` | `estimated_price` | `Integer` | 2.147B | $21.4M | Medio — agregados en reports |
| `appointments` | `actual_price` | `Integer` | 2.147B | $21.4M | Medio |
| `payment_ledger` | `amount_cents` | `Integer` | 2.147B | $21.4M | **Alto** — SUM en ledger |
| `ledger_seals` | `total_amount_cents` | `Integer` | 2.147B | $21.4M | **Alto** — SUM diario |
| `client_profiles` | `total_spent_cents` | `BigInteger` | Ilimitado | Ilimitado | ✅ |
| `provider_profiles` | `earnings_lifetime_cents` | `BigInteger` | Ilimitado | Ilimitado | ✅ |

**`Integer` en PostgreSQL es 32-bit signed = 2,147,483,647 (~$21.4M en cents).** Con un marketplace en crecimiento, SUM en ledger puede exceder esto en reports mensuales.

### 2.3 `average_rating` — `Numeric(3,2)` demasiado ajustado

```sql
average_rating NUMERIC(3,2)  -- rango: -9.99 a 9.99
```

Para rating 1-5 es funcional, pero si se agregan promedios compuestos podría exceder. **Recomendación: `Numeric(4,2)`** (rango -99.99 a 99.99) para safety.

---

## 3. Tipos de Datos — Inconsistencias

### 3.1 PG ENUM vs String para Tipos Fijos

| Ubicación | Tipo Actual | Método |
|-----------|-----------|--------|
| `appointments.status` | `AppointmentStatus` | **PG ENUM** ✅ |
| `vehicles.vehicle_size` | `VehicleSize` (en appointment_vehicles) | **PG ENUM** ✅ |
| `services.category` | `ServiceCategory` | **PG ENUM** ✅ |
| `device_tokens.platform` | `DevicePlatform` | **PG ENUM** ✅ |
| `audit_logs.action` | `AuditAction` | **String(50)** ❌ |
| `pending_contact_changes.change_type` | `ContactChangeType` | **String(10)** ❌ |
| `appointment_assignments.status` | `AssignmentStatus` | **String(20)** ❌ |
| `payment_ledger.entry_type` | String literal | **String(30)** ❌ |

**Problema**: PG ENUM requiere migración ALTER TYPE para añadir nuevos valores (transaction bloqueante). String permite datos inválidos silenciosamente.

**Recomendación**: Unificar a `String` con `CheckConstraint` para flexibilidad + validación.

### 3.2 `now()` sin Timezone en `ProviderSpecialty.added_at`

```python
# services_catalog/models.py:130
server_default=sa_text("now()")  # ← Sin timezone!
```

vs el resto del proyecto que usa `DateTime(timezone=True)` con `default=lambda: datetime.now(timezone.utc)`.

**Impacto**: `now()` devuelve timestamp naive (sin timezone). La columna es `DateTime(timezone=True)`, lo que causa un mismatch.

### 3.3 `FareEstimate` — `Numeric(9,6)` para lat/lng pero Python type mismatch

```python
# paymnts/models.py
client_lat: Mapped[Decimal] = mapped_column(Numeric(9, 6), ...)  # Decimal
# appointments/models.py
service_latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), ...)  # float
```

Mismo tipo DB (`Numeric(9,6)`), pero uno mapea a `Decimal` y otro a `float` en Python. **Consistencia**: usar `Decimal` para ambos o `float` para ambos.

---

## 4. Soft Deletes — Patrón Inconsistente

### 4.1 `TimestampMixin` vs Duplicación Manual

| Model | Uses `TimestampMixin`? | Has `is_deleted`? |
|-------|----------------------|-------------------|
| `User` | ✅ | ✅ (via mixin) |
| `Vehicle` | ✅ | ✅ (via mixin) |
| `Appointment` | ✅ | ✅ (via mixin) |
| `ClientProfile` | ✅ | ✅ (via mixin) |
| `ProviderProfile` | ✅ | ✅ (via mixin) |
| `UserAddress` | ✅ (`TimestampMixin`) | ✅ **inline** (duplicado) |
| `PaymentMethod` | ✅ (`TimestampMixin`) | ✅ **inline** (duplicado) |
| `ClientFavorite` | ❌ (solo `Base`) | ❌ |
| `VehiclePhoto` | ❌ (solo `Base`) | ❌ |
| `PendingContactChange` | ❌ (solo `Base`) | ❌ |

`UserAddress` y `PaymentMethod` heredan `TimestampMixin` **pero también declaran `is_deleted` y `deleted_at` inline**. El mixin ya provee esos campos — están duplicados.

### 4.2 Tablas sin Soft Delete (Intencional)

| Model | Reason |
|-------|--------|
| `RefreshToken` | Rotación — hard delete de expired |
| `PasswordResetToken` | Single-use — hard delete tras uso |
| `EmailVerificationToken` | Single-use — hard delete tras uso |
| `PaymentLedger` | Append-only financiero |
| `ProcessedWebhook` | Idempotencia — nunca se borra |
| `AuditLog` | Append-only por compliance |
| `ClientFavorite` | No necesita — delete directo |
| `VehiclePhoto` | No necesita — cascade con Vehicle |

Estos son correctos — no todas las entidades necesitan soft delete.

---

## 5. Foreign Keys — Análisis

### 5.1 `ondelete` Patterns

| Action | Usage | Correct? |
|--------|-------|----------|
| `CASCADE` | Dependencias de ciclo de vida (user→roles, appointment→vehicles) | ✅ |
| `RESTRICT` | Protección de datos financieros (appointment→user, payment→appointment) | ✅ |
| `SET NULL` | Relaciones opcionales (user→address, role→assigned_by) | ✅ |

### 5.2 Faltantes / Issues

| Issue | Location | Detail |
|-------|----------|--------|
| `ClientProfile.default_address_id` sin FK constraint | `users/models.py:42-44` | Comentario: "without constraint for now" — pero m_010 ya existe |
| `Appointment.service_id` usa `ondelete="RESTRICT"` | `appointments/models.py:91` | Si un servicio se desactiva, no se puede eliminar por appointments activos. Correcto. |

---

## 6. Columnas Deprecadas / Muertas

| Table | Column | Status | Desde |
|-------|--------|--------|-------|
| `client_profiles` | `service_address` | ❌ Deprecated | Phase 4 |
| `client_profiles` | `total_appointments_count` | ⏳ No implementado | Phase 9 (m_020 triggers) |
| `client_profiles` | `total_spent_cents` | ⏳ No implementado | Phase 9 |
| `appointments` | `vehicle_id` | ⏳ Legacy single-vehicle | Nunca marcado deprecado |
| `appointments` | `service_id` | ⏳ Legacy single-service | Nunca marcado deprecado |

---

## 7. Buenas Prácticas Confirmadas ✅

| Practice | Evidence |
|----------|----------|
| UUID como PK en todas las tablas | ✅ 28/28 tablas |
| `DateTime(timezone=True)` en timestamps | ✅ 100% de columnas datetime |
| `snake_case` consistente en columnas | ✅ 100% |
| `ondelete` explícito en FK | ✅ 100% de FK |
| `comment=` en columnas no obvias | ✅ AuditAction, Review.detailer_id, etc. |
| `__repr__` en todos los modelos | ✅ 100% |
| `server_default` en contadores | ✅ total_appointments_count, response_rate, etc. |
| `metadata_` workaround para Python builtin | ✅ PaymentLedger, AuditLog |
| EncryptedType para PII | ✅ full_name, phone_number, tax_id, insurance |

---

## 8. Summary — Plan de Acción

| Priority | Task | Tables | Effort |
|----------|------|--------|--------|
| **P0** | Renombrar `estimated_price` → `estimated_price_cents`, `actual_price` → `actual_price_cents` | `appointments` + schema + service | Medium |
| **P0** | Migrar `Integer` → `BigInteger` en columnas de cents | `appointments`, `payment_ledger`, `ledger_seals` | Medium |
| **P1** | Expandir `average_rating` → `Numeric(4,2)` | `provider_profiles` | Low |
| **P1** | Renombrar `payment_ledger` → `payment_ledger_entries` | Ledger + service + schema | Medium |
| **P1** | Renombrar `user_login_history` → `login_records` | Auth + service + schema | Low |
| **P1** | Unificar PG ENUM → String + CheckConstraint | Audit, Payments, Appointments | High |
| **P1** | Eliminar `is_deleted`/`deleted_at` duplicados de `UserAddress`, `PaymentMethod` | `user_addresses`, `payment_methods` | Low |
| **P1** | Agregar `default` a `ClientFavorite.created_at` | `client_favorites` | Low |
| **P1** | Fix `ProviderSpecialty.added_at` timezone | `provider_specialties` | Low |
| **P2** | Eliminar columnas deprecadas de `ClientProfile` | `client_profiles` | Low |
| **P2** | Agregar FK constraint a `default_address_id` | `client_profiles` | Low |
| **P2** | Marcar `Appointment.vehicle_id` como deprecado | `appointments` | Low |
| **P3** | Normalizar `working_hours` JSONB → tabla separada | `provider_profiles` | High |

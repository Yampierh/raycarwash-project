# Cross-Reference Audit & Canonical Standards

> **Date**: 2026-05-17
> **Purpose**: Detect contradictions across audit findings, define coherent team standards
> **Files analyzed**: 01 through 05 in `docs/audit/`

---

## 1. Contradictions Detectadas

### C1 — VehicleSize: ¿Violación o Snapshot Permitido?

| Source | Dice | File |
|--------|------|------|
| Audit 01 (§3) | "violates business rule — never store VehicleSize" | 🔴 |
| Audit 05 (§3.1) | Lo lista como PG ENUM ✅ (práctica establecida) | 🟢 |

**Resolución**: `appointment_vehicles.vehicle_size` es un **snapshot de auditoría** del tamaño al momento de la reserva (el precio depende del tamaño en booking time, no del tamaño actual del vehículo). Actualizar AGENTS.md para permitir snapshot columns con comentario explícito.

### C2 — Envelope[T] Rompe Web Admin Login

| Source | Dice | File |
|--------|------|------|
| Audit 01 (§11) | P1 — Migrar todos los routers legacy a EnvelopeRouter | 🔴 |
| Audit 04 (§1.2) | Web login lee `res.data` directamente, no unwrap | 🔴 |

**Resolución**: NO se puede enforce Envelope en `/auth/*` endpoints sin arreglar web login primero. **Solución**: Eximir `/auth/*` de Envelope (no están bajo `/api/v1`). El CI check de EnvelopeRouter debe scoping por prefix. Web login debe añadir interceptor, pero no está bloqueado.

### C3 — Misma Issue, Distinta Prioridad (NHTSA → Domain Import)

| Source | Priority | File |
|--------|----------|------|
| Audit 01 (§6) | **P1** | |
| Audit 03 (§4.3) | **P0** | |

**Resolución**: Es P0 (bloquea infraestructura limpia). Unificar prioridad.

### C4 — PG ENUM: Aprobado ✅ pero Recomiendan Reemplazo ❌

Dentro del mismo archivo 05:
- Tabla §3.1: `appointments.status` → PG ENUM ✅
- Recomendación §3.1: "Unificar a String + CheckConstraint"

**Resolución**: Decisión de estándar: **PG ENUM para tipos fijos pequeños (2-10 valores). String + CheckConstraint para enums grandes o evolutivos (AuditAction 30+ valores).** Ver §4 abajo.

### C5 — `estimated_price` Rename Impacta Regla de Negocio Inmutable

| Source | Dice | File |
|--------|------|------|
| Audit 05 (§2.1) | P0 — Renombrar a `estimated_price_cents` | |
| AGENTS.md | `estimated_price` es inmutable | |

**Resolución**: El rename es correcto pero de alto impacto. Debe hacerse en UNA migración que incluya: columna DB → schemas → services → tests → AGENTS.md.

---

## 2. Hallazgos Duplicados (Merge Recomendado)

| Hallazgo | Aparece en | Debe vivir en |
|----------|-----------|---------------|
| NHTSA import de domain | 01 (§6), 03 (§4.3) | 03-infrastructure (archivo natural) |
| FSM transiciones faltantes | 01 (§12), 02 (§2.2) | 01-architecture (source of truth) |
| Missing repos (Payments, Matching) | 01 (§1.1/1.2), 01 (§13) | Unificar en §1 |
| `db.commit()` fuera de service layer | 01 (§1.2), 03 (§5.1) | 01-architecture with cross-ref |
| Timezone-naive datetimes | 01 (§10), 05 (§3.2/§11) | 05-db-schema (central) |

---

## 3. Dependency Graph

```
Phase 0 — Sin dependencias (inmediato):
  ├── pool_pre_ping + create_all guard   (03:§1.1/1.2)
  ├── RBAC write:permissions fix          (01:§5)
  ├── Encryption key startup validation   (03:§1.3)
  └── TimestampMixin dedup                (05:§4.1)

Phase 1A — Web login (BLOQUEANTE para 1B):
  └── Envelope unwrap en web login        (04:§1.2)
      ↓
Phase 1B — Envelope roll-out (BLOQUEADO por 1A):
  └── Migrar routers legacy               (01:§11)
      ├── Eximir /auth/* del check
      └── Scope CI test a /api/v1/

Phase 2 — Service Layer Reorg:
  ├── AdminService (extraer de AdminRepo) (01:§2)
  ├── PaymentsRepository (extraer SQL)    (01:§1.1)
  ├── MatchingRepository (extraer SQL)   (01:§1.2)
  ├── VehicleSize → shared/              (01:§6 / 03:§4.3)
  └── H3 db.commit() → service           (03:§5.1)

Phase 3 — DB Migrations (una tanda):
  ├── estimated_price → estimated_price_cents (05:§2.1)
  ├── Integer → BigInteger columns        (05:§2.2)
  ├── Rename payment_ledger               (05:§1.1)
  ├── Rename user_login_history           (05:§1.1)
  ├── Drop deprecated columns             (05:§6)
  └── Remove duplicate is_deleted cols    (05:§4.1)

Phase 4 — Tests (código estable):
  ├── Reembolsos, double-booking, audit   (02:§1.1/1.2/1.3)
  ├── FSM restantes, WebSocket, failure   (02:§2)
  └── Sprint 9 admin tests                (02:§2.3)

Phase 5 — Infra hardening:
  ├── Redis pool config + timeouts        (03:§2)
  ├── SMTP retry                          (03:§3)
  ├── NHTSA retry + shared client         (03:§4)
  └── Seed functions env flag             (03:§9.2)

Phase 6 — Largo plazo:
  ├── Enums: PG ENUM vs String decision   (05:§3.1)
  ├── Server-side auth web                (04:§1.4)
  └── Docker compose backend service      (04:§4.4)
```

---

## 4. Canonical Standards Propuestos

### 4.1 DB Naming Standards

| Elemento | Estándar | Excepciones |
|----------|----------|-------------|
| Table names | `snake_case` plural | `payment_ledger` → `payment_ledger_entries` |
| FK columns | `{table_singular}_id` (`user_id`, `appointment_id`) | `client_favorites.provider_user_id` (unique FK name for clarity) |
| Money columns | `{descriptor}_cents` (`estimated_price_cents`) | `estimated_price`/`actual_price` → migrar |
| Boolean columns | `is_` prefix (`is_active`, `is_deleted`) | — |
| Timestamps | `DateTime(timezone=True)` + `default=_utcnow` | — |
| Primary keys | `UUID(as_uuid=True)` | — |
| Soft delete | Via `TimestampMixin` (nunca inline) | Tablas append-only (AuditLog, PaymentLedger) |

### 4.2 DB Type Standards

| Uso | Tipo | Razón |
|-----|------|-------|
| Enums fijos (2-10 valores) | **PG ENUM** | Validación forzada en DB |
| Enums grandes/evolutivos (10+) | **String + CheckConstraint** | ALTER TYPE es bloqueante |
| Montos monetarios | **BigInteger** (no Integer) | Overflow seguro en aggregates |
| Coordenadas | `Numeric(9,6)` + Python `Decimal` | Precisión ~10cm |
| PII | `EncryptedType(String(N))` | Cifrado en reposo |

### 4.3 Architecture Standards

| Capa | Responsabilidad | Prohibido |
|------|----------------|-----------|
| **Repository** | Solo data access: CRUD, filtering, pagination | Lógica de negocio, audit writes, FSM |
| **Service** | Lógica de negocio, orquestación, audit logging | Raw SQL (`select()`, `update()`), `db.commit()` |
| **Router (v1)** | Parse request, formato response, `Depends()` | SQLAlchemy imports, DB access directo |
| **Infrastructure** | Integraciones externas (Stripe, NHTSA, Redis) | `from domains.*`, `db.commit()` |
| **shared/** | Enums inter-dominio, constants, schemas base | Lógica de negocio, DB access |

### 4.4 Schema Naming Standards

| Tipo | Patrón | Ejemplo |
|------|--------|---------|
| Response | `{Entity}Read` | `AppointmentRead`, `UserRead` |
| Request create | `{Entity}Create` | `AppointmentCreate` |
| Request update | `{Entity}Update` | `UserUpdate` |
| Paginated | `PaginatedEnvelope[{Entity}Read]` | — |
| Private nested | `_{Entity}Info` | `_ClientInfo`, `_DetailerBrief` |
| Base response | `_BaseSchema` con `from_attributes=True` | — |
| Base request | `_BaseRequestSchema` sin `from_attributes` | — |

### 4.5 Business Rule Clarification (Resuelve C1)

**Regla actual (AGENTS.md)**: *"VehicleSize is runtime-derived via `map_body_to_size(body_class)`. Never stored — do NOT add a size column."*

**Regla propuesta**: *"VehicleSize is runtime-derived via `map_body_to_size(body_class)`. Never add a `size` column to the `vehicles` table. Snapshot columns in join/history tables (e.g., `appointment_vehicles.vehicle_size`) are ALLOWED with a comment explaining they are audit snapshots at booking time, NOT the current vehicle size."*

### 4.6 Envelope Scope (Resuelve C2)

| Prefix | Enforce Envelope? | Reason |
|--------|------------------|--------|
| `/api/v1/*` | ✅ **Sí** — CI test obligatorio | Estándar API |
| `/auth/*` | ❌ **No** — exento | Web login sin unwrap |
| `/ws/*` | N/A | WebSocket, no REST |
| `/.well-known/*` | ❌ No | JWKS endpoint público |
| `/webhooks/*` | ❌ No | Stripe webhooks raw |

---

## 5. Resumen de Acciones para Coherencia

| Archivo | Acción Necesaria |
|---------|-----------------|
| `AGENTS.md` | Actualizar regla VehicleSize (snapshot permitido) |
| `AGENTS.md` | Agregar que `/auth/*` está exento de Envelope |
| `01-architecture-violations.md` | Mover NHTSA issue a infra audit (cross-ref) |
| `01-architecture-violations.md` | Unificar missing repos con SQL en services |
| `02-test-gaps.md` | Referenciar FSM transitions desde architecture audit |
| `04-web-frontend-issues.md` | Agregar server-side auth como P1 |
| `05-db-schema-analysis.md` | Resolver contradicción PG ENUM ✅ vs ❌ |
| `05-db-schema-analysis.md` | Agregar cross-ref a `datetime.utcnow()` en VehicleRepo |
| `SUMMARY.md` | Reorganizar prioridades según dependency graph |

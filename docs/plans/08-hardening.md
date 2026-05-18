# 08 — Hardening: Fixes Criticos del Audit

> **Status:** Draft
> **Priority:** Critical
> **Dependencies:** None (ejecutable inmediatamente)
> **Audit findings resolved:** C1–C7, H1–H15, M1–M10 (ver seccion 2)
> **Unblocks:** `00-user.md`, `01-profiles.md`, `02-detailing.md`, `03-mechanic.md`, `04-vehicles.md`, `05-ci-cd.md`

## 1. Objective

Resolver los 7 hallazgos CRITICAL y 15 HIGH del audit tecnico (`docs/audit/`) antes de cualquier otro trabajo de producto. Estos son bugs y vulnerabilidades que pueden causar perdida financiera, breach de seguridad o caida en produccion. **NINGUN plan de integracion debe ejecutarse hasta que Hardening Phase 0 este completo.**

## 2. Audit Findings Map

### Phase 0 — Inmediatos (sin dependencias)

| ID | Finding | File | Fix |
|----|---------|------|-----|
| C3 | `write:permissions` en role `client` | `app/db/seed_rbac.py:75` | Eliminar permiso |
| C4 | No `pool_pre_ping` en DB engine | `infrastructure/db/session.py` | Agregar `pool_pre_ping=True` |
| H1 | `create_all` sin guard de entorno | `backend/main.py:94-96` | Envolver en `if settings.RAYCARWASH_ENV == "development"` |
| H5 | `AdminRepository` contiene business logic | `domains/admin/repository.py` | Extraer `AdminService` |
| H3 | No Redis connection pool config | `infrastructure/redis/client.py:18` | Agregar `max_connections`, `socket_timeout` |
| M10 | `map_body_to_size` ubicacion incorrecta | `infrastructure/nhtsa/client.py:14` | Mover a `shared/` |
| M3 | `datetime.utcnow()` naive | `vehicles/repository.py:48` | Reemplazar con `datetime.now(timezone.utc)` |
| H6 | Pricing constants en seed.py | `app/db/seed.py:23` | Mover a `shared/constants.py` |

### Phase 1A — Web Login (bloqueante para 1B)

| ID | Finding | File | Fix |
|----|---------|------|-----|
| H14 | Web login no unwraps envelope | `web/lib/api.ts:79` | Agregar `unwrap()` interceptor |

### Phase 1B — Envelope Roll-out (bloqueado por 1A)

| ID | Finding | File | Fix |
|----|---------|------|-----|
| M1 | Non-compliant routers (7 legacy) | Multiples routers | Migrar a `EnvelopeRouter` |

### Phase 2 — Service Layer Reorg

| ID | Finding | File | Fix |
|----|---------|------|-----|
| C1 | PaymentService inline SQL | `domains/payments/service.py` | Crear `PaymentsRepository` |
| C2 | MatchingService inline SQL + `db.commit()` | `domains/matching/service.py` | Crear `MatchingRepository` |
| C7 | Zero audit logging tests | — | Agregar tests de compliance |
| M4 | Missing `ClientProfileRepository` | — | Crear repositorio |
| M6 | `db.commit()` en infraestructura H3 | `infrastructure/h3/client.py:90` | Mover a service layer |
| M7 | Cross-domain direct coupling | reviews->providers | Reemplazar con EventBus |

### Phase 3 — DB Migrations

| ID | Finding | Migracion Requerida |
|----|---------|---------------------|
| C5/M20 | `estimated_price`/`actual_price` sin sufijo `_cents` | Renombrar columnas en `appointments` |
| H7 | `Integer` -> `BigInteger` en columnas monetarias | Varias tablas |
| — | Duplicados `is_deleted` en `UserAddress`, `PaymentMethod` | Eliminar columnas duplicadas |

### Phase 4 — Tests

| ID | Finding | Coverage Required |
|----|---------|-------------------|
| C5 | Zero tests cancellation refund | 6+ test cases (tiered refund, auth void, captured) |
| C6 | Zero tests double-booking | 4+ test cases (lock key, overlap, concurrency) |
| H9 | Zero WebSocket integration tests | Connection, heartbeat, close codes |
| H10 | 11/18 FSM transitions untested | Tests por transicion faltante |
| H11 | Zero failure mode tests | Stripe/DB/NHTSA failure scenarios |
| H12 | Sprint 9 admin zero tests | Admin appointments, verifications, payments |

## 3. Execution Order

```
Semana 1: Phase 0 (8 fixes, sin dependencias)
  +-- pool_pre_ping, create_all guard
  +-- write:permissions fix
  +-- Redis pool config
  +-- seed.py constants -> shared/
  +-- datetime.utcnow() fix
  +-- VehicleSize -> shared/
  +-- Encryption key startup validation

Semana 2: Phase 1A -> 1B (secuencial)
  +-- Web login envelope unwrap
  `-- EnvelopeRouter en routers legacy

Semana 3: Phase 2 (Service Layer)
  +-- AdminService
  +-- PaymentsRepository + MatchingRepository
  +-- H3 db.commit() fix
  `-- EventBus for cross-domain

Semana 4: Phase 3 (DB Migrations)
  +-- Rename estimated_price -> estimated_price_cents
  +-- Integer -> BigInteger
  +-- BigDecimal for average_rating
  `-- Remove duplicated columns

Semana 5: Phase 4 (Tests)
  +-- Refund logic tests
  +-- Double-booking tests
  +-- FSM transition coverage
  +-- WebSocket integration tests
  +-- Failure mode tests
  `-- Admin extension tests
```

## 4. Verification

Cada fix incluye:
- [ ] Test que reproduce el bug (si era untested)
- [ ] Fix implementado
- [ ] `mypy` + `ruff` verde
- [ ] Tests existentes siguen pasando
- [ ] Alembic upgrade/downgrade round-trip (si es migration)

## 5. Risks

| Risk | Mitigation |
|------|-----------|
| Renombrar columnas DB rompe queries existentes | Una migracion atomica con todos los call-sites actualizados |
| EnvelopeRouter rompe frontends | Eximir `/auth/*` del enforcement |
| Service layer reorg introduce bugs | Tests de integracion por cada repositorio nuevo |

## 6. Dependent Plans

Hardening es un **prerrequisito obligatorio** para los planes de integracion vertical y operacionales:

| Plan | Dependencia | Razon |
|------|-------------|-------|
| `00-user.md` (E0) | Hardening Phase 0 completa | El modelo `User` necesita `pool_pre_ping`, `RBAC fix`, y `create_all` guard antes de agregar `zip_code` |
| `01-profiles.md` (E1) | Hardening Phase 0-2 completas | `ProviderProfile` 1:N requiere Service Layer estable (AdminService, repos ausentes) |
| `02-detailing.md` (E2) | Hardening Phase 0 + 4 completas | Combos requieren AppointmentService sin SQL inline + tests de FSM completos |
| `03-mechanic.md` (E3) | Hardening Phase 0-4 completas | Vertical nuevo necesita infraestructura solida desde el dia 1 |
| `04-vehicles.md` (E4) | Hardening Phase 0 + 3 completas | Refactor de `Vehicle` colisiona con DB migrations de hardening |
| `05-ci-cd.md` | Hardening Phase 0 completa | Pipeline CI/CD necesita codigo estable (tests verdes, lint sin errores) |

### Orden de ejecucion global

```
SEMANA 1-2: 08-hardening Phases 0-1 (cimientos)
  +-- pool_pre_ping, RBAC, create_all, Redis config
  +-- Envelope compliance
  |
  +-- EN PARALELO: 05-ci-cd.md (CI basico corre sobre lo existente)
  |
  V
SEMANA 3-5: Integration Plans (E0-E4)
  +-- 00-user.md (zip_code - 3 dias)
  +-- 01-profiles.md (multi-profile - 6 dias)
  +-- 04-vehicles.md (vehicle catalog - 8 dias)
  +-- 02-detailing.md (combos - 5 dias)
  +-- 03-mechanic.md (backend - 5 dias)
  |
  +-- EN PARALELO: 08-hardening Phases 2-4 (continuan)
  +-- EN PARALELO: 06-infrastructure.md (si CI/CD listo)
  |
  V
SEMANA 6+: 07-observability.md
```

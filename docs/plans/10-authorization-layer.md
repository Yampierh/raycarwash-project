# 10 — Authorization Layer: Enforcement Unificado

> **Status:** Planning
> **Priority:** High
> **Dependencies:** `08-hardening.md` Phase 0 (C3 fix: `write:permissions` en client role)
> **Audit findings resolved:** Enforcement inconsistente (ver sección 2)
> **Unblocks:** `01-profiles.md` (multi-role), ABAC futuro, OPA futuro

## 1. Diagnóstico

El sistema actual tiene un **modelo RBAC completo** pero **enforcement fragmentado**:

| Estado | Detalle | Archivo |
|--------|---------|---------|
| ✅ `require_role()` central | 35 endpoints protegidos | `auth/service.py:854` |
| ✅ `has_permission()` implementado | Recorre roles → permisos | `users/models.py:223` |
| ✅ Permisos seedeados en DB | 18 permisos en `permissions` table | `seed_rbac.py` |
| ❌ **`require_permission()` no existe** | `has_permission()` nunca se llama desde un `Depends()` | Gap |
| ❌ Checks inline | 8 ocurrencias de `is_admin()` / `is_detailer()` en routers y services | `appointments/router.py`, `providers/router.py`, `avatar_router.py`, `realtime/router.py`, `appointments/service.py` |
| ❌ Ownership mezclado con RBAC | Lógica de "quién puede ver este booking" embedded en handlers | `appointments/router.py:254-315` |

**Problema raíz:** El modelo de autorización existe como **datos**, no como **sistema** — los permisos están en DB pero el enforcement no los consume.

## 2. Scope

**In scope:**
- Crear `require_permission(action, resource)` como FastAPI `Depends()` sobre `User.has_permission()` existente
- Crear `OwnershipChecker` como ABAC-lite separado del permission engine
- Reemplazar 8 ocurrencias de `is_admin()` / `is_detailer()` inline por el nuevo sistema
- Migración progresiva de `require_role()` a `require_permission()` sin romper endpoints existentes
- Tests de permisos y ownership (compliance obligatorio)
- Documentar el *enforcement contract*: cero lógica de permisos inline

**Out of scope:**
- OPA — se evaluará post-ABAC si la complejidad de reglas lo justifica
- Refactor del modelo de datos (roles, permissions, user_role_associations se mantienen)
- Cambios en JWT (RS256, claims, token_version se mantienen)
- Middleware de auth — todo via `Depends()` (ver hallazgo L14 del audit)

## 3. Arquitectura

```
require_permission("write", "appointments")   ← nuevo Depends()
         │
         ▼
User.has_permission("write:appointments")     ← existe en users/models.py:223
         │
         ▼
user_roles → role_permissions → permissions   ← modelo existente

--- separado ---

OwnershipChecker.enforce_booking_access(user, booking)   ← ABAC-lite
```

No se crean archivos nuevos — `require_permission()` y `OwnershipChecker` viven en `domains/auth/service.py` junto a `require_role()` y `get_current_user()`.

## 4. Execution Phases

### Fase 1 — require_permission() dependency (1 día)

1. Agregar `require_permission(action: str, resource: str)` en `auth/service.py`
   - Factory function que retorna un `Depends()` llamando a `User.has_permission()`
   - Admin bypass explícito: `user.is_admin()` → allow (mantiene compatibilidad)

2. Agregar tests unitarios de compliance:
   - `test_client_cannot_write_appointments`: cliente con solo `read:appointments` → 403
   - `test_admin_bypass`: admin pasa cualquier permiso
   - `test_detailer_can_write_appointments`: detailer con permiso → 200
   - `test_missing_permission`: usuario sin permiso → 403

**Código:**
```python
def require_permission(action: str, resource: str):
    permission_name = f"{action}:{resource}"

    async def _dep(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.is_admin():
            return current_user
        if not current_user.has_permission(permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission_name}",
            )
        return current_user

    return _dep
```

### Fase 2 — OwnershipChecker (1 día)

1. Agregar `OwnershipChecker` class en `auth/service.py` con métodos estáticos:
   - `can_access_booking(user, booking) → bool`
   - `can_access_payment(user, payment) → bool` (cuando exista el repo)
   - `enforce_booking_access(user, booking)` → raise 403 si no tiene acceso

2. Reglas de ownership:
   - Admin → acceso total
   - Client → solo si `booking.customer_id == user.id`
   - Detailer → solo si `booking.provider_id == user.id`

3. Tests de ownership:
   - `test_client_cannot_access_other_booking`
   - `test_detailer_cannot_access_unassigned_booking`
   - `test_admin_any_booking`

### Fase 3 — Reemplazar inline checks (2 días)

Migrar 8 ocurrencias de `is_admin()` / `is_detailer()`:

| Archivo | Línea | Reemplazo |
|---------|-------|-----------|
| `appointments/router.py:254` | `is_detailer()` | `require_role("detailer")` |
| `appointments/router.py:262` | `is_detailer()` | `OwnershipChecker + require_role` |
| `appointments/router.py:315` | `is_admin()` | `OwnershipChecker.enforce_booking_access` |
| `appointments/service.py:455` | `is_admin()` | `OwnershipChecker.enforce_booking_access` |
| `providers/router.py:472` | `is_detailer()` | `require_role("detailer")` |
| `realtime/router.py:87` | `is_admin()` | `OwnershipChecker.enforce_booking_access` |
| `realtime/router.py:91` | `is_detailer()` | `require_role("detailer")` |
| `avatar_router.py:39` | `is_detailer()` | `require_role("detailer")` |

**Regla:** Cada reemplazo incluye test que verifica que el comportamiento no cambió.

### Fase 4 — Migración progresiva de require_role() a require_permission() (3 días)

No se migran todos los 35 endpoints de golpe. Se sigue este orden:

| Prioridad | Endpoints | Criterio |
|-----------|-----------|----------|
| P0 | Admin endpoints (24) | Ya usan `require_role("admin")` — se dejan igual (admin bypass ya cubre) |
| P1 | Detailer endpoints (7) | Evaluar si necesitan permisos finos o role check es suficiente |
| P2 | Client endpoints (4) | Ídem |
| P3 | Endpoints con ownership (bookings, realtime) | Ya cubiertos por Fase 2 |

**Decisión Fase 4:** Si tras evaluar los 35 endpoints el role check es suficiente para todos, se documenta y se cierra. `require_permission()` queda disponible para cuando se necesite granularidad fina.

### Fase 5 — Enforcement contract + linting (1 día)

1. Documentar en `AGENTS.md`:
   ```
   ALL authorization decisions must go through one of:
   - require_permission(action, resource)   ← preferred
   - require_role(role_name)                ← legacy, transitional
   - OwnershipChecker.enforce_*()           ← resource-level access
   NO inline role checks (is_admin, is_detailer, etc.)
   ```

2. Agregar CI check: grep que detecte nuevos `is_admin()` / `is_detailer()` en routers y falle si aparecen.

## 5. Verification

- [ ] `User.has_permission()` existe y funciona (ya implementado, verificar)
- [ ] `require_permission("read", "appointments")` retorna 403 si falta permiso
- [ ] `require_permission("write", "appointments")` retorna 200 si detailer con permiso
- [ ] Admin bypass: admin pasa cualquier `require_permission()`
- [ ] 0 ocurrencias de `is_admin()` / `is_detailer()` inline en routers (post-migración)
- [ ] `OwnershipChecker.enforce_booking_access()` funciona para admin, client, detailer
- [ ] Tests de permisos pasan (mínimo 6 casos)
- [ ] Tests existentes (70 auth + 19 appointments + 17 user_flows + 27 admin) siguen verdes
- [ ] `mypy` + `ruff` verde
- [ ] Enforcement contract documentado en `AGENTS.md`

## 6. Risks

| Riesgo | Mitigación |
|--------|------------|
| `require_permission()` rompe endpoints que dependen de `require_role()` | Admin bypass activado por defecto — no hay cambios de comportamiento para admin |
| OwnershipChecker incorrecto bloquea acceso legítimo | Tests por cada combinación (admin, client dueño, client no dueño, detailer asignado, detailer no asignado) |
| Migración de inline checks introduce bugs | Cada reemplazo es atómico con su test. Se deploya por separado, no en batch. |
| `has_permission()` hace N+1 queries (user_roles → role → permissions) | Evaluar performance en Fase 4. Si es necesario, agregar eager loading o cache en Redis. |
| El equipo sigue escribiendo inline checks post-migración | CI check (grep) bloquea PRs con nuevos `is_admin()` / `is_detailer()` en routers |

## 7. Dependencias

| Plan | Relación |
|------|----------|
| `08-hardening.md` Phase 0 | Debe completar fix de `write:permissions` en client role (C3) antes de que `require_permission()` tenga sentido |
| `plan.md` Phase 6 | Active role switcher — cuando exista multi-role, `require_permission()` ya estará en su lugar |
| `01-profiles.md` (E1) | Multi-profile traerá ownership reglas más complejas — el `OwnershipChecker` es la base |

## 8. Secuencia Recomendada

```
Día 1: Fase 1 — require_permission() + tests
Día 2: Fase 2 — OwnershipChecker + tests
Día 3-4: Fase 3 — Reemplazar 8 inline checks
Día 5-7: Fase 4 — Evaluar + migrar gradual require_role() → require_permission()
Día 8: Fase 5 — Enforcement contract + CI check
       ↓
Backlog: ABAC avanzado / OPA (si la complejidad de reglas lo justifica)
```

**Total estimado:** 8 días hábiles (no consecutivos — puede intercalarse con hardening)

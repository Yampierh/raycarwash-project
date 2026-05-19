# 23 — Auth Hardening: Session Binding, Device Tracking & Anomaly Detection

> **Status:** Planning
> **Priority:** Critical
> **Dependencies:** None (parallel-safe with plans 08, 10, 22)
> **Audit findings resolved:** N/A (auth gaps surfaced by internal audit, not formal findings)
> **Unblocks:** True multi-device management, IP-bound tokens, permission enforcement, suspicious activity detection

---

## 1. Objective

Elevate the auth system from **stateless-JWT-with-refresh-rotation** to **session-bound, device-aware, anomaly-detecting identity control**. Cierra los 3 gaps más peligrosos del audit interno:

1. Access token sin `sid` → no puedes matar una sesión específica
2. `get_current_user` stateless → token robado sirve 30 min aunque revoques
3. No hay sesión real → usuario no ve "iPhone 15 · Safari · hace 2h"

---

## 2. Diagnosis

### Current Architecture

```
JWT access (30 min) → sin sid, sin ip, stateless
       ↓
get_current_user → valida firma + user activo + token_version
       ↓
       ❌ NUNCA consulta DB session
       ❌ NUNCA verifica si la sesión fue revocada
       ❌ NUNCA verifica IP/device coincidencia

RefreshToken (family_id) → rotation impecable, pero:
       ❌ No tiene device_name, ip, last_active
       ❌ No hay tabla sessions real
       ❌ device_name en login_history siempre NULL

Sesiones → GET /auth/sessions devuelve solo UUIDs sin metadata
```

### Gap Matrix

| Gap | Severidad | Archivo | Líneas |
|-----|-----------|---------|--------|
| Access token sin `sid` | **CRITICAL** | `domains/auth/service.py` | 86-98 |
| `get_current_user` sin DB check | **CRITICAL** | `domains/auth/service.py` | 734-816 |
| Sin tabla `sessions` con metadata | **HIGH** | `domains/auth/models.py` | 113-133 |
| `device_name` nunca se popula | **HIGH** | `domains/auth/routers/core.py` | 121-127 |
| `SessionRead` sin device/IP | **MEDIUM** | `domains/auth/schemas.py` | 256-262 |
| Permission engine sin conectar | **MEDIUM** | `users/models.py` vs `auth/service.py` | 234-246 vs 863-883 |
| Sin suspicious activity detection | **HIGH** | No existe | — |
| Sin ABAC (ownership checks inline) | **MEDIUM** | 8 ocurrencias en routers/services | ver plan 10 |
| Sin session UX (dispositivos visibles) | **LOW** | `sessions.py` router | 1-80 |
| Sin IP binding en tokens | **MEDIUM** | `auth/service.py` | 86-98 |

---

## 3. Scope

**In scope:**
- `sid` claim en access token JWT + Redis cache para sessions
- `get_current_user` con validación contra `sessions` table en DB
- Nueva tabla `sessions` con metadata (device, IP, user_agent, last_active_at)
- `SessionRead` schema con device_name + ip_address + user_agent + location
- Popular `device_name` en login + refresh flows
- RBAC runtime: `require_permission(action, resource)` como FastAPI `Depends()`
- ABAC: `OwnershipChecker` para bookings, payments, jobs (context-aware)
- IP binding opcional en access token (configurable)
- Suspicious activity detection: geo-anomaly + impossible travel + new device
- Session Management API UX: listar dispositivos con metadata, revocar específico
- Worker de cleanup de sesiones expiradas
- Tests: session validation, theft detection, device tracking, RBAC, ABAC, anomaly

**Out of scope:**
- Refactor del rotation de refresh tokens (funciona impecable)
- OPA avanzado (se evaluará post-ABAC)
- Cambios en WebAuthn, TOTP, social auth flows (solo logging)
- Frontend changes (API ready, UI adjustments son separadas)

---

## 4. Architecture

### Target State

```
LOGIN
↓
Crear session row: {user_id, device, ip, user_agent, family_id}
↓
Access token lleva sid + opcionalmente ip
↓
get_current_user:
  1. Decode JWT (firma + exp + aud)
  2. Redis: get_session_cached(sid) → session | None
  3. If miss → DB: session_repo.get_by_id(sid) → Redis setex 5min
  4. Validar session.active AND NOT session.revoked
  5. Fetch user: validar activo + token_version
  6. Update session.last_active_at (async, non-blocking)
  7. Validar IP si ip_binding=true
  8. Detectar geo-anomaly si cambió drásticamente

Refresh token rotation (sin cambios) + actualiza session metadata
```

### Redis Cache Pattern

```
Key:     session:{sid}
Value:   JSON → Session model (id, user_id, device, ip, revoked, etc.)
TTL:     300s (5 min = refresh token rotation window × 10)
Miss:    DB lookup → setex 300s
Invalidate on: session revoked, IP updated, device changed
```

### Data Model — New `sessions` Table

```python
class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID]          # PK = sid
    user_id: Mapped[uuid.UUID]     # FK → users.id
    family_id: Mapped[uuid.UUID]   # FK → refresh_tokens.family_id
    device_name: Mapped[str | None]     # "iPhone 15", "Chrome 120/Win"
    device_type: Mapped[str | None]     # "mobile", "desktop", "tablet", "api"
    ip_address: Mapped[str | None]      # last known IP
    ip_country: Mapped[str | None]      # geoip country code
    ip_city: Mapped[str | None]         # geoip city
    user_agent: Mapped[str | None]
    last_active_at: Mapped[datetime]
    created_at: Mapped[datetime]
    revoked: Mapped[bool]
    revoked_at: Mapped[datetime | None]
```

### JWT — New `sid` Claim

```python
# Current
payload = {
    "sub": str(user_id), "role": role_name, "type": "access",
    "v": token_version, "jti": str(uuid.uuid4()),
    # ❌ NO sid, NO ip
}

# Target
payload = {
    "sub": str(user_id), "role": role_name, "type": "access",
    "v": token_version, "jti": str(uuid.uuid4()),
    "sid": str(session_id),   # 🔥 NEW
    "ip": ip_address,         # 🔥 NEW (optional, configurable)
}
```

### get_current_user — Target State

```python
async def get_current_user(token, db, redis):
    payload = decode(token)

    session = await get_session_cached(payload["sid"], db, redis)
    if not session or session.revoked:
        raise HTTPException(401, "Session revoked")

    if settings.IP_BINDING and payload.get("ip") != current_ip:
        raise HTTPException(401, "IP mismatch")

    user = await user_repo.get_by_id(payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(401)

    if payload.get("v") != user.token_version:
        raise HTTPException(401)

    asyncio.create_task(session_repo.update_last_active(session.id))

    return user
```

### Mental Model

```
Access Token → identidad (quién eres)
Session      → control (desde dónde, con qué, deberías tener acceso?)
RBAC         → intención (qué puedes hacer)
ABAC         → contexto (bajo qué condiciones)
```

---

## 5. Execution Phases

### Fase 1 — `sid` + Session Validation con Redis Cache (3 días)

**Día 1 — Migration + Model**
1. Crear migration `m_023a_create_sessions_table.py`:
   - Tabla `sessions` con columnas del data model
   - FK → `users.id` (CASCADE)
   - FK → `refresh_tokens.family_id` (SET NULL on revoke)
   - Indexes: `(user_id, revoked)`, `(user_id, last_active_at)`, `(family_id)`
   - Partial index: `(user_id) WHERE revoked = FALSE`

2. Crear `Session` model en `domains/auth/models.py`
3. Registrar en `infrastructure/db/registry.py`

**Código modelo:**
```python
class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_active", "user_id", postgresql_where=sa.text("revoked = FALSE")),
        Index("ix_sessions_user_last_active", "user_id", sa.text("last_active_at DESC")),
        Index("ix_sessions_family_id", "family_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("refresh_tokens.family_id", ondelete="SET NULL"), nullable=False, unique=True)
    device_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    ip_country: Mapped[str | None] = mapped_column(String(4), nullable=True)
    ip_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

**Día 2 — SessionRepository + Redis Cache Layer**
1. Crear `SessionRepository` en `domains/auth/session_repository.py`:
   - `create(user_id, family_id, device_name, device_type, ip_address, user_agent) → Session`
   - `get_by_id(session_id) → Session | None`
   - `get_by_family(family_id) → Session | None`
   - `revoke(session_id) → None`
   - `revoke_all_for_user(user_id) → int`
   - `update_last_active(session_id) → None`
   - `get_sessions_for_user(user_id, limit, offset) → tuple[list[Session], int]`
   - `delete_expired(days) → int`

2. Crear función cacheada `get_session_cached()` en `domains/auth/service.py`:
```python
_SESSION_CACHE_TTL = 300  # 5 min

async def get_session_cached(
    sid: str,
    db: AsyncSession,
    redis: Redis,
) -> Session | None:
    cache_key = f"session:{sid}"
    cached = await redis.get(cache_key)
    if cached:
        return Session.model_validate_json(cached)

    session = await SessionRepository(db).get_by_id(uuid.UUID(sid))
    if session:
        await redis.setex(cache_key, _SESSION_CACHE_TTL, session.model_dump_json())

    return session
```

3. Crear `invalidate_session_cache(sid, redis)` → `redis.delete(f"session:{sid}")`
   - Llamar en: revoke, login (si ya existía sesión previa), IP update

**Día 3 — get_current_user + Login/Refresh Integration**
1. Modificar `AuthService._build_token()`:
   - Aceptar `session_id: uuid.UUID | None` param
   - Agregar `"sid": str(session_id)` al payload si no es None
   - `create_access_token()` acepta `session_id`

2. Modificar `get_current_user()`:
   - Extraer `sid` del payload
   - `get_session_cached(sid, db, redis)` en vez de DB directo
   - Si session revoked o no existe → 401
   - `asyncio.create_task(session_repo.update_last_active(session.id))` (fire-and-forget)
   - Mantener todas las validaciones existentes (user activo, token_version, onboarding)

3. Modificar login flow:
   - Crear Session row simultáneo con refresh token
   - Pasar `session_id` a `create_access_token()`
   - Registrar `session.family_id` en `UserLoginHistory`

4. Modificar refresh flow:
   - No crear nueva Session (misma familia = misma sesión)
   - Actualizar `last_active_at` + `ip_address` + `user_agent`
   - Invalidar cache: `invalidate_session_cache(sid, redis)`
   - Refresh token rotation sigue igual

**Rollback:**
- Si `sid` no está en payload → skip session check (backward compat)
- Config flag `AUTH_ENFORCE_SESSION: bool = False` durante rollout
- Si Redis está caído → fallback a DB lookup directo (graceful degradation)

---

### Fase 2 — Sessions Table + Device Tracking (2 días)

**Día 1 — Popular device_name con `user_agents` lib**
1. Agregar dependencia: `pip install user-agents` (PyPI)
2. Crear `infrastructure/geoip/device_parser.py`:
```python
from user_agents import parse

def parse_device_name(user_agent: str | None) -> str | None:
    """Extrae nombre descriptivo del dispositivo desde el User-Agent."""
    if not user_agent:
        return None
    ua = parse(user_agent)
    parts = []
    if ua.device.family and ua.device.family != "Other":
        parts.append(ua.device.family)
    if ua.os.family and ua.os.family != "Other":
        parts.append(ua.os.family)
    if ua.browser.family and ua.browser.family != "Other":
        parts.append(ua.browser.family)
    return " · ".join(parts) if parts else None

def parse_device_type(user_agent: str | None) -> str:
    """mobile | tablet | desktop | api"""
    if not user_agent:
        return "api"
    ua = parse(user_agent)
    if ua.is_mobile:
        return "mobile"
    if ua.is_tablet:
        return "tablet"
    if ua.is_pc:
        return "desktop"
    return "api"

def parse_device_fingerprint(user_agent: str | None, device_name: str | None) -> str:
    """Hash único para reconocer dispositivos conocidos."""
    raw = f"{user_agent or ''}|{device_name or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()
```

3. Modificar `LoginRequest` schema para aceptar `device_name: str | None` (opcional, respaldo si no se puede inferir del UA)
4. En los routers de login/social/refresh, llamar `parse_device_name(ua)` + `parse_device_type(ua)`
5. Frontend puede enviar `device_name` explícito como respaldo

**Populate login_history con metadata enriquecida:**
En el mismo login flow, agregar a `UserLoginHistory`:
```python
login_history.device_name = parse_device_name(user_agent)
login_history.ip_location = f"{geo.city}, {geo.country}"  # de MaxMind lookup
```
Hoy `device_name` siempre es `None` — esto lo corrige sin cambios de schema.

**Día 2 — Session Schemas + Endpoints**
1. Actualizar `SessionRead` schema:
```python
class SessionRead(_BaseSchema):
    id: uuid.UUID
    device_name: str | None
    device_type: str | None
    ip_address: str | None
    ip_country: str | None
    ip_city: str | None
    user_agent: str | None
    created_at: datetime
    last_active_at: datetime
    expires_at: datetime
    revoked: bool
```

2. Migrar `GET /auth/sessions` de `RefreshTokenRepository` a `SessionRepository`:
   - Usar `Session` model en vez de `RefreshToken`
   - JOIN con refresh_tokens para `expires_at`
   - Response ahora incluye device_name, device_type, ip, user_agent, location

3. Migrar `DELETE /auth/sessions/{family_id}` a `SessionRepository`:
   - Revocar session → invalidar Redis cache
   - Revocar refresh tokens de esa familia

4. Mantener backward compat: `RefreshTokenRepository.get_sessions_for_user()` deprecated

---

### Fase 3 — RBAC Runtime: `require_permission()` (2 días)

**Día 1 — Dependency + Redis Cache**
1. Crear `require_permission(action, resource)` en `domains/auth/service.py`:
```python
def require_permission(action: str, resource: str):
    permission_name = f"{action}:{resource}"

    async def _dep(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.is_admin():
            return current_user
        if not await _has_permission_cached(current_user, permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission_name}",
            )
        return current_user

    return _dep
```

2. `_has_permission_cached()` con Redis:
```python
_PERM_CACHE_TTL = 600  # 10 min

async def _has_permission_cached(user: User, permission_name: str) -> bool:
    cache_key = f"permissions:{user.id}"
    permissions = await redis.get(cache_key)

    if permissions is None:
        permissions = user.get_all_permissions()  # already exists in users/models.py
        await redis.setex(cache_key, _PERM_CACHE_TTL, json.dumps(list(permissions)))
    else:
        permissions = set(json.loads(permissions))

    return permission_name in permissions or "*:*" in permissions
```

3. Invalidar cache de permisos cuando:
   - Admin cambia roles de un usuario
   - User hace logout global (token_version increment)

**Día 2 — Migrar Endpoints**
1. Reemplazar `require_role("admin")` en 24 endpoints admin (admin bypass ya cubre)
2. Reemplazar `require_role("detailer")` en 7 endpoints por `require_permission("write", "appointments")` donde aplique
3. Reemplazar `require_role("client")` en 4 endpoints
4. Mantener `require_role()` como wrapper legacy que llama a `require_permission()`

**Nota:** Esto NO reemplaza los 8 inline checks de `is_admin()` / `is_detailer()` — esos se cubren en Fase 4 (ABAC) porque mezclan ownership con roles.

---

### Fase 4 — ABAC: Context-aware Authorization (2 días)

**Principio:** ABAC **NO vive en auth**. Cada dominio es dueño de sus políticas de acceso. Auth solo provee el hook `get_current_user()` — las reglas de ownership pertenecen al recurso.

**Día 1 — Policies por dominio**

1. Crear `domains/appointments/policies.py`:
```python
class AppointmentPolicies:

    @staticmethod
    def can_read(user: User, appointment: Appointment) -> bool:
        if user.is_admin():
            return True
        if appointment.client_id == user.id:
            return True
        if appointment.detailer_id == user.id:
            return True
        return False

    @staticmethod
    def can_write(user: User, appointment: Appointment) -> bool:
        """Modificar: solo dueño del recurso + estado permitido."""
        if user.is_admin():
            return True
        if appointment.status not in ALLOWS_MODIFICATION:
            return False
        if appointment.client_id == user.id:
            return True
        if appointment.detailer_id == user.id:
            return True
        return False
```

2. Crear `domains/payments/policies.py`:
```python
class PaymentPolicies:

    @staticmethod
    def can_read(user: User, payment: Payment) -> bool:
        if user.is_admin():
            return True
        return payment.user_id == user.id
```

3. Crear `domains/providers/policies.py`:
```python
class ProviderPolicies:

    @staticmethod
    def can_read_profile(user: User, provider: ProviderProfile) -> bool:
        if user.is_admin():
            return True
        return provider.user_id == user.id

    @staticmethod
    def can_write_profile(user: User, provider: ProviderProfile) -> bool:
        return provider.user_id == user.id
```

**Uso en routers:**
```python
from domains.appointments.policies import AppointmentPolicies

@router.get("/appointments/{id}")
async def get_appointment(
    id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    appointment = await AppointmentRepository(db).get_by_id(id)
    if not appointment:
        raise HTTPException(404)
    if not AppointmentPolicies.can_read(user, appointment):
        raise HTTPException(403, "Access denied")
    return appointment
```

**Patrón opcional — decorator/helper:**
```python
def enforce_policy(policy_fn):
    """Decorator-helper para no repetir el patrón if-not-policy en cada handler."""
    async def wrapper(
        resource_id: UUID,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        resource = await resolve_resource(resource_id, db)
        if not policy_fn(user, resource):
            raise HTTPException(403)
        return resource
    return wrapper
```

**¿Por qué policies en cada dominio y no un OwnershipChecker central?**
- El acoplamiento: `auth` no debería conocer `Appointment.client_id` ni `Payment.user_id`
- SRP: si cambia la lógica de negocio de appointments, tocas `appointments/policies.py`, no `auth/service.py`
- Testeabilidad: cada policy se testea con su dominio, sin imports circulares

**Día 2 — Reemplazar 8 inline checks**
Migrar ocurrencias de `is_admin()` / `is_detailer()` usando las policies de cada dominio:

| Archivo | Línea | Actual | Reemplazo |
|---------|-------|--------|-----------|
| `appointments/router.py:254` | `is_detailer()` | `AppointmentPolicies.can_read(user, appointment)` |
| `appointments/router.py:262` | `is_detailer()` | `AppointmentPolicies.can_write(user, appointment)` |
| `appointments/router.py:315` | `is_admin()` | `AppointmentPolicies.can_read(user, appointment)` |
| `appointments/service.py:455` | `is_admin()` | `AppointmentPolicies.can_write(user, appointment)` |
| `providers/router.py:472` | `is_detailer()` | `ProviderPolicies.can_read_profile(user, provider)` |
| `realtime/router.py:87` | `is_admin()` | `AppointmentPolicies.can_read(user, booking)` |
| `realtime/router.py:91` | `is_detailer()` | ya cubierto por `require_permission("read", "appointments")` |
| `avatar_router.py:39` | `is_detailer()` | `ProviderPolicies.can_read_profile(user, provider)` |

**Regla:** Cada reemplazo incluye test que verifica que el comportamiento no cambió.

---

### Fase 5 — Suspicious Activity Detection (3 días)

**Día 1 — Geo-IP + Impossible Travel**
1. Integrar geoip lookup con **MaxMind GeoLite2** (gratuito, ~99.8% accuracy país):
   - `pip install geoip2`
   - Descargar `GeoLite2-City.mmdb` desde maxmind.com (free license)
   - Montar en `infrastructure/geoip/client.py`:
```python
import geoip2.database
from dataclasses import dataclass

@dataclass
class GeoLocation:
    country: str | None   # "US"
    city: str | None      # "Fort Wayne"
    lat: float | None
    lon: float | None

class GeoIPClient:
    def __init__(self, db_path: str = "data/GeoLite2-City.mmdb"):
        self._reader = geoip2.database.Reader(db_path)

    async def lookup(self, ip: str) -> GeoLocation | None:
        try:
            resp = self._reader.city(ip)
            return GeoLocation(
                country=resp.country.iso_code,
                city=resp.city.name,
                lat=resp.location.latitude,
                lon=resp.location.longitude,
            )
        except Exception:
            return None  # IP privada o inválida → skip
```
   - Cache en Redis: `geoip:{ip}` → JSON de GeoLocation
   - TTL: 24h (las IPs no cambian de país frecuentemente)
   - Warmup: precargar IPs de sessions activas al iniciar

2. En `get_current_user`, después de validar sesión:
```python
if settings.GEO_ANOMALY_DETECTION:
    current_geo = await geoip.lookup(request.client.host)
    last_geo = session_repo.get_last_geo(session.id)

    if last_geo and _is_impossible_travel(last_geo, current_geo, session.last_active_at):
        await _trigger_anomaly_alert(
            user=user, session=session,
            reason="impossible_travel",
            from_geo=last_geo, to_geo=current_geo,
        )
```

3. `_is_impossible_travel()`:
```python
def _is_impossible_travel(last, current, last_active_at):
    if not last or not current:
        return False
    distance = haversine(last.lat, last.lon, current.lat, current.lon)
    hours_since = (datetime.now(timezone.utc) - last_active_at).total_seconds() / 3600
    return distance > 500 and hours_since < 1  # 500km/h = imposible sin avión
```

**Día 2 — Known Device Recognition**
1. Mantener `device_fingerprint` en sessions (hash de user-agent + device_name)
2. En login, si device fingerprint no existe en sessions del user:
   - Log como `NEW_DEVICE_LOGIN` en audit log
   - Opcional: enviar email "New device logged in"
   - Opcional: step-up auth requirement

3. Detectar IP reputation:
   - Si `ip_country` cambia drásticamente (US → CN en misma sesión)
   - Si IP aparece en blocklists conocidas (futuro)

**Día 3 — Anomaly Alerting + Rate Limit Hardening**
1. Crear `AnomalyEvent` schema:
```python
class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"
    id, user_id, session_id, anomaly_type (String), severity (String),
    description (Text), metadata_ (JSONB), created_at
```

2. Log every anomaly en `anomaly_events` table + audit log
3. Config thresholds vía `settings.py`:
   - `ANOMALY_IMPOSSIBLE_TRAVEL_SPEED: int = 500` (km/h)
   - `ANOMALY_KNOWN_DEVICE_EMAIL: bool = True`
   - `ANOMALY_AUTO_REVOKE_ON: list[str] = ["impossible_travel"]`
   - `ANOMALY_STEP_UP_ON: list[str] = ["new_device", "new_country"]`

---

### Fase 6 — Session Management API (UX PRO) (1 día)

**Objetivo:** Experiencia tipo Uber / Google — el usuario ve sus dispositivos activos y puede cerrar sesiones específicas.

**Endpoints:**

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/auth/sessions` | Listar sesiones activas con metadata |
| `POST` | `/auth/sessions/{id}/revoke` | Revocar sesión específica |

**Response `GET /auth/sessions`:**
```json
{
  "sessions": [
    {
      "id": "uuid",
      "device_name": "iPhone 15 Pro",
      "device_type": "mobile",
      "ip_address": "192.168.1.1",
      "ip_country": "US",
      "ip_city": "Fort Wayne",
      "user_agent": "Mozilla/5.0 ...",
      "created_at": "2026-05-19T10:00:00Z",
      "last_active_at": "2026-05-19T14:30:00Z",
      "expires_at": "2026-05-26T10:00:00Z",
      "revoked": false,
      "is_current": true
    }
  ],
  "total": 3
}
```

**`is_current`:** El frontend marca la sesión actual para que el usuario no se cierre a sí mismo por accidente.
- Comparar `session.id` con `payload["sid"]` del access token actual.

**UX cues para frontend:**
- Mostrar icono de dispositivo (phone/laptop/desktop/api)
- "Activo ahora" si `last_active_at < 5 min`
- Botón "Cerrar sesión" con confirmación

---

### Fase 7 — IP Binding Opcional (1 día)

1. Agregar `ip` claim al access token cuando `settings.IP_BINDING_ENABLED = True`
2. En `get_current_user`, si el claim `ip` existe y no coincide con `request.client.host` → 401
3. Config flag en `settings.py`:
   - `IP_BINDING: bool = False` (default off durante rollout)
   - `IP_BINDING_STRICT: bool = False` (True = rechazar, False = solo log + alert)

---

### Fase 8 — Session Cleanup Worker (1 día)

1. Worker en `workers/session_cleanup_worker.py`:
   - Corre daily
   - Revoca sesiones expiradas (refresh token expired + grace period)
   - Hard-delete anomaly_events viejos (>90 días)
   - Invalidar Redis cache de sessions eliminadas
   - Log stats: `{sessions_revoked, anomalies_cleaned, cache_invalidated}`

2. Registrar en `main.py` lifespan

---

## 6. Verification

- [ ] Migration `m_023a_create_sessions_table` corre limpio (up + down)
- [ ] Login crea Session row + access token con `sid`
- [ ] Redis cache: `get_session_cached()` funciona (hit + miss + invalidate)
- [ ] `get_current_user` rechaza access token de sesión revocada
- [ ] `get_current_user` funciona sin `sid` (backward compat con tokens viejos)
- [ ] Redis caído → fallback a DB lookup (graceful degradation)
- [ ] Refresh no crea nueva Session (misma familia)
- [ ] `GET /auth/sessions` devuelve device_name, ip, user_agent, country, city
- [ ] `POST /auth/sessions/{id}/revoke` revoca session + refresh tokens + invalida cache
- [ ] `device_name` se popula desde login request
- [ ] `require_permission("read", "appointments")` retorna 403 si falta permiso
- [ ] Admin bypass: admin pasa cualquier `require_permission()`
- [ ] `AppointmentPolicies.can_read()` funciona: admin, client dueño, detailer asignado, ajenos
- [ ] `AppointmentPolicies.can_write()` respeta estado del appointment (solo si ALLOWS_MODIFICATION)
- [ ] `PaymentPolicies.can_read()` funciona: admin, payment.user_id
- [ ] `ProviderPolicies.can_read_profile()` funciona: admin, provider.user_id
- [ ] 0 ocurrencias de `is_admin()` / `is_detailer()` inline en routers (post-migración)
- [ ] `parse_device_name()` extrae "iPhone · iOS · Safari" correctamente
- [ ] `parse_device_type()` clasifica mobile/tablet/desktop/api
- [ ] `parse_device_fingerprint()` produce hash consistente para mismo UA+device_name
- [ ] login_history.device_name ya no es NULL
- [ ] Impossible travel detecta US→CN en 5 min
- [ ] MaxMind GeoIP lookup con cache Redis funciona
- [ ] New device login logged como anomaly
- [ ] IP binding opcional funciona (on/off)
- [ ] Session cleanup worker revoca expiradas + limpia cache
- [ ] Tests existentes (70 auth + 19 appointments + 17 user_flows + 27 admin) siguen verdes
- [ ] Tests nuevos: session validation (4), device tracking (3), RBAC (4), ABAC policies (6), anomaly (3), ip binding (2), worker (1)
- [ ] `mypy` + `ruff` verde

---

## 7. Risks

| Riesgo | Mitigación |
|--------|------------|
| Session DB lookup en cada request añade latency | Redis cache con TTL 5min + `update_last_active` es fire-and-forget async. Session lookup es PK indexado = ~1ms. |
| Redis caído = auth caído | `get_session_cached()` fallback a DB lookup directo con try/except. Log warning si Redis no responde. |
| Rollback difícil si `sid` es requerido | `AUTH_ENFORCE_SESSION = False` durante rollout. Si token no tiene `sid`, skip session check. |
| `device_name` del frontend no es confiable | Es metadata informativa, no security boundary. La session validation depende de `sid` + `revoked`, no del device. Usar `user_agents` lib como fuente primaria. |
| Impossible travel falsos positivos (VPN, proxy) | Configurable por severity. Default: solo log + alert, no revocar. Step-up auth como acción intermedia. |
| GeoIP lookup latency | Cache en Redis con TTL 24h. Si cache miss, fire-and-forget sin bloquear request. Warmup de IPs activas al startup. |
| Sesiones existentes sin `sid` en tokens | Backward compat: tokens sin `sid` usan `token_version` como fallback (comportamiento actual). No se fuerza re-login. |
| Permission cache stale si role cambia | Invalidar `permissions:{user_id}` cuando admin modifica roles. TTL 10 min es aceptable. |
| ABAC policies duplicadas entre dominios | No hay duplicación — cada dominio modela sus propias reglas de ownership. Si hay patrones comunes, extraer a `shared/policies.py` post-Fase 4. |
| `is_current` en sessions: el frontend podría auto-revocarse | El backend marca `is_current` comparando con `payload["sid"]`. El frontend debe deshabilitar botón en sesión actual. |

---

## 8. Dependencies

| Plan | Relación |
|------|----------|
| `08-hardening.md` | Independiente (security hardening paralelo) |
| `22-security-architecture-audit.md` | Independiente (audit findings, no auth gaps) |
| `frontend/` | Enviar `device_name` desde login (opcional, respaldo) + mostrar sessions con metadata UX |

**Nota:** Este plan absorbe el scope de `10-authorization-layer.md` (RBAC runtime + ABAC).

---

## 9. Secuencia Recomendada

```
Semana 1:
  Día 1-3: Fase 1 — sid + session validation + Redis cache
  Día 4-5: Fase 2 — Sessions metadata + device tracking

Semana 2:
  Día 6-7: Fase 3 — RBAC runtime: require_permission() + Redis cache
  Día 8-9: Fase 4 — ABAC: OwnershipChecker + inline checks replacement

Semana 3:
  Día 10-12: Fase 5 — Suspicious activity detection
  Día 13:    Fase 6 — Session Management API UX

Semana 4:
  Día 14:    Fase 7 — IP binding opcional
  Día 15:    Fase 8 — Session cleanup worker
  Día 16-17: Test pasada completa + hardening + rollout

Paralelo (sin bloqueo):
  - Frontend: enviar device_name en login + mostrar sessions con metadata
```

**Total estimado:** 17 días hábiles (no consecutivos)

---

## 10. Migration Plan

### Rollout Strategy

```
Fase 0 (preparación, day 0):
  - Crear tabla sessions + SessionRepository + Redis cache
  - No cambiar nada de tokens aún

Fase 1 (day 1):
  - Empezar a poblar sessions en login
  - Access token todavía sin sid

Fase 2 (day 2):
  - Agregar sid al access token
  - AUTH_ENFORCE_SESSION = False

Fase 3 (day 3):
  - AUTH_ENFORCE_SESSION = True (token sin sid → fallback)
  - Redis cache activo

Fase 4 (day 5):
  - Rechazar tokens sin sid (tokens pre-migración expiraron en 30 min)
  - Full enforcement + ABAC + RBAC runtime + anomaly detection
```

**Zero-downtime:** Sí — backward compat en cada fase. Los tokens viejos sin `sid` siguen funcionando hasta que expiran naturalmente.

---

## 11. Mental Model

```text
Access Token → identidad       → quién eres
Session      → control         → desde dónde, con qué, deberías seguir teniendo acceso?
RBAC         → intención       → qué puedes hacer en el sistema (auth/)
ABAC         → contexto        → bajo qué condiciones puedes hacerlo (cada dominio/)


═══════════════════════════════════════════════════

Layers (de abajo hacia arriba):
┌─────────────────────────────────────────────────┐
│  AnomalyDetector                                 │
│  → responde: "¿este comportamiento es anómalo?" │
├─────────────────────────────────────────────────┤
│  Domain Policies (appointments/, payments/, ...) │
│  → responde: "¿es dueño / tiene contexto?"      │
├─────────────────────────────────────────────────┤
│  require_permission() — RBAC runtime             │
│  → responde: "¿tiene permiso para la acción?"   │
├─────────────────────────────────────────────────┤
│  get_current_user() — Session validation         │
│  → responde: "¿quién es y su sesión sigue viva?"│
└─────────────────────────────────────────────────┘

═══════════════════════════════════════════════════

Principio:
  - Session y RBAC viven en auth/domain/auth por ser transversales
  - ABAC policies viven en cada dominio de negocio
  - Anomaly detection vive en infrastructure/geoip/ + callbacks en auth
```

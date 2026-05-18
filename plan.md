# Plan: Sistema de Profile completo para RayCarWash (API RESTful unificada, por fases)

## Contexto

RayCarWash es un marketplace móvil (Uber-like) que conecta clientes con mobile detailers. Hoy el "perfil" del usuario está **fragmentado** en endpoints inconsistentes (`/auth/me`, `/auth/update`, `/api/v1/detailers/me`, `/api/v1/vehicles`, `/api/v1/notifications/device-token`), cada uno con su propio estilo de respuesta, manejo de errores, paginación, y sin contrato de API coherente.

**Decisión arquitectónica central**: en vez de crear un nuevo namespace `/api/v1/profile/*` que orqueste los dominios fragmentados, **rediseñamos la API completa bajo principios RESTful uniformes**, centralizando todo lo del usuario autenticado bajo `/api/v1/users/me/*`. Auth-específico (register, login, refresh, password reset) se mantiene en `/api/v1/auth/*`. Esto:

- **Elimina fragmentación**: el frontend habla con UN dominio (`users`) en vez de tres.
- **Unifica patrones**: misma envoltura de respuesta, mismo formato de error, misma paginación, misma autenticación, mismo versionado.
- **Es resource-oriented**: sustantivos (`/users/me/vehicles`), no verbos. Acciones se expresan via HTTP verbs + sub-recursos.
- **Es escalable**: agregar features = agregar sub-recursos consistentes. Onboarding de nuevos integradores trivial gracias a OpenAPI auto-generado.

**Decisiones ya tomadas con el usuario**:
1. **Alcance**: diseño completo (todas las fases, no MVP-only).
2. **Multi-rol UX**: switcher explícito (Uber driver/rider). Vista Cliente ↔ Vista Detailer alternable. Rol activo persiste y se refleja en JWT (`role` claim).
3. **Storage**: AWS S3 + CloudFront, presigned URLs (TTL 1h upload, 24h download), KMS para docs sensibles.
4. **Próximo paso**: documento de diseño primero — implementación por fases en sesiones separadas tras aprobación.
5. **API unificada bajo `/api/v1/users/me/*`** (este plan).

**Outcome**: un sistema de Profile que (a) vive como sub-recursos coherentes del usuario, (b) seguro por diseño (PII clasificado, step-up auth, audit log extendido), (c) escalable a multi-ciudad y miles de usuarios concurrentes, y (d) dividido en **9 fases ejecutables** sobre 8-10 sprints.

---

## 0. Auditoría del codebase actual (mayo 2026)

### 0.1 Estructura backend real

```
backend/
├── alembic/                 # ✅ migraciones (16 existen)
├── alembic.ini
├── api/
│   └── router.py            # ✅ ensamble principal
├── app/                     # infra estable
│   ├── core/                # config, security, limiter
│   ├── db/                  # seed_rbac.py
│   ├── models/              # legacy/shared
│   ├── repositories/, routers/, schemas/, services/
│   ├── workers/             # (placeholder)
│   └── ws/                  # websocket helpers
├── domains/                 # ✅ DDD-lite organization (PATRÓN ACTUAL)
│   ├── admin/               # dashboard admin (router.py, repository.py, schemas.py)
│   ├── appointments/        # FSM lifecycle
│   ├── audit/               # AuditLog append-only
│   ├── auth/                # COMPLETO — RS256 JWT, WebAuthn, OAuth2, sessions, password, email_verify
│   │   ├── routers/         # split en 6 sub-routers
│   │   ├── models.py        # Role, Permission, RefreshToken, EmailVerificationToken, etc.
│   │   ├── service.py       # AuthService (800+ líneas)
│   │   └── *_repository.py  # 5 repositorios especializados
│   ├── matching/            # H3 geospatial scoring
│   ├── notifications/       # Expo Push API
│   ├── payments/            # Stripe + ledger append-only
│   ├── providers/           # ProviderProfile
│   ├── realtime/            # Redis Pub/Sub
│   ├── reviews/             # Rating
│   ├── services_catalog/    # services + addons
│   ├── users/               # User + ClientProfile
│   └── vehicles/            # Vehicle + NHTSA VIN
├── events/                  # event bus
├── infrastructure/          # adapters
│   ├── db/, email/, h3/, nhtsa/, redis/, stripe/
├── shared/
│   └── schemas.py           # _BaseSchema, PaginatedResponse
├── tests/
├── workers/                 # CRONS existentes — sin RQ aún
│   ├── assignment_worker.py
│   ├── ledger_seal_worker.py
│   ├── location_worker.py
│   ├── token_cleanup_worker.py
│   └── domain/
├── main.py                  # FastAPI + lifespan
├── requirements.txt
└── alembic.ini
```

**Decisión confirmada**: **respetar `backend/domains/X/`**. NO migrar a `backend/app/{models,routers}/`. Las entidades nuevas del Profile system viven dentro de `domains/users/`, `domains/auth/`, `domains/providers/`, etc., según su dueño natural.

### 0.2 Auditoría de auth (estado real, mayo 2026)

✅ **YA EXISTE y funciona bien** — solo EXTENDER, no reescribir:

| Capacidad | Implementación actual | Archivo |
|---|---|---|
| JWT signing | **RS256** con RSA-2048 keys (`jwt_private.pem` / `jwt_public.pem`) | `domains/auth/service.py:78` |
| Token types | access, refresh, password_reset, registration, onboarding, webauthn_*, email_verification | `service.py:35-46` |
| Token version | `User.token_version` invalida tokens globalmente | `service.py:_build_token` |
| Refresh rotation | `RefreshTokenRepository.rotate_family()` | `domains/auth/refresh_token_repository.py` |
| RBAC | `Role` + `Permission` + `UserRoleAssociation` + `RolePermission` (3-tabla classic) | `domains/auth/models.py` |
| WebAuthn / Passkeys | `webauthn==2.2.0`, challenges en Redis TTL 5min, sign_count anti-cloning | `domains/auth/webauthn_service.py` |
| OAuth2 social | Google + Apple via `auth_providers` table | `domains/auth/routers/social.py` |
| Sessions list/revoke | `GET /auth/sessions`, `DELETE /auth/sessions/{id}` | `domains/auth/routers/sessions.py` |
| Email verification | DB-backed tokens (no JWT stateless), single-use, audit logged | `domains/auth/routers/email_verification.py` |
| Password reset | Token-based, single-use | `domains/auth/routers/password.py` |
| Account lockout | `failed_login_attempts`, `locked_until` con escalación | `domains/auth/service.py` |
| Onboarding state | `OnboardingStatus` enum + lockout post-completion | `domains/users/models.py` |
| Rate limiting | slowapi en `/auth/register`, `/auth/login`, etc. | `app/core/limiter.py` |
| PII encryption | `EncryptedType` en `full_name`, `phone_number` | `domains/users/models.py` |
| Phone HMAC | `phone_hash` SHA-256 para lookup sin decrypt | `domains/users/models.py` |
| Audit log | `AuditLog` append-only con `AuditAction` enum | `domains/audit/models.py` |
| JWKS endpoint | `GET /.well-known/jwks.json` | `domains/auth/wellknown_router.py` |
| Stripe Identity KYC | `verification_status`, `stripe_verification_session_id` | `domains/providers/models.py` |

❌ **FALTA — agregar en Fase 0/3**:

| Capacidad faltante | Dónde agregar |
|---|---|
| `TotpCredential` model + endpoints `/auth/two-fa/*` | `domains/auth/models/totp_credential.py` (nuevo) |
| `UserLoginHistory` model + hook en `authenticate_user` | `domains/auth/models/user_login_history.py` (nuevo) |
| Step-up dependency con Redis primary + DB fallback | `app/core/step_up.py` (nuevo) |
| `User.last_step_up_at` column | migración |
| Endpoint `GET /auth/security` (summary consolidado) | `domains/auth/routers/security.py` (nuevo) |
| Endpoint `GET /auth/history` (login + audit security) | `domains/auth/routers/history.py` (nuevo) |
| Endpoints admin de passkeys (list/rename/delete) | `domains/auth/routers/passkeys_admin.py` (nuevo) |
| `audit_log` extension (old_value, new_value, ip, UA, request_id) | migración |
| Middleware `audit_context` | `app/middleware/audit_context.py` (nuevo) |

### 0.3 Frontend — 3 tracks

| Track | Path | Stack | Estado actual | Prioridad |
|---|---|---|---|---|
| **Mobile app** | `frontend/` | React Native 0.81 + Expo 54 | 29 screens, Zustand, axios, Stripe RN, WebAuthn (`react-native-passkey`) | **Primaria** — el Profile completo se entrega aquí |
| **Admin web** | `web/` | Next.js 15 + App Router | Login + dashboard inicial | Secundaria — vista admin de usuarios, edición/impersonación suave |
| **Marketing/Customer web** | `marketing/` | Next.js + App Router con `[locale]` i18n | Marketing pages + estructura inicial | Tercera — mirror web del flujo cliente (login, perfil, citas) |

**Estructura `frontend/src/`** (mobile):
- `screens/` (29 archivos), `components/` (8), `services/` (auth, user, detailer, etc.), `store/` (Zustand authStore), `hooks/`, `navigation/`, `theme/`, `utils/`

**Estructura `web/app/`** (admin):
- `app/dashboard/`, `app/login/`, `components/`, `lib/`

**Estructura `marketing/app/`** (customer web):
- `app/[locale]/` con i18n via `next-intl`, `components/`, `messages/` (translations)

**Decisión**: cambios al Profile se entregan **primero en mobile** (canal principal). Las webs se actualizan con un lag de 1-2 fases. Cada fase tendrá:
- **Mobile**: lista de screens nuevas/modificadas (detalle alto)
- **Admin web**: lista de páginas que necesitan actualización (detalle medio)
- **Marketing web**: lista de páginas mirror que necesitan implementarse (detalle bajo — placeholders por ahora)

### 0.4 Decisiones de entorno de desarrollo

| Tema | Producción | Desarrollo / Staging |
|---|---|---|
| **Storage** | AWS S3 + CloudFront, SSE-KMS para docs privados | `LocalStorageAdapter` que guarda en `./storage/` con misma interfaz. `# TODO(prod): swap to S3Adapter` |
| **Pagos** | Stripe real | Stripe **test mode** (claves `sk_test_*`, `pk_test_*`). Cards de prueba (4242...). Webhooks via Stripe CLI (`stripe listen`) |
| **Email** | SendGrid (paid) | SendGrid trial (100/día gratis) o **MailHog** local (`docker-compose` exposes :8025) |
| **SMS OTP** | Twilio | Twilio trial gratis (+15 dólares crédito) o **mock** que loguea OTP a consola |
| **Geocoding** | Google Maps Geocoding API | Capa gratuita Google (200 USD/mes free credit) o **OpenStreetMap Nominatim** (gratis pero rate-limited) |
| **IP geolocation** | MaxMind GeoLite2 | Free download mensual de MaxMind o `ipapi.co` free tier |
| **Workers** | RQ (Redis Queue) + supervisor | RQ local + `rq worker` manual o via docker-compose |
| **Queue** | Redis production cluster | Redis local (docker-compose) |
| **Identity KYC** | Stripe Identity real | Stripe Identity test mode |
| **Branch strategy** | `main` deploy a prod | feature branches `feat/profile-phaseX` → PR a `main` |

**Cada adapter externo se diseña con interfaz abstracta** + dos implementaciones (real + dev/mock). Selección via env var `RAYCARWASH_ENV=development|production`.

---

---

## 0.5 Convenciones de implementación (no negociables, agregado 2026-05-15)

**Bugs pre-existentes que aparezcan durante una fase**:
- Si el fix es trivial y no cambia semántica → arreglar in-place y mencionarlo en el commit message bajo "Pre-existing fixes:".
- Si el fix cambia semántica o tiene scope grande → dejar comentario `# TODO(bug): <descripción>` o `// TODO(bug): ...` en la línea exacta, con: (a) qué hace mal, (b) qué debería hacer, (c) por qué se posterga (ej. "needs product decision", "blocked by Phase X migration").
- Nunca ignorar silenciosamente un test que falla — actualizar el assert si la nueva semántica es correcta, o marcarlo `@pytest.mark.xfail(reason="...")` con el reason ligado a un issue. El plan trata `xfail` como deuda visible.

**Funciones / blocks no implementados**:
- Devolver un valor "vacío seguro" (lista vacía, `None`, `0`, `False`) NUNCA un mock con datos falsos.
- Acompañar siempre con `# TODO(phase N <nombre-recurso>): <descripción>` indicando exactamente qué fase entrega el código real y qué archivos/migraciones se esperan.
- Si el frontend depende de un endpoint que aún no existe, definir el helper tipado (que lanza `NotImplementedError` o `throw new Error("…")`) para que el code path quede pre-escrito y la migración futura sea reemplazar la implementación, no agregarla.

**Adaptadores externos**:
- Cada servicio externo (S3, Stripe, Twilio, SendGrid, Google Maps, MaxMind) **debe** tener:
  1. Un Protocol / interface puro en `infrastructure/<servicio>/base.py`.
  2. Una implementación dev/mock (Local, ConsoleSms, MailHog, Nominatim, NullIpLocation).
  3. Un placeholder `# TODO(prod): implement <Adapter>` o método que lance `RuntimeError` con el mensaje de qué falta — no fallar silencioso.
- La selección Dev↔Prod vive en `app/core/dependencies.py` keyed por `RAYCARWASH_ENV`.

**Migraciones Alembic**:
- Cada migración trae **upgrade y downgrade simétricos** (excepto enum extensions Python-only, que documentan como no-op).
- Antes de cerrar una fase: `alembic upgrade head && alembic downgrade <previous-head> && alembic upgrade head` debe pasar limpio contra Postgres.
- Si una columna depende de otra que entra en una fase posterior (ej. `client_profiles.default_address_id` referencia `user_addresses` que llega en Phase 4), la migración inicial crea el campo **sin FK constraint**; la migración futura añade la FK. Ambas se nombran en el commit message para que el reviewer las correlacione.

**Code review check-list** que cada PR debe pasar:
- [ ] Tests existentes verdes (o documentado por qué un fallo es pre-existente con TODO o xfail).
- [ ] Type-check verde en cada track frontend tocado.
- [ ] Cada bloque del Profile Hub que devuelve placeholder tiene su `TODO(phase N)` con archivo destino.
- [ ] Cada migración nueva tiene downgrade no-vacío.
- [ ] No hay `print()`, `console.log`, `Alert.alert("WIP")` o equivalentes.
- [ ] No hay credenciales hardcodeadas (Stripe keys, SMTP passwords) — todo va por `Settings`.

---

## 1. Principios de diseño de API (no negociables)

| Principio | Aplicación en RayCarWash |
|---|---|
| **Recursos, no acciones** | Sustantivos en plural (`/users`, `/vehicles`). Acciones via HTTP verbs + sub-recursos (`/users/me/avatar`). Excepciones nombradas como "comandos" cuando no encaja CRUD: `/users/me/role` (PATCH cambia rol activo). |
| **Versionado en URL** | Prefijo `/api/v1/`. Breaking changes → `/api/v2/`. Coexisten durante deprecación. Header `Deprecation: true` + `Sunset:` para endpoints viejos. |
| **HTTP verbs** | `GET` (read), `POST` (create), `PUT` (replace), `PATCH` (partial update), `DELETE` (remove). 204 No Content en deletes sin body. |
| **Status codes semánticos** | 200, 201, 202, 204, 400, 401, 403, 404, 409, 410, 422, 423, 429, 500. Cada uno con significado fijo (tabla §3.3). |
| **Auth uniforme** | `Authorization: Bearer <jwt>` en todos los endpoints protegidos. Excepción: `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/password/forgot`, `/.well-known/jwks.json`. |
| **Rate limiting por endpoint + por user + por IP** | Headers `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`. Límites en tabla de endpoints. |
| **Paginación cursor-based** | Query params `?limit=20&cursor=opaque_string`. Nunca `?page=N` (evita inconsistencias en datos volátiles). |
| **Filtros y orden uniformes** | `?status=active`, `?sort=-created_at` (el `-` = desc). Combinaciones: `?sort=price,-created_at`. |
| **Idempotencia** | Header `Idempotency-Key: <client-uuid>` en POST/PATCH sensibles (payments, contact changes, deletion). El backend cachea respuesta por `(user_id, key)` durante 24h. |
| **Documentación viva** | OpenAPI auto-generado por FastAPI desde Pydantic. Tags por dominio. Ejemplos en cada endpoint. |
| **Soft delete por default** | `is_deleted: bool` + `deleted_at`. Hard-delete solo en GDPR finalizer worker. |
| **Timestamps UTC + ISO 8601** | Toda fecha en respuesta: `"2026-05-14T10:30:00Z"`. Frontend convierte a timezone del user. |
| **Precios en integer cents** | Nunca floats. Display `cents/100` en frontend. |

---

## 2. Estructura de endpoints unificada

### 2.1 `/api/v1/auth/*` — Identidad y sesión (auth-specific)

Solo lo que **NO es un recurso del User** sino una acción de autenticación.

| Método | Endpoint | Descripción | Auth | RL |
|---|---|---|---|---|
| POST | `/api/v1/auth/register` | Crear cuenta + onboarding token | público | 5/h por IP |
| POST | `/api/v1/auth/login` | Email + password → tokens | público | 5/min por IP |
| POST | `/api/v1/auth/refresh` | Refresh token → nuevo access | refresh | 60/h |
| POST | `/api/v1/auth/logout` | Revoca refresh actual | access | 60/h |
| POST | `/api/v1/auth/logout-all` | Revoca todos refresh + bump token_version | access | 5/h |
| POST | `/api/v1/auth/identify` | Identifier-first lookup | público | 30/min |
| POST | `/api/v1/auth/verify` | OAuth/social verification | público | 10/min |
| POST | `/api/v1/auth/complete-profile` | Onboarding final (asigna role) | onboarding | 3/h |
| POST | `/api/v1/auth/password/forgot` | Inicia reset por email | público | 3/h |
| POST | `/api/v1/auth/password/reset` | Consume token de reset | público | 5/h |
| POST | `/api/v1/auth/password/change` | Cambia password autenticado (step-up) | step-up | 5/h |
| GET | `/api/v1/auth/state` | Auth state para navegación FE | access \| onboarding | 60/min |
| GET | `/.well-known/jwks.json` | Public key del JWT (RS256) | público | — |
| POST | `/api/v1/auth/google` | OAuth Google | público | 10/min |
| POST | `/api/v1/auth/apple` | OAuth Apple | público | 10/min |
| POST | `/api/v1/auth/webauthn/register/begin` | Passkey enrollment challenge | step-up | 10/h |
| POST | `/api/v1/auth/webauthn/register/complete` | Confirm enrollment | access | 10/h |
| POST | `/api/v1/auth/webauthn/authenticate/begin` | Passkey challenge | público | 30/min |
| POST | `/api/v1/auth/webauthn/authenticate/complete` | Verify + emit tokens | público | 30/min |
| POST | `/api/v1/auth/email/verify` | Confirma email con token | público | 10/h |
| POST | `/api/v1/auth/email/verify/resend` | Re-envía link | access | 3/h |

**Deprecaciones (Fase 0)**: los siguientes endpoints se marcan deprecated con `Sunset` header y migran a su equivalente:
- `GET /auth/me` → `GET /api/v1/users/me`
- `PUT /auth/update` → `PATCH /api/v1/users/me`
- `GET /api/v1/detailers/me` → `GET /api/v1/users/me/provider-profile`
- `PUT /api/v1/detailers/me` → `PATCH /api/v1/users/me/provider-profile`
- `PATCH /api/v1/detailers/me/status` → `PATCH /api/v1/users/me/provider-status`
- `POST /api/v1/notifications/device-token` → `POST /api/v1/users/me/devices`

Los viejos retornan 200 + warning header durante 2 sprints, luego 410 Gone.

### 2.1.4 `/api/v1/auth/history` — Historial de seguridad

Auditoría granular para el usuario: logins (exitosos y fallidos), cambios de password, 2FA enable/disable, passkey register/revoke, email/phone change, session revocations, password resets.

| Método | Endpoint | Descripción | Auth | RL |
|---|---|---|---|---|
| GET | `/api/v1/auth/history?limit=&cursor=&type=&from=&to=` | Feed cursor-paginated. Mezcla `UserLoginHistory` + `AuditLog` filtrado a security actions. | access | 60/h |

**Filtros**:
- `type` (comma-separated): `login`, `login_failed`, `password_change`, `email_change`, `phone_change`, `two_fa_enabled`, `two_fa_disabled`, `passkey_added`, `passkey_revoked`, `session_revoked`, `password_reset_requested`. Default: todos.
- `from` / `to`: rango ISO 8601 fechas.

**Response item shape**:
```json
{
  "id": "log_001",
  "type": "login",
  "occurred_at": "2026-05-14T09:00:00Z",
  "summary": "Login from iPhone 13 in Miami, FL",
  "ip_address": "192.168.1.1",
  "ip_location": "Miami, FL (approx)",
  "user_agent": "RaycarwashApp/1.4.2 iOS/17.2",
  "device_name": "iPhone 13",
  "was_successful": true,
  "failure_reason": null,
  "details": { ... }  // variable según type; ej: email_change → {old_value, new_value}
}
```

**Retención**: logins exitosos 12 meses, logins fallidos 90 días. Worker mensual purga.

### 2.1.5 `/api/v1/auth/*` — Centro de seguridad (decisión: separación estricta)

**Decisión arquitectónica**: TODO lo relacionado con credenciales, sesiones, autenticadores y 2FA vive bajo `/api/v1/auth/*`. `/users/me` se enfoca SOLO en datos de perfil y preferencias. Esto cumple SRP estricto: identidad/autenticación ≠ persona/perfil.

| Método | Endpoint | Descripción | Auth | RL |
|---|---|---|---|---|
| GET | `/api/v1/auth/security` | Resumen consolidado: `{two_fa_enabled, passkeys_count, active_sessions_count, password_age_days, last_login_at, recent_failed_attempts, suspicious_locations[]}` | access | 60/h |
| GET | `/api/v1/auth/sessions` | Lista sessions (refresh tokens activos) con device, IP, last_seen | access | 60/h |
| DELETE | `/api/v1/auth/sessions/{session_id}` | Revoca sesión específica | access | 20/h |
| DELETE | `/api/v1/auth/sessions` | Revoca TODAS menos la actual | step-up | 5/h |
| GET | `/api/v1/auth/passkeys` | Lista WebAuthn credentials registradas | access | 60/h |
| PATCH | `/api/v1/auth/passkeys/{id}` | Renombra `device_name` | access | 20/h |
| DELETE | `/api/v1/auth/passkeys/{id}` | Revoca passkey | step-up | 10/h |
| POST | `/api/v1/auth/two-fa/enroll` | Devuelve TOTP secret + QR + 10 backup codes (one-shot) | step-up | 5/h |
| POST | `/api/v1/auth/two-fa/verify` | Body `{code}`. Activa 2FA. | access | 10/h |
| DELETE | `/api/v1/auth/two-fa` | Desactiva 2FA | step-up | 5/h |
| POST | `/api/v1/auth/two-fa/backup-codes/regenerate` | Genera nuevos backup codes, invalida anteriores | step-up | 3/h |

Los endpoints de protocolo (`/auth/webauthn/register/begin|complete`, `/auth/webauthn/authenticate/*`) siguen viviendo donde están — son handshakes criptográficos, no recursos administrables.

### 2.2 `/api/v1/users/me` — Profile Hub (recurso central agregador)

> **🆕 CAMBIO (Profile Hub spec)** — el endpoint pasa de "aggregate con include" a **Profile Hub** con shape compuesto por bloques. La respuesta agrupa la información en bloques nombrados (`user`, `profile`, `vehicles`, `sessions`, etc.) bajo `data`, y `meta.includes` confirma exactamente qué bloques se cargaron.

| Método | Endpoint | Descripción | Roles | RL |
|---|---|---|---|---|
| GET | `/api/v1/users/me?include=` | Profile Hub. `user` siempre presente. Otros bloques opt-in via `?include=`. | any-auth | 120/h |
| PATCH | `/api/v1/users/me` | Actualiza campos básicos en `profile` (first_name, last_name, pronouns, language, timezone) | self | 30/h |

**Filosofía del Hub**: una sola llamada que el frontend puede pedir con distintos `include` según la pantalla. Carga inicial mínima → más bloques on-demand a medida que el usuario navega. Evita N+1 calls y mantiene un solo punto de verdad para "qué sé del usuario logueado".

#### 2.2.1 Tokens `include` soportados

| Token | Bloque | Costo | Step-up | Quién |
|---|---|---|---|---|
| `profile` | `profile` | cheap (1 row join) | no | any-auth |
| `vehicles` | `vehicles[]` | cheap (1 query) | no | client |
| `favorites` | `favorites[]` | cheap | no | client |
| `addresses` | `addresses[]` | cheap | no | any-auth |
| `payment_methods` | `payment_methods[]` | cheap (local sync) | no | any-auth |
| `preferences` | `preferences` | cheap | no | client |
| `notifications` | `notifications` | cheap (JSONB) | no | any-auth |
| `stats` | `stats` | **denormalizado** (triggers PostgreSQL en appointments) | no | any-auth |
| `provider` | `provider` (solo si user es detailer) | cheap (1 row join) | no | detailer / dual-role |
| `security` | `security` | medio (consulta auth domain: tokens, webauthn count, last_login) | **sí** | any-auth |
| `sessions` | `sessions[]` | medio (consulta refresh_tokens activos + last UserLoginHistory) | **sí** | any-auth |

**Ejemplos**:
- Carga inicial post-login: `GET /api/v1/users/me?include=profile,stats`
- SecurityScreen: `GET /api/v1/users/me?include=security,sessions` (requiere step-up reciente)
- VehiclesScreen: `GET /api/v1/users/me?include=vehicles` (o usar cache local)
- ProviderHubScreen: `GET /api/v1/users/me?include=profile,provider,stats`
- DEV inspector: `GET /api/v1/users/me?include=profile,vehicles,favorites,addresses,payment_methods,preferences,notifications,stats,provider,security,sessions`

#### 2.2.2 Shape de la respuesta

```json
{
  "data": {
    "user": {
      "id": "uuid",
      "email": "yampi@example.com",
      "email_verified": true,
      "phone": "+15551234567",
      "phone_verified": true,
      "role": "client",
      "available_roles": ["client", "detailer"],
      "created_at": "2024-09-01T10:00:00Z"
    },
    "verification_badges": {
      "email": true,
      "phone": true,
      "identity": false,
      "background_check": false
    },
    "profile": {
      "first_name": "Yampier",
      "last_name": "Hernandez",
      "full_name": "Yampier Hernandez",
      "pronouns": "he/him",
      "avatar_url": "https://d111.cloudfront.net/avatars/...?signature=...",
      "cover_url": null,
      "language": "en",
      "timezone": "America/Indiana/Indianapolis"
    },
    "stats": {
      "total_bookings": 14,
      "total_spent_cents": 124500,
      "favorite_provider_id": "uuid",
      "vehicles_total": 2,
      "favorites_total": 3,
      "member_since": "2024-09-01"
    },
    "security": {
      "has_password": true,
      "two_factor_enabled": false,
      "passkeys_count": 1,
      "last_password_change": "2026-03-25T10:00:00Z",
      "last_login_at": "2026-05-14T09:00:00Z",
      "step_up_required": false,
      "active_sessions_count": 2,
      "recent_failed_attempts": 0
    },
    "sessions": [
      {
        "id": "uuid",
        "device_name": "iPhone 13",
        "user_agent": "RaycarwashApp/1.4.2 iOS/17.2",
        "ip_address": "192.168.1.1",
        "ip_location": "Miami, FL (approx)",
        "is_current": true,
        "created_at": "2026-05-14T08:00:00Z",
        "last_seen_at": "2026-05-14T10:00:00Z"
      }
    ],
    "provider": {
      "business_name": "Yampi Detailing",
      "display_name": "Yampi",
      "tagline": "Ceramic specialist - Fort Wayne",
      "bio": "...",
      "verification_status": "approved",
      "rating": 4.9,
      "total_jobs": 82,
      "is_accepting_bookings": true
    },
    "vehicles": [ /* objetos Vehicle simplificados (id, make, model, year, color, plate, photo_url, is_default) */ ],
    "addresses": [ /* objetos UserAddress simplificados */ ],
    "payment_methods": [ /* {id, brand, last4, exp_month, exp_year, is_default} */ ],
    "favorites": [ /* providers favoritos simplificados */ ],
    "preferences": { "default_vehicle_id": "uuid", "default_address_id": "uuid", "marketing_opt_in": false, "frequency_preference": "monthly" },
    "notifications": { "preferences": { /* topic × channel */ }, "quiet_hours_start": "22:00", "quiet_hours_end": "07:00" }
  },
  "meta": {
    "includes": ["profile", "stats", "security", "sessions"],
    "step_up_recent": true
  },
  "links": {
    "self": "/api/v1/users/me?include=profile,stats,security,sessions"
  }
}
```

**Reglas**:
- `user` y `verification_badges` SIEMPRE están presentes (derivación barata, sin query extra).
- Cualquier otro bloque está presente **solo si se pidió** explícitamente en `include`.
- `meta.includes` lista los bloques que efectivamente se incluyeron — útil para que el cliente sepa qué cachear y qué refetchear después.
- Si el cliente pide `include=provider` y el user NO es detailer → el bloque `provider` se omite (no error), y `meta.includes` no lo lista. Esto evita romper UIs con role-switch en vuelo.

#### 2.2.3 Mapeo a entidades existentes (sin duplicación)

| Bloque | Fuente backend |
|---|---|
| `user` | `User` (id, email, phone_number, email_verified, is_verified, active_role, user_roles, created_at) |
| `verification_badges` | derivado de `User.is_verified`, `phone_verified` (flag implícito), `ProviderProfile.verification_status`, background_check_consent |
| `profile` | `User.full_name` (split o concat según vista), avatar_s3_key (firma URL), `User.preferred_language`, timezone (de ProviderProfile o default) |
| `vehicles` | `Vehicle` filtrado por owner_id, con photo URL firmada |
| `favorites` | `ClientFavorite` joined con `User`/`ProviderProfile` del favorito |
| `sessions` | `RefreshToken` activos + último entry de `UserLoginHistory` por session → `Session` shape (requiere step-up) |
| `security` | `User` (password_hash existe), `TotpCredential.enabled`, count `WebAuthnCredential`, last `password_change` audit entry, último `UserLoginHistory.was_successful=true`, `last_step_up_at` (requiere step-up) |
| `provider` | `ProviderProfile` (display_name, business_name, tagline, verification_status, average_rating, total_reviews → renombrado a `total_jobs` en respuesta, is_accepting_bookings) |
| `addresses` | `UserAddress` |
| `payment_methods` | `PaymentMethod` (sync local de Stripe) |
| `preferences` | `ClientProfile` (default_vehicle_id, default_address_id, marketing_email_opt_in, frequency_preference) |
| `notifications` | `NotificationPreference` |
| `stats` | denormalizado: `ClientProfile.total_appointments_count`, `total_spent_cents` (NUEVO denormalizado), `ClientProfile.default_provider_id` (renombrado a favorite_provider_id), counts cheap (vehicles, favorites) |

**Nueva columna denormalizada**: `ClientProfile.total_spent_cents` (BIGINT default 0) — actualizada por trigger PostgreSQL en cada `payment_ledger` entry tipo CAPTURE. Evita SUM(amount_cents) en cada `?include=stats`.

#### 2.2.4 Step-up enforcement sobre `include`

> **🆕 CAMBIO** — Step-up ahora se aplica al **valor del `include`**, no a un endpoint separado.

Reglas:
- `include=security` ó `include=sessions` → el endpoint chequea `require_step_up()` antes de poblar esos bloques.
- Si **no hay step-up reciente**:
  - **Comportamiento default (recomendado)**: responder **401 `step_up_required`** con header `WWW-Authenticate: StepUp realm="raycarwash"` y `meta.requires_step_up: ["security", "sessions"]`. Cliente abre modal de re-auth y reintenta.
  - **Alternativa configurable** via query param `?on_step_up=skip`: omitir bloques sensibles, marcar `meta.skipped_due_to_step_up: ["security", "sessions"]`, responder 200 con los demás bloques poblados. Útil para refresh background sin interrumpir UI.
- Includes no sensibles (`profile`, `vehicles`, etc.) NO afectados — siempre se sirven si están en `include`.

Esto significa que `GET /auth/security` y `GET /auth/sessions` **siguen existiendo** (ver §2.1.5) para casos administrativos y para revocaciones por ID. Pero la **vista principal de SecurityScreen** consume el Hub: `GET /users/me?include=security,sessions` (con step-up). Sin duplicación de lógica — los services del dominio `auth` exponen helpers reutilizados tanto por el Hub como por los endpoints standalone.

#### 2.2.5 Evolución futura

Nuevos sub-recursos arrancan opt-in (`?include=loyalty`, `?include=referrals`, etc.) — el contrato default no rompe clientes. Para versionado más estricto, considerar `Accept-Profile-Version: 2026-05-01` header (futuro, no urgente).

### 2.3 `/api/v1/users/me/active-role` — Cambio de rol activo

**Rename de `/role` → `/active-role`**: refleja que es una propiedad del usuario, no un recurso "Role" aparte. Más claro.

| Método | Endpoint | Descripción | Roles | RL |
|---|---|---|---|---|
| GET | `/api/v1/users/me/active-role` | Devuelve `{active_role, available_roles}` | any-auth | 60/min |
| PATCH | `/api/v1/users/me/active-role` | Body: `{role: "client"\|"detailer"}`. Setea `active_role`. **Rota refresh token** (revoca el anterior, emite uno nuevo) y emite nuevo access token. Respuesta: `{access_token, refresh_token, active_role}`. | dual-role | 60/h |

**Decisión de seguridad (rotación de refresh)**: en cambio de rol, **se rota el refresh token igual que en cambio de password**. Razón: un refresh token robado antes del switch podría seguir emitiendo access tokens con el rol viejo durante 7 días. Rotar elimina esa ventana. La complejidad es baja (mismo flujo que `RefreshTokenRepository.rotate_family()`) y el frontend ya maneja refresh rotation en el interceptor.

### 2.4 `/api/v1/users/me/avatar` y `/cover`

| Método | Endpoint | Descripción | Roles | RL |
|---|---|---|---|---|
| POST | `/api/v1/users/me/avatar/upload-url` | Body: `{mime_type, size_bytes}`. Devuelve presigned PUT URL S3 + s3_key. Valida mime ∈ {jpeg,png,webp} y size ≤ 5MB. | any-auth | 10/h |
| POST | `/api/v1/users/me/avatar` | Body: `{s3_key}`. HEAD el objeto S3, valida mime real, setea `User.avatar_s3_key`. Side effect: borra avatar anterior async. | any-auth | 10/h |
| DELETE | `/api/v1/users/me/avatar` | Borra S3 + null en User | any-auth | 10/h |
| POST | `/api/v1/users/me/cover/upload-url` | Cover image (solo detailers) | detailer | 10/h |
| POST | `/api/v1/users/me/cover` | Confirma cover | detailer | 10/h |
| DELETE | `/api/v1/users/me/cover` | | detailer | 10/h |

### 2.5 `/api/v1/users/me/email` y `/phone` — Cambios con verificación

| Método | Endpoint | Descripción | Roles | RL |
|---|---|---|---|---|
| POST | `/api/v1/users/me/email/change-request` | Body: `{new_email, current_password}`. Crea `PendingContactChange` (TTL 1h, token 64-char). Envía link al **nuevo** email. NO toca User aún. | step-up | 3/h |
| POST | `/api/v1/users/me/email/change-confirm` | Body: `{token}`. Consume token. Update `User.email`, bump `token_version` (invalida sessions). Email anti-takeover al viejo. | público | 10/h |
| POST | `/api/v1/users/me/phone/change-request` | Body: `{new_phone, current_password}`. Envía OTP 6 dígitos SMS (Twilio). TTL 10min, max 5 intentos. | step-up | 3/h |
| POST | `/api/v1/users/me/phone/change-verify` | Body: `{otp}`. Update `phone_number` + `phone_hash`. Audit. | any-auth | 10/h |

### 2.6 `/api/v1/users/me/security` — MOVIDO a `/api/v1/auth/*`

**Decisión arquitectónica final**: TODA la gestión de credenciales, sesiones, passkeys y 2FA vive bajo `/api/v1/auth/*` (ver sección 2.1.5). `/users/me` se enfoca exclusivamente en datos de perfil y preferencias del usuario. Esto cumple SRP estricto: identidad/autenticación ≠ persona/perfil, y evita que el dominio `users` dependa del dominio `auth` para lógica que ya vive correctamente en auth.

Sub-recursos relacionados a seguridad **NO existen** bajo `/users/me/security/*`. Si el frontend necesita el resumen consolidado:
- `GET /api/v1/auth/security` — resumen completo
- `GET /api/v1/users/me?include=security_summary` — embed en aggregate (delega internamente al mismo service de auth)

### 2.7 `/api/v1/users/me/vehicles`

| Método | Endpoint | Descripción | Roles | RL |
|---|---|---|---|---|
| GET | `/api/v1/users/me/vehicles?limit=&cursor=` | Lista vehículos del owner | any-auth | 60/h |
| POST | `/api/v1/users/me/vehicles` | Crea vehículo (con VIN lookup NHTSA opcional) | client | 20/h |
| GET | `/api/v1/users/me/vehicles/{id}` | Detalle | self-owner | 60/h |
| PATCH | `/api/v1/users/me/vehicles/{id}` | Update parcial | self-owner | 30/h |
| DELETE | `/api/v1/users/me/vehicles/{id}` | 409 si tiene appointments activos | self-owner | 10/h |
| POST | `/api/v1/users/me/vehicles/{id}/photos/upload-url` | Presigned URL (max 4 fotos por vehicle) | self-owner | 20/h |
| POST | `/api/v1/users/me/vehicles/{id}/photos` | Confirma upload | self-owner | 20/h |
| DELETE | `/api/v1/users/me/vehicles/{id}/photos/{photo_id}` | | self-owner | 20/h |
| PATCH | `/api/v1/users/me/vehicles/{id}/default` | Setea `ClientProfile.default_vehicle_id` | client | 10/h |

### 2.8 `/api/v1/users/me/payment-methods`

| Método | Endpoint | Descripción | Roles | RL |
|---|---|---|---|---|
| GET | `/api/v1/users/me/payment-methods` | Lista (sync con Stripe vía webhooks + lazy refresh) | any-auth | 60/h |
| POST | `/api/v1/users/me/payment-methods/setup-intent` | Body opcional `{}`. Header `Idempotency-Key`. Devuelve `{client_secret}` para Stripe SDK. | step-up | 10/h |
| GET | `/api/v1/users/me/payment-methods/{id}` | Detalle | self-owner | 60/h |
| PATCH | `/api/v1/users/me/payment-methods/{id}/default` | Marca default | self-owner | 20/h |
| DELETE | `/api/v1/users/me/payment-methods/{id}` | Detach en Stripe + soft delete local | step-up | 10/h |

### 2.9 `/api/v1/users/me/addresses`

| Método | Endpoint | Descripción | Roles | RL |
|---|---|---|---|---|
| GET | `/api/v1/users/me/addresses` | Lista | any-auth | 60/h |
| POST | `/api/v1/users/me/addresses` | Crea (geocoding automático → lat/lng + h3_index_r9) | any-auth | 20/h |
| GET | `/api/v1/users/me/addresses/{id}` | Detalle | self-owner | 60/h |
| PATCH | `/api/v1/users/me/addresses/{id}` | Update parcial | self-owner | 30/h |
| DELETE | `/api/v1/users/me/addresses/{id}` | 409 si es default y user tiene appointments futuros | self-owner | 10/h |
| PATCH | `/api/v1/users/me/addresses/{id}/default` | Setea default | self-owner | 20/h |

### 2.10 `/api/v1/users/me/favorites` (client)

| Método | Endpoint | Descripción | Roles | RL |
|---|---|---|---|---|
| GET | `/api/v1/users/me/favorites/providers` | Lista detailers favoritos | client | 60/h |
| POST | `/api/v1/users/me/favorites/providers/{provider_user_id}` | Add | client | 60/h |
| DELETE | `/api/v1/users/me/favorites/providers/{provider_user_id}` | Remove | client | 60/h |

### 2.11 `/api/v1/users/me/client-preferences`

| Método | Endpoint | Descripción | Roles | RL |
|---|---|---|---|---|
| GET | `/api/v1/users/me/client-preferences` | default_vehicle_id, default_address_id, marketing_opt_in, frequency_preference | client | 60/h |
| PUT | `/api/v1/users/me/client-preferences` | Reemplaza | client | 30/h |

### 2.12 `/api/v1/users/me/provider-profile` y sub-recursos (detailer)

| Método | Endpoint | Descripción | Roles | RL |
|---|---|---|---|---|
| POST | `/api/v1/users/me/provider-profile` | Activa modo provider (client → dual-role). Crea ProviderProfile vacío, asigna role detailer. NO marca accepting hasta KYC. | client | 1/día |
| GET | `/api/v1/users/me/provider-profile` | Devuelve ProviderProfile + stats (earnings, total_services) | detailer | 60/h |
| PATCH | `/api/v1/users/me/provider-profile` | Update bio, display_name, business_name, tagline, social_links, working_hours, service_radius, specialties | detailer | 30/h |
| POST | `/api/v1/users/me/provider-profile/deactivate` | Pausa modo (mantiene data, niega bookings). | detailer | 1/día |
| PATCH | `/api/v1/users/me/provider-status` | Body `{is_accepting_bookings: bool}`. Requiere `verification_status=approved`. | detailer | 30/h |
| GET | `/api/v1/users/me/provider-services` | Lista detailer_services | detailer | 60/h |
| POST | `/api/v1/users/me/provider-services` | Body `{service_id, custom_price_cents?}`. Add. | detailer | 30/h |
| PATCH | `/api/v1/users/me/provider-services/{id}` | Toggle is_active, custom_price | detailer | 30/h |
| DELETE | `/api/v1/users/me/provider-services/{id}` | | detailer | 30/h |
| GET | `/api/v1/users/me/provider-portfolio` | Fotos before/after | detailer | 60/h |
| POST | `/api/v1/users/me/provider-portfolio/upload-url` | Presigned (max 30 fotos) | detailer | 30/h |
| POST | `/api/v1/users/me/provider-portfolio` | Confirma + tags `before|after`, optional caption | detailer | 30/h |
| DELETE | `/api/v1/users/me/provider-portfolio/{id}` | | detailer | 30/h |
| GET | `/api/v1/users/me/provider-documents` | Lista docs propios (insurance, license, certs) | detailer | 60/h |
| POST | `/api/v1/users/me/provider-documents/upload-url` | Presigned (SSE-KMS bucket privado) | detailer | 10/h |
| POST | `/api/v1/users/me/provider-documents` | Confirma + type + expires_at | detailer | 10/h |
| DELETE | `/api/v1/users/me/provider-documents/{id}` | | step-up | 10/h |
| POST | `/api/v1/users/me/provider-verification` | Inicia Stripe Identity session | detailer | 3/día |
| GET | `/api/v1/users/me/provider-verification` | Status + última sesión | detailer | 60/h |
| GET | `/api/v1/users/me/provider-achievements` | Lista badges otorgados | detailer | 60/h |
| POST | `/api/v1/users/me/provider-location` | Body `{lat, lng}`. Update GPS + H3 index. Solo activo durante shift. | detailer | 120/min |

### 2.13 `/api/v1/users/me/notifications`

| Método | Endpoint | Descripción | Roles | RL |
|---|---|---|---|---|
| GET | `/api/v1/users/me/notifications` | NotificationPreference + lista de devices | any-auth | 60/h |
| PUT | `/api/v1/users/me/notifications` | Update preferences + quiet_hours. Topic `security` siempre on. | any-auth | 30/h |
| GET | `/api/v1/users/me/devices` | Lista DeviceToken registrados | any-auth | 60/h |
| POST | `/api/v1/users/me/devices` | Registra Expo token (idempotente por token value) | any-auth | 20/h |
| DELETE | `/api/v1/users/me/devices/{id}` | Unregister | self-owner | 20/h |

### 2.14 `/api/v1/users/me/privacy`

| Método | Endpoint | Descripción | Roles | RL |
|---|---|---|---|---|
| GET | `/api/v1/users/me/privacy` | profile_visibility, show_last_active, show_total_appointments, show_reviews_received, share_realtime_location, marketing_opt_in, analytics_opt_in | any-auth | 60/h |
| PUT | `/api/v1/users/me/privacy` | Update | any-auth | 30/h |

### 2.15 Historiales especializados (auditoría granular)

**Decisión**: en vez de un único feed genérico, exponemos endpoints especializados por tipo de historial. Cada uno con su propio filtrado, paginación cursor, y shape optimizado para la pantalla que lo consume. El feed unificado se mantiene como **resumen opcional en el hub**, no como única fuente.

| Método | Endpoint | Descripción | Roles | RL |
|---|---|---|---|---|
| GET | `/api/v1/users/me/appointments/history?limit=&cursor=&status=&from=&to=&vehicle_id=` | Citas pasadas y futuras con detalles completos (service, vehicle, provider, payment, review). Filtros multi-status. | any-auth | 300/h |
| GET | `/api/v1/users/me/payments/history?limit=&cursor=&status=&from=&to=` | Transacciones con receipt URLs, refunds, method usado | any-auth | 300/h |
| GET | `/api/v1/users/me/vehicles/history?include_deleted=true` | **Solo eventos del vehículo como recurso**: cuándo se añadió, cuándo se editó (qué campos), photo_uploaded, photo_deleted, deleted. **NO incluye appointments** (esos se consultan via `/appointments/history?vehicle_id=`). | any-auth | 60/h |
| GET | `/api/v1/users/me/profile-changes?limit=&cursor=&action=` | Cambios en datos personales (avatar, nombre, dirección, preferences, métodos de pago, notificaciones, privacy). Lee `audit_log` filtrado a entity_type del user. | any-auth | 300/h |
| GET | `/api/v1/users/me/reviews?role=given\|received&limit=&cursor=` | Reviews dadas (client) o recibidas (detailer) | role-aware | 60/h |
| GET | `/api/v1/users/me/activity?limit=20&cursor=&type=` | **Feed unificado (resumen opcional)**. Tipos: `appointment`, `payment`, `review`, `profile_change`. **NO incluye `security`** — eventos de seguridad viven exclusivamente en `/auth/history` (fuente de verdad única, sin duplicación). | any-auth | 300/h |

**Ejemplo `GET /users/me/appointments/history`**:
```json
{
  "data": [
    {
      "id": "apt_123",
      "scheduled_at": "2026-05-10T14:00:00Z",
      "status": "completed",
      "completed_at": "2026-05-10T16:30:00Z",
      "service": { "id": "svc_1", "name": "Lavado Premium", "duration_minutes": 90, "price_cents": 8900 },
      "vehicle": { "id": "veh_1", "make": "Toyota", "model": "Camry", "year": 2020, "license_plate": "ABC123", "photo_url": "https://..." },
      "provider": { "id": "prov_1", "display_name": "Juan Detailing", "avatar_url": "https://...", "rating": 4.9 },
      "payment": { "id": "pay_456", "amount_cents": 8900, "status": "captured", "receipt_url": "https://..." },
      "review": { "rating": 5, "comment": "Excelente trabajo", "created_at": "2026-05-11T10:00:00Z" }
    }
  ],
  "meta": { "cursor": "...", "has_more": true, "limit": 20 }
}
```

**Vehicle timeline (`vehicles/history` shape)** — solo eventos del vehículo como recurso:
```json
{
  "data": [
    {
      "vehicle": { "id": "veh_1", "make": "Toyota", "model": "Camry", "year": 2020, "is_deleted": false },
      "timeline": [
        { "type": "added", "occurred_at": "2024-09-01T10:00:00Z" },
        { "type": "photo_uploaded", "occurred_at": "2024-09-02T11:00:00Z", "photo_id": "..." },
        { "type": "edited", "occurred_at": "2025-01-15T08:00:00Z", "field": "color", "old": "white", "new": "pearl_white" },
        { "type": "photo_deleted", "occurred_at": "2025-03-10T12:00:00Z", "photo_id": "..." },
        { "type": "set_as_default", "occurred_at": "2025-06-01T09:00:00Z" }
      ]
    }
  ]
}
```

Para historial de citas de un vehículo: usar `GET /users/me/appointments/history?vehicle_id={id}`. Separación clara: `/vehicles/history` audita el vehículo como entidad; `/appointments/history` audita las citas (filtrable por vehículo).

### 2.15b `/api/v1/users/me/analytics/*` — Análisis (Fase 9)

| Método | Endpoint | Descripción | Roles |
|---|---|---|---|
| GET | `/api/v1/users/me/analytics/service-frequency?vehicle_id=` | Frecuencia de servicios: avg_days_between_washes, count_per_month últimos 12 meses, most_common_service | client |
| GET | `/api/v1/users/me/analytics/upcoming-reminders` | Recordatorios derivados: "Vehículo X no ha sido lavado en 45 días (típico: 25)". Datos para mostrar CTA. | client |
| GET | `/api/v1/users/me/analytics/monthly-spending?year=` | Total gastado por mes (12-month rolling), breakdown por servicio | client |
| GET | `/api/v1/users/me/analytics/earnings?from=&to=` | (detailer) Earnings agregados, breakdown por servicio, días, vehículos | detailer |
| GET | `/api/v1/users/me/analytics/rating-trend` | (detailer) Rating timeline mensual | detailer |

### 2.16 `/api/v1/users/me/account` — Lifecycle (GDPR)

| Método | Endpoint | Descripción | Roles | RL |
|---|---|---|---|---|
| POST | `/api/v1/users/me/account/exports` | Crea DataExportRequest. Worker async. | step-up | 1/día |
| GET | `/api/v1/users/me/account/exports` | Lista exports recientes | any-auth | 30/h |
| GET | `/api/v1/users/me/account/exports/{id}` | Status + presigned download URL si READY | self-owner | 60/h |
| POST | `/api/v1/users/me/account/deletion-request` | Crea AccountDeletionRequest (scheduled +30d). Body `{current_password, reason?}`. | step-up | 1/día |
| GET | `/api/v1/users/me/account/deletion-request` | Status si existe | any-auth | 60/h |
| DELETE | `/api/v1/users/me/account/deletion-request` | Cancela | any-auth | 5/h |

### 2.17 `/api/v1/users/{user_id}/public` — Vista pública

| Método | Endpoint | Descripción | Roles | RL |
|---|---|---|---|---|
| GET | `/api/v1/users/{user_id}/public` | Vista respetando PrivacySetting. Si target.profile_visibility=PRIVATE → 404 (no 403, no leak). Si AUTHENTICATED y caller no autenticado → 401. | público / any-auth | 120/h |

---

## 3. Contrato de respuestas y errores (uniforme)

### 3.1 Envelope de éxito

```json
{
  "data": { ... },        // recurso individual, lista, u objeto compuesto (Profile Hub)
  "meta": {               // metadatos opcionales
    "cursor": "next_cursor_opaque",
    "has_more": true,
    "limit": 20,
    "includes": ["profile", "stats"],          // 🆕 Profile Hub: bloques efectivos
    "requires_step_up": ["security"],          // 🆕 si 401 step_up_required
    "skipped_due_to_step_up": ["sessions"]     // 🆕 si ?on_step_up=skip
  },
  "links": {              // HATEOAS opcional
    "self": "/api/v1/users/me/vehicles?cursor=xyz",
    "next": "/api/v1/users/me/vehicles?cursor=abc"
  }
}
```

**Tres formas de `data`**:
- **Lista** (`GET /users/me/vehicles`): `data` es array.
- **Recurso singular** (`GET /users/me/vehicles/{id}`): `data` es objeto plano.
- **Objeto compuesto** (`GET /users/me` — Profile Hub): `data` es objeto con bloques nombrados (`user`, `profile`, `vehicles`, etc.). `meta.includes` documenta qué bloques están presentes.

Para acciones sin body (DELETE): **204 No Content** sin envelope.

### 3.2 Envelope de error

```json
{
  "error": {
    "code": "validation_failed",
    "message": "The request contains invalid fields",
    "details": [
      { "field": "email", "reason": "must be a valid email address" }
    ],
    "request_id": "req_01HXY8M..."
  }
}
```

### 3.3 Códigos de error estandarizados

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `bad_request` | JSON inválido, params malformados |
| 401 | `authentication_required` | Token ausente o inválido |
| 401 | `step_up_required` | Necesita re-auth reciente. Header `WWW-Authenticate: StepUp realm="raycarwash"`. |
| 403 | `permission_denied` | Token válido pero no autorizado para el recurso |
| 403 | `onboarding_incomplete` | Onboarding pendiente |
| 403 | `kyc_required` | Acción requiere `verification_status=approved` |
| 404 | `resource_not_found` | Recurso inexistente o invisible por privacy |
| 409 | `conflict` | Estado actual incompatible (ej: delete vehicle con appointments activos) |
| 409 | `already_exists` | Único violado (ej: email duplicado) |
| 410 | `gone` | Token expired/consumed, endpoint deprecated |
| 422 | `validation_failed` | Pydantic validation error |
| 423 | `account_locked` | Locked por failed attempts o pending deletion |
| 429 | `rate_limit_exceeded` | Headers `X-RateLimit-*` + `Retry-After` |
| 500 | `internal_error` | Bug. Logueado + alertado. |
| 503 | `service_unavailable` | Stripe/S3/Twilio down |

### 3.4 Headers estándar

**Request**:
- `Authorization: Bearer <jwt>`
- `Idempotency-Key: <client-uuid>` (POST/PATCH sensibles)
- `X-Client-Version: 1.4.2` (opcional, para deprecation tracking)
- `Accept-Language: en` (opcional, override de user.preferred_language)

**Response**:
- `X-Request-ID: req_01HXY...` (tracing, replicado en error.request_id)
- `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- `Deprecation: true` + `Sunset: 2026-08-01` (endpoints en transición)
- `Cache-Control` (`private, max-age=60` para `/users/me`)

### 3.5 Paginación cursor-based (uniforme)

```
GET /api/v1/users/me/activity?limit=20&cursor=eyJ...

Response:
{
  "data": [...],
  "meta": {
    "cursor": "eyJ...next",       // next page cursor (null si !has_more)
    "prev_cursor": "eyJ...prev",  // optional, presente solo si endpoint soporta backward nav
    "has_more": true,
    "limit": 20
  }
}
```

Cursor opaco (base64 de `{created_at, id, direction}`). Backend valida y decodifica. Cliente trata como string opaco. `prev_cursor` se incluye solo en endpoints donde la UI necesita "ir atrás" sin keep-stack (ej: activity feed donde el user puede saltar a una página específica y volver).

---

## 4. Arquitectura backend

### 4.1 Reorganización de dominios

```
backend/domains/
├── auth/                    # endpoints /api/v1/auth/*  (mantiene su estructura)
│   ├── models.py            # RBAC, tokens, WebAuthn (existente, se mantiene)
│   ├── schemas.py
│   ├── service.py
│   ├── routers/             # core, social, webauthn, sessions, password, email_verification
│   └── ...
├── users/                   # endpoints /api/v1/users/*  ← DOMINIO EXPANDIDO
│   ├── __init__.py
│   ├── models/              # split por sub-recurso para mantenibilidad
│   │   ├── __init__.py
│   │   ├── user.py          # User (existente + columnas nuevas)
│   │   ├── client_profile.py
│   │   ├── address.py       # NUEVO UserAddress
│   │   ├── payment_method.py # NUEVO
│   │   ├── document.py      # NUEVO
│   │   ├── notification_preference.py # NUEVO
│   │   ├── privacy_setting.py # NUEVO
│   │   ├── pending_contact_change.py # NUEVO
│   │   ├── client_favorite.py # NUEVO
│   │   ├── account_deletion_request.py # NUEVO
│   │   └── data_export_request.py # NUEVO
│   ├── schemas/             # idem split
│   ├── repositories/        # idem split
│   ├── services/            # idem split + UserAggregateService (orquesta GET /me)
│   ├── routers/             # split por sub-recurso → ensamble en users_router
│   │   ├── __init__.py      # users_router que incluye todos los sub-routers
│   │   ├── me.py            # GET/PATCH /users/me, /role, /avatar, /cover
│   │   ├── contact.py       # /email/*, /phone/*
│   │   ├── security.py      # /security/*
│   │   ├── vehicles.py      # /vehicles/* (delega a domains.vehicles.service)
│   │   ├── payment_methods.py
│   │   ├── addresses.py
│   │   ├── favorites.py
│   │   ├── client_preferences.py
│   │   ├── provider_profile.py # /provider-profile, /provider-status
│   │   ├── provider_services.py
│   │   ├── provider_portfolio.py
│   │   ├── provider_documents.py
│   │   ├── provider_verification.py
│   │   ├── provider_achievements.py
│   │   ├── provider_location.py
│   │   ├── notifications.py  # /notifications, /devices
│   │   ├── privacy.py
│   │   ├── activity.py       # /activity, /reviews
│   │   ├── account.py        # /account/exports, /account/deletion-request
│   │   └── public.py         # GET /users/{id}/public
│   └── adapters/
│       ├── s3_adapter.py
│       └── stripe_payment_adapter.py
├── providers/               # se mantiene; refactor: router público (search detailers) sigue aquí.
│                            # /api/v1/detailers/me se deprecara, lógica migra a users/routers/provider_profile.py
│                            # ProviderProfile model sigue viviendo aquí (reutilizado por users domain)
├── vehicles/                # CRUD privado migra a users/routers/vehicles.py (delega a service)
│                            # Vehicle model sigue aquí
├── appointments/, services_catalog/, payments/, matching/, reviews/, notifications/,
│   audit/, admin/, realtime/ — sin cambios estructurales (solo extensión de AuditAction enum)
```

**Patrón crítico**: el dominio `users/` **compone** los servicios de `providers`, `vehicles`, `payments`, `notifications`. NO duplica modelos. Los routers `/users/me/provider-*` instancian `ProviderService` y delegan; solo la capa de presentación cambia.

### 4.2 Layers (responsabilidades estrictas)

| Layer | Responsabilidad | NO debe |
|---|---|---|
| **router** | Validar JWT + dependency injection, parsear DTOs, llamar service, mapear excepciones HTTP | Tocar DB, llamar S3/Stripe directamente, contener lógica |
| **service** | Lógica de negocio, orquestación de repos + adapters, eventos al bus, side effects | Conocer FastAPI (`Request`, `Response`, `HTTPException`) |
| **repository** | CRUD puro, queries SQL, sin reglas de negocio | Llamar otros services |
| **schemas** | Validación Pydantic in/out, alias para envelope `{data}` | Contener lógica |
| **adapters** | Integración con servicios externos (S3, Stripe, Twilio, NHTSA) | Conocer modelos SQLAlchemy |

### 4.3 Middleware global (Fase 0)

Orden en `main.py`:
1. **RequestID middleware** — genera `request_id` UUID, attach a request state, echo en response.
2. **Logging middleware** — log estructurado JSON: `{request_id, method, path, user_id, status, latency_ms}`.
3. **CORS** (existente).
4. **Auth middleware** — extrae user del JWT, attach a request.state.user (None si no auth).
5. **Rate limiter** (slowapi existente, extender para usar user_id + IP combinados).
6. **Step-up validator** — dependency que chequea `last_step_up_at` en Redis `auth:stepup:{user_id}` vs `now() - 5min`. Si stale → 401 `step_up_required`.
7. **Idempotency middleware** — para POST/PATCH/DELETE: si `Idempotency-Key` presente, cachea response 24h por `(user_id, key, method, path)`.
8. **Response envelope: explícito por endpoint** — NO middleware. Cada endpoint declara `response_model=Envelope[T]` con T = schema concreto. Esto evita overhead de middleware, mantiene tipos explícitos en OpenAPI, y es más predecible. `Envelope[T]` es un Pydantic generic en `shared/schemas.py` con `data: T`, `meta: Meta | None`, `links: dict | None`.
9. **Exception handlers** — captura `ValidationError`, `HTTPException`, custom `BusinessError` y los mapea al envelope de error.

### 4.4 Versionado y deprecación

- Prefijo `/api/v1/` para todo (alias en backwards-compat: `/auth/*` redirige a `/api/v1/auth/*`).
- Cuando se necesite `/api/v2/` para breaking changes, ambos coexisten ≥ 6 meses.
- Endpoints deprecated retornan headers:
  - `Deprecation: true`
  - `Sunset: 2026-08-01` (RFC 8594)
  - `Link: </api/v1/users/me>; rel="successor-version"`
- Logging dedicado de uso de endpoints deprecated → métrica para saber cuándo es seguro eliminar.

---

## 5. Modelo de datos (entidades existentes + nuevas)

### 5.1 Existentes a EXTENDER

#### `User` (`domains/users/models/user.py`)
Nuevas columnas:
| Campo | Tipo | Justificación |
|---|---|---|
| `avatar_s3_key` | `str \| None` | Key en S3, URL se firma on-demand |
| `cover_s3_key` | `str \| None` | Solo detailers |
| `pronouns` | `str \| None` (20) | UX inclusivo |
| `preferred_language` | `str` default `"en"` | i18n-ready |
| `last_active_at` | `datetime \| None` | Para "última actividad" + privacy |
| `deleted_at` | `datetime \| None` | Soft delete |
| `active_role` | `str \| None` (`client` / `detailer`) | Reflejado en JWT al emitir tokens |
| `last_step_up_at` | `datetime \| None` | Step-up auth cache (opcional, alternativa a Redis) |

#### `ClientProfile`
| Campo | Tipo |
|---|---|
| `default_vehicle_id` | `UUID \| None` FK vehicles |
| `default_address_id` | `UUID \| None` FK user_addresses |
| `total_appointments_count` | `int` default 0 (denormalizado, actualizado por trigger o worker) |
| `marketing_email_opt_in` | `bool` default false |
| `frequency_preference` | `str \| None` (e.g., "weekly", "monthly") |

`service_address` se mantiene deprecated, migra gradual a `UserAddress`.

#### `ProviderProfile` (`domains/providers/models.py`)
| Campo | Tipo |
|---|---|
| `display_name` | `str \| None` (80) — público, distinto a legal_full_name |
| `business_name` | `str \| None` (120) |
| `tagline` | `str \| None` (140) |
| `social_links` | `JSONB \| None` — `{instagram, tiktok, website}` |
| `insurance_policy_number_encrypted` | `EncryptedType(String)` |
| `tax_id_encrypted` | `EncryptedType(String)` |
| `payout_method_id` | `str \| None` — Stripe Connect (futuro) |
| `cover_photo_s3_key` | `str \| None` |

### 5.2 Entidades NUEVAS (resumen — detalles en cada fase)

| Entidad | Vive en | Propósito |
|---|---|---|
| `UserAddress` | `domains/users/models/address.py` | Múltiples direcciones (home, work) con lat/lng + h3 |
| `PaymentMethod` | `domains/users/models/payment_method.py` | Espejo local de Stripe (solo IDs + last4 + brand) |
| `Document` | `domains/users/models/document.py` | KYC docs S3 (insurance, license, certs) |
| `NotificationPreference` | `domains/users/models/notification_preference.py` | Matrix channel × topic + quiet hours |
| `PrivacySetting` | `domains/users/models/privacy_setting.py` | profile_visibility, show_* flags |
| `PendingContactChange` | `domains/users/models/pending_contact_change.py` | Flujo email/phone verification |
| `ClientFavorite` | `domains/users/models/client_favorite.py` | Detailers favoritos |
| `AccountDeletionRequest` | `domains/users/models/account_deletion_request.py` | GDPR soft-delete + grace |
| `DataExportRequest` | `domains/users/models/data_export_request.py` | GDPR export |
| `ProviderPortfolioPhoto` | `domains/providers/models.py` (extend) | before/after photos |
| `ProviderAchievement` | `domains/providers/models.py` (extend) | Badges auto-otorgables |
| `VehiclePhoto` | `domains/vehicles/models.py` (extend) | Fotos del vehículo |
| `TotpCredential` | `domains/auth/models/totp_credential.py` | TOTP 2FA: secret encrypted, backup codes hashes |
| `UserLoginHistory` | `domains/auth/models/user_login_history.py` | Auditoría de logins (success + failed) |

#### `UserLoginHistory` — detalle

```python
class UserLoginHistory(Base):
    __tablename__ = "user_login_history"
    id: UUID (PK)
    user_id: UUID (FK users.id, cascade, indexed)
    login_at: datetime (UTC, default now, indexed)
    ip_address: str | None (45 chars — soporta IPv6)
    ip_location: str | None (denormalizado: "Miami, FL (approx)") — opcional, llenado por adapter MaxMind o ipapi
    user_agent: str | None (text)
    device_name: str | None (derivado de UA — "iPhone 13", "Pixel 7")
    auth_method: str  # "password", "google", "apple", "webauthn", "refresh"
    was_successful: bool default true
    failure_reason: str | None  # "invalid_password", "account_locked", "user_not_found", "2fa_failed"
    refresh_token_family_id: UUID | None (FK refresh_tokens.family_id) — para correlation con sesiones

    __table_args__ = (
        Index("idx_login_history_user_time", "user_id", "login_at"),
        Index("idx_login_history_failed", "user_id", "was_successful", "login_at"),
    )
```

**Retención**: worker mensual purga `was_successful=true AND login_at < now() - 12 months`, y `was_successful=false AND login_at < now() - 90 days`.

#### `AuditLog` — EXTENDER

El `AuditLog` existente (`domains/audit/models.py`) ya tiene `actor_id, action, entity_type, entity_id, created_at, stripe_metadata`. Necesita extender:

| Campo nuevo | Tipo | Justificación |
|---|---|---|
| `old_value` | `JSONB \| None` | Snapshot antes del cambio (PII redactado para email/phone) |
| `new_value` | `JSONB \| None` | Snapshot después |
| `ip_address` | `str \| None` (45) | Forensics |
| `user_agent` | `str \| None` | Forensics |
| `request_id` | `str \| None` (64) | Tracing — correlación con structured logs |

`stripe_metadata` se renombra a `metadata_` (genérico). Migración añade columnas, copia data y dropea columna vieja.

**Captura automática de ip/user_agent**: middleware `audit_context` setea `request.state.audit_ctx = {ip, user_agent, request_id}`. El `AuditLogger.log()` lee de ahí cuando construye la entry. Sin esto, los routers tendrían que pasar el contexto manualmente — frágil.

**Política de retención de `old_value`/`new_value`** (JSONB crecen rápido):
- **0–90 días**: valores completos retenidos.
- **>90 días**: campos sensibles redactados → `{"redacted": true, "fields": ["email", "phone_number", "address"]}`. Se mantiene `entity_type`, `action`, `created_at`, `actor_id`, `ip_address` — suficiente para auditoría legal.
- **>3 años**: entries no-security se archivan a cold storage (S3 + Glacier) y se borran de Postgres. Entries de security (logins, password_change, etc.) y financieras se retienen indefinidas para cumplimiento.
- **Worker `workers/audit_log_redactor.py`** cron mensual ejecuta la redacción + archive.

Tradeoff: la redacción rompe forensics post-90d, pero respeta GDPR data minimization. Si se requiere data más antigua, se recupera del export en S3.

(Schemas SQLAlchemy detallados en cada fase correspondiente.)

---

## 6. Seguridad transversal

### 6.1 Clasificación de datos

| Nivel | Campos | Tratamiento |
|---|---|---|
| **Públicos** | display_name, avatar, bio, rating, specialties | Cacheable, expuesto en `/users/{id}/public` |
| **PII básico** | full_name, email, phone_number, addresses | EncryptedType en BD; phone_hash HMAC para lookup |
| **PII sensible** | DOB, legal_full_name, tax_id, insurance_policy | EncryptedType; nunca en logs ni responses excepto endpoints de verification |
| **Financiero** | stripe_customer_id, payment_method_id, last4 | Stripe-only para data completa; localmente solo IDs |
| **Documentos** | KYC, license, insurance | S3 SSE-KMS, bucket privado, presigned TTL 1h |
| **Seguridad** | password_hash, refresh_token_hash, totp_secret, webauthn_public_key | Solo backend |

### 6.2 Step-up authentication

**🆕 Step-up se aplica en DOS lugares**:

**(A) Endpoints sensibles** (re-auth ≤ 5 min):
- `POST /api/v1/auth/password/change`
- `POST /api/v1/auth/two-fa/enroll`
- `DELETE /api/v1/auth/two-fa`
- `POST /api/v1/auth/two-fa/backup-codes/regenerate`
- `DELETE /api/v1/auth/sessions` (todas)
- `DELETE /api/v1/auth/passkeys/{id}`
- `POST /api/v1/users/me/email/change-request`
- `POST /api/v1/users/me/phone/change-request`
- `POST /api/v1/users/me/payment-methods/setup-intent`
- `DELETE /api/v1/users/me/payment-methods/{id}`
- `POST /api/v1/users/me/provider-profile` (activate)
- `POST /api/v1/users/me/provider-profile/deactivate`
- `DELETE /api/v1/users/me/provider-documents/{id}`
- `POST /api/v1/users/me/account/exports`
- `POST /api/v1/users/me/account/deletion-request`

**(B) `GET /users/me?include=...` con tokens sensibles** — Profile Hub:
- `include=security` requiere step-up.
- `include=sessions` requiere step-up.
- Otros tokens (`profile`, `vehicles`, `addresses`, `payment_methods` (lista), `favorites`, `preferences`, `notifications`, `stats`, `provider`) NO requieren step-up — son data de presentación, no operaciones críticas.

**Comportamiento sin step-up reciente**:
- Default → 401 `step_up_required` + `WWW-Authenticate: StepUp realm="raycarwash"` + body `{error: {code: "step_up_required"}, meta: {requires_step_up: ["security", "sessions"]}}`.
- Opt-in `?on_step_up=skip` → 200 con bloques sensibles omitidos + `meta.skipped_due_to_step_up: ["security", "sessions"]`. Útil para fetches background donde no se quiere interrumpir UX.

**Implementación con fallback (Redis primario + DB fallback)**:

1. **Primario — Redis**: key `auth:stepup:{user_id}` = `last_auth_at` ISO timestamp, TTL 5 min. Set en cada login exitoso, password verify, OAuth verify, passkey verify.
2. **Fallback — DB**: columna `User.last_step_up_at` (datetime UTC), actualizada en los mismos eventos. Sirve si Redis está caído o el key expiró por TTL pero la auth sigue siendo reciente.

```python
async def require_step_up(user: User = Depends(get_current_user)) -> User:
    threshold = datetime.now(UTC) - timedelta(minutes=5)
    # 1. Try Redis primary
    try:
        cached = await redis.get(f"auth:stepup:{user.id}")
        if cached and datetime.fromisoformat(cached) > threshold:
            return user
    except RedisConnectionError:
        logger.warning("Redis unavailable for step-up, using DB fallback", user_id=user.id)
    # 2. Fallback to DB column
    if user.last_step_up_at and user.last_step_up_at > threshold:
        return user
    # 3. Reject
    raise StepUpRequiredError()
```

Esto garantiza disponibilidad: un outage de Redis no bloquea operaciones sensibles si el usuario se autenticó recientemente. Tradeoff: la columna DB se actualiza en cada login/verify (1 UPDATE pequeño) — costo despreciable.

### 6.3 Audit logging extendido

Nuevos `AuditAction` enums (Fase 0):
- `PROFILE_UPDATED`, `AVATAR_CHANGED`, `COVER_CHANGED`
- `EMAIL_CHANGE_REQUESTED`, `EMAIL_CHANGED`
- `PHONE_CHANGE_REQUESTED`, `PHONE_CHANGED`
- `PASSWORD_CHANGED`
- `TWO_FA_ENABLED`, `TWO_FA_DISABLED`
- `PASSKEY_REGISTERED`, `PASSKEY_REVOKED`
- `SESSION_REVOKED`, `ALL_SESSIONS_REVOKED`
- `PAYMENT_METHOD_ADDED`, `PAYMENT_METHOD_REMOVED`, `PAYMENT_METHOD_DEFAULT_CHANGED`
- `ADDRESS_ADDED`, `ADDRESS_REMOVED`, `ADDRESS_DEFAULT_CHANGED`
- `VEHICLE_ADDED`, `VEHICLE_REMOVED`
- `FAVORITE_ADDED`, `FAVORITE_REMOVED`
- `DOCUMENT_UPLOADED`, `DOCUMENT_DELETED`
- `PROVIDER_MODE_ACTIVATED`, `PROVIDER_MODE_DEACTIVATED`
- `PROVIDER_PROFILE_UPDATED`, `PROVIDER_STATUS_CHANGED`
- `ROLE_SWITCHED`
- `NOTIFICATION_PREFS_UPDATED`, `PRIVACY_SETTINGS_UPDATED`
- `DATA_EXPORT_REQUESTED`, `DATA_EXPORT_READY`
- `ACCOUNT_DELETION_REQUESTED`, `ACCOUNT_DELETION_CANCELLED`, `ACCOUNT_ANONYMIZED`

### 6.4 Buenas prácticas reales (proyecto-específicas)

- **Anti-takeover en email change**: link al **nuevo** email + notification al **viejo** ("Your email was changed. Wasn't you? Recover").
- **Token version bump** en cambio password/email → invalida TODOS los access tokens.
- **No leak existence**: `/email/change-request` con email ajeno → 202 con **mensaje genérico** ("Si el correo es válido, te enviamos un enlace de verificación. Revisa tu bandeja."). NO usar texto que insinúe existencia. Internamente sí enviar email "Alguien intentó usar tu email" al dueño actual de esa dirección — pero esa notificación viaja por canal aparte, no por el response del endpoint.
- **S3 buckets separados**: `raycarwash-public-assets` (avatars, portfolio — CloudFront público) y `raycarwash-private-docs` (KYC, exports — SSE-KMS, presigned).
- **HEAD post-upload**: backend valida mime real, size, existencia antes de confirmar.
- **Idempotency-Key obligatorio** en Stripe SetupIntent, contact changes, deletion request.
- **Rate limit por user_id + por IP** (no solo IP — atacante con muchas IPs).
- **No exponer Stripe IDs en logs estructurados** (PCI scope).
- **No emitir nuevo refresh token en /role**: el refresh sigue, solo cambia el access (más simple, menos superficie).
- **Onboarding-completion lockout** (ya existe): aplica a `/auth/complete-profile`, NO a `/users/me/provider-profile` (POST activate). Activar provider después de completar onboarding sí está permitido — el lockout es solo del estado de onboarding inicial.

---

## 7. Frontend — 3 tracks

### 7.0 Alcance por track

| Track | Path | Stack | Profile feature scope |
|---|---|---|---|
| **Mobile (primario)** | `frontend/` | React Native 0.81 + Expo 54 + Zustand + axios | **100% del Profile**: hub, edit, security, vehicles, payments, addresses, favorites, provider mode, role-switcher, notifications, privacy, GDPR, historiales |
| **Admin web** | `web/` | Next.js 15 App Router + lib SWR | Vista admin de usuarios: lista, detalle, edición limitada (status, roles, deactivate), revisión de documentos KYC, vista de historial de seguridad por usuario |
| **Marketing/Customer web** | `marketing/` | Next.js + `[locale]` i18n + App Router | Mirror del flujo cliente en web: login, register, perfil basic (info + addresses + vehicles + payment methods), reserva de citas. Sin role-switcher de proveedor (los detailers operan vía mobile). Marketing pages se mantienen separadas. |

Cliente HTTP compartido (paquete `@raycarwash/api-client` o copy-paste hasta extraer): `Envelope` types, `ApiError`, request/response interceptors, refresh rotation logic. Idéntico contrato entre mobile y webs.

### 7.1 Mobile — RoleSwitcher (componente central)

```
┌─────────────────────────────┐
│  [👤 Cliente]  [🚗 Detailer] │  ← solo si available_roles.length > 1
└─────────────────────────────┘
```

- Tap → optimistic toggle visual → `PATCH /api/v1/users/me/role {role: "detailer"}` → guarda nuevo `access_token` → `navigation.reset({name: target_stack})`.
- Si fallo (KYC pendiente para detailer) → revert + toast "Complete KYC first" con CTA.
- Estado activo persistido en `SecureStore` y en `useAuthStore` (Zustand).

### 7.2 Pantallas

```
UserHubScreen (entry point, varía por active_role)
├── EditProfileScreen          (refactor: sections — Avatar, Basic, Contact, Language)
├── ContactChangeFlow stack    (ChangeEmail, ChangePhone, ConfirmOTP)
├── SecurityScreen
│   ├── PasswordChange
│   ├── TwoFactorSetup
│   ├── PasskeysScreen
│   └── SessionsScreen
├── VehiclesScreen + VehicleDetailScreen + VehiclePhotosScreen
├── PaymentMethodsScreen
├── AddressesScreen
├── FavoritesScreen (client)
├── ClientPreferencesScreen
├── ProviderHubScreen (detailer)
│   ├── ProviderProfileEditScreen
│   ├── ProviderServicesScreen
│   ├── ProviderPortfolioScreen
│   ├── ProviderDocumentsScreen
│   ├── ProviderAchievementsScreen
│   ├── ProviderVerificationScreen
│   └── ProviderStatusToggle
├── NotificationsScreen + DevicesScreen
├── PrivacyScreen
├── ActivityFeedScreen
└── AccountSettingsScreen (Export, Delete, Sign out)
```

### 7.3 State management + 🆕 Lazy loading de bloques del Hub

- **Zustand** se mantiene para auth (token, active_role) — síncrono, hot path.
- **React Query** (`@tanstack/react-query`) NUEVO para data del Profile Hub — invalidation por key, optimistic updates, retry, refetch on focus.
- **Cliente HTTP**: extend `apiClient` con interceptor de envelope + handler de `step_up_required`.

```ts
// services/api.ts (extension)
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const body = err.response?.data;
    if (body?.error?.code === "step_up_required") {
      throw new StepUpRequiredError(body.meta?.requires_step_up ?? []);
    }
    if (body?.error) {
      throw new ApiError(body.error, err.response.status);
    }
    throw err;
  }
);

// services/users.service.ts
export type HubInclude =
  | "profile" | "vehicles" | "favorites" | "sessions" | "security"
  | "provider" | "addresses" | "payment_methods" | "preferences"
  | "notifications" | "stats";

export async function getHub(includes: HubInclude[] = [], onStepUpSkip = false) {
  const params: any = {};
  if (includes.length) params.include = includes.join(",");
  if (onStepUpSkip) params.on_step_up = "skip";
  const { data } = await apiClient.get("/users/me", { params });
  return data; // { user, profile?, stats?, security?, sessions?, ... } + meta.includes
}

// hooks/useMe.ts — Profile Hub con lazy loading
import { useQuery } from "@tanstack/react-query";

export const useMe = (includes: HubInclude[] = ["profile", "stats"], opts?: { onStepUpSkip?: boolean }) => {
  const key = [...includes].sort();
  return useQuery({
    queryKey: ["users", "me", key.join(",")],
    queryFn: () => usersService.getHub(includes, opts?.onStepUpSkip),
    staleTime: 5 * 60_000,
  });
};
```

**Estrategia de carga por pantalla**:

| Pantalla | Includes | Notas |
|---|---|---|
| LoadingScreen / post-login splash | `profile,stats` | warm cache antes de UserHubScreen |
| UserHubScreen | (usa cache) | sin fetch nuevo si la query ya está warm |
| SecurityScreen | `security,sessions` | step-up modal si error; reintentar tras success |
| VehiclesScreen | `vehicles` | o usar cache previa si existe |
| PaymentMethodsScreen | `payment_methods` | |
| AddressesScreen | `addresses` | |
| FavoritesScreen | `favorites` | |
| NotificationsScreen | `notifications` | |
| PrivacyScreen | `preferences,notifications` | privacy ahora vive en preferences/notifications blocks o en sub-block aparte (decidir Fase 7) |
| ProviderHubScreen | `profile,provider,stats` | |

**Prefetch on intent**: cuando el user hace tap (o long-press) en un menu item, `queryClient.prefetchQuery(["users","me",sortedIncludesKey])` dispara el fetch durante la transición de navegación — la pantalla destino ve la data ya warm.

**Step-up flow**: cuando `useMe(["security","sessions"])` lanza `StepUpRequiredError` → modal global con biometría/passkey o password → `POST /auth/verify` (o `POST /auth/webauthn/authenticate/complete`) → al éxito, `queryClient.invalidateQueries(["users","me"])` → refetch automático con los includes pendientes.

**Optimistic updates**: preferences, privacy, favorites toggles, set-default vehicle/address/payment. NO para email/phone change ni para mutaciones del bloque `security`.

### 7.4 Patrones de UI (mobile)

- **Hero**: avatar + name + verification badges + RoleSwitcher.
- **Stats cards**: numbers prominentes (washes, vehicles, favorites).
- **Section navigation**: MenuOption (existente) con icon + badge inline (ej: "Security ⚠ 2FA").
- **Forms**: TextInput nativo + validación inline (patrón actual, sin react-hook-form aún).
- **Mutations destructivas**: confirm modal + haptic Heavy + undo toast 5s.
- **Loading**: skeletons sectional, NO spinner global.

### 7.5 Admin web (`web/`) — vista admin de usuarios

**Pages a crear (App Router)**:
- `web/app/dashboard/users/page.tsx` — lista paginada con filtros (role, status, verified)
- `web/app/dashboard/users/[id]/page.tsx` — detalle del usuario con tabs:
  - **Overview**: data básica del user (consume `GET /api/v1/admin/users/{id}` extendido para incluir aggregate)
  - **Security**: historial completo de seguridad (consume `GET /api/v1/admin/users/{id}/security/history`)
  - **Documents**: lista de docs KYC con preview + actions approve/reject (consume `GET /api/v1/admin/users/{id}/documents`)
  - **Sessions**: sesiones activas con opción de force-revoke
  - **Payment methods**: solo lectura (Stripe-only, link a Stripe Dashboard)
  - **Activity**: feed de cambios del usuario
- `web/app/dashboard/users/[id]/impersonate/page.tsx` — botón impersonation suave (genera read-only token para soporte)

**Endpoints admin necesarios (Fase 4-5)**:
- `GET /api/v1/admin/users/{id}` — proxy del aggregate con todos los `include`
- `GET /api/v1/admin/users/{id}/security/history`
- `GET /api/v1/admin/users/{id}/documents`
- `POST /api/v1/admin/users/{id}/documents/{doc_id}/approve|reject`
- `DELETE /api/v1/admin/users/{id}/sessions/{session_id}` (force revoke)
- `POST /api/v1/admin/users/{id}/impersonate` (genera token soporte read-only)

**Stack web**:
- SWR para data fetching
- shadcn/ui o Radix para componentes (no decidido aún — TODO)
- React Hook Form + Zod para validación
- Cliente HTTP compartido con mobile (mismo envelope, mismo refresh logic)

### 7.6 Marketing/Customer web (`marketing/`) — mirror cliente del flujo

**Decisión scope**: solo el flujo **cliente** (no proveedor). Detailers operan únicamente vía mobile por necesidad de location updates GPS, push notifications, y biometría. Web ofrece a clientes: registro, login, perfil, vehículos, direcciones, métodos de pago, reserva de cita, y ver historial.

**Pages bajo `marketing/app/[locale]/`**:
- `auth/login`, `auth/register`, `auth/forgot-password`
- `account/` — UserHubScreen equivalente
  - `account/edit`
  - `account/security`
  - `account/vehicles`
  - `account/payment-methods`
  - `account/addresses`
  - `account/favorites`
  - `account/notifications`
  - `account/privacy`
  - `account/history/appointments`
  - `account/history/payments`
  - `account/settings` (export, delete)
- `book/` — flujo de reserva (catálogo, schedule, summary, confirmación)
- `bookings/` — list + detail (history)

**Sin role-switcher**. Si el user es dual-role, se le muestra un banner "Para gestionar tu modo detailer, abre la app móvil" con link al App Store / Play Store.

**Stack**:
- i18n via `next-intl` (ya integrado)
- App Router con server components para SEO de páginas marketing
- Client components para flows interactivos (login, perfil)
- Cliente HTTP compartido
- Tailwind CSS

### 7.7 Sincronización entre tracks

| Fase | Mobile entrega | Admin web entrega | Marketing web entrega |
|---|---|---|---|
| 0 | API client envelope refactor | API client envelope refactor | API client envelope refactor |
| 1 | UserHubScreen | Lista users + detalle Overview | Account overview page |
| 2 | Avatar flow | Display avatar en detail | Avatar flow |
| 3 | Contact change + Security | Security tab en user detail | Contact change + Security page |
| 4 | Payment methods + Addresses + Vehicles | Read-only en user detail | Mismas pantallas |
| 5 | Provider hub | Documents/verification review tab | — (no proveedor) |
| 6 | RoleSwitcher | — | — (no aplica) |
| 7 | Notifications + Privacy | Read-only | Notifications + Privacy |
| 8 | GDPR + Historiales | Activity tab | GDPR + History pages |
| 9 | Polish + analytics | Admin analytics dashboards | Polish |

Cada PR `feat/profile-phaseX` incluye los 3 tracks juntos cuando aplica. El admin y marketing pueden tener lag de 1-2 sprints si el bottleneck es mobile.

---

## 8. UX (lineamientos clave)

### 8.1 Jerarquía visual del UserHubScreen

```
╔═══════════════════════════════════════╗
║  [RoleSwitcher: Cliente | Detailer]   ║
╠═══════════════════════════════════════╣
║      [Avatar]   Yampier Hernandez     ║
║                 ⭐ 4.9 · Member 2024  ║
║                                       ║
║  [✓ Email] [✓ Phone] [○ Identity]    ║
║                                       ║
║  ┌──14──┬───2───┬───3───┐             ║
║  │Washes│ Cars  │ Favs  │             ║
║  └──────┴───────┴───────┘             ║
║                                       ║
║  Personal                             ║
║  > Edit profile           →           ║
║  > Security              →   ⚠ 2FA   ║
║  > Notifications         →           ║
║  > Privacy               →           ║
║                                       ║
║  Cliente (si active_role=client)      ║
║  > Vehicles              →   2       ║
║  > Payment methods       →           ║
║  > Addresses             →   1       ║
║  > Favorites             →   3       ║
║                                       ║
║  Become a detailer                    ║
║  ┌─────────────────────────────────┐  ║
║  │ Earn money detailing cars   →   │  ║
║  └─────────────────────────────────┘  ║
║                                       ║
║  Activity & help                      ║
║  > Recent activity       →           ║
║  > Help & support        →           ║
║                                       ║
║  Account                              ║
║  > Sign out                           ║
║  > Delete account              (rojo) ║
║                                       ║
║  v1.4.2 · Terms · Privacy             ║
╚═══════════════════════════════════════╝
```

### 8.2 Errores comunes a EVITAR

| Error | Por qué malo | Solución aquí |
|---|---|---|
| Mezclar settings de cuenta con de app | Confusión | Profile vs Settings/App separados |
| Esconder delete account | GDPR + UX | Visible, rojo subtle, en AccountSettings |
| Avatar sin preview pre-upload | Sorpresas | ImagePicker con crop |
| Loading global blanco | Sensación broken | Skeletons sectional |
| Provider data en vista client | Cognitivo | RoleSwitcher dicta visibility |
| Edit como modal sin contexto | Lost user | Push con back nativo |
| Alert.alert() para confirmaciones | Aspecto 2000s | Toasts (Snackbar) excepto destructivos |
| Email change instantáneo | Takeover | Doble verificación |
| 2FA disable sin step-up | Bypass | step-up obligatorio |

---

## 9. Escalabilidad

- **Redis cache**: `users:me:{user_id}:{token_version}` TTL 5 min. Invalida en cada mutación (bumps token_version o explicit DEL).
- **Índices DB críticos**: ver detalle en cada fase. Resumen: partial unique en `(user_id) WHERE is_default=true` para payment_methods + addresses; `(user_id, type, status)` en documents; `(scheduled_for) WHERE finalized_at IS NULL` en account_deletion_requests.
- **Background workers** (Redis Queue / RQ): achievement_evaluator, account_deletion_finalizer, data_export_builder, document_expiry_checker, pending_contact_cleanup, notification_dispatcher.
- **S3 + CloudFront**: 2 buckets (public-assets, private-docs). Lifecycle: avatars cleanup 90d orphans; KYC retain 7 años → Glacier; exports delete 7d.
- **Multi-ciudad ready**: `UserAddress.city/state/country`, `User.preferred_currency` (USD only por ahora, schema-ready), `User.preferred_timezone`.
- **i18n**: `User.preferred_language` + frontend `react-i18next` (futuro).
- **Read replicas**: cuando `GET /users/me` > 5k/min. Router-level routing por endpoint (read-only → replica).

---

## 10. Plan de implementación por FASES

Cada fase es **deployable** independientemente y deja el sistema en estado coherente. Duración estimada: 1-2 sprints por fase.

---

### **Fase 0 — Fundaciones de API uniforme** (1 sprint)

**Goal**: establecer estándares de API antes de tocar funcionalidad nueva. Sin esto, fase 1+ acumula deuda.

**Entregables**:
- ✅ Middleware: RequestID, structured logging, rate limit headers.
- ✅ Pydantic generic `Envelope[T]` + `PaginatedEnvelope[T]` + `ErrorEnvelope` en `shared/schemas.py`. **Cada endpoint declara `response_model=Envelope[X]` explícito** (NO middleware de wrapping).
- ✅ **Enforcement del envelope**:
  - Custom `APIRouter` base (`EnvelopeRouter`) que valida en setup que cada route registrada tenga `response_model` que herede de `Envelope` o sea `None` (para 204) — fail-fast al startup.
  - Test integration `tests/api/test_envelope_compliance.py` que recorre `app.router.routes`, filtra los `/api/v1/*` protegidos, y asserta que el `response_model` derive de `Envelope`. CI red si falla.
- ✅ Exception handlers: mapear `ValidationError`, `HTTPException`, `BusinessError` → `ErrorEnvelope` con `code` estandarizado.
- ✅ Cursor pagination helper: `encode_cursor(item)`, `decode_cursor(s)`.
- ✅ Idempotency middleware: cachea response por `(user_id, key, method, path)` 24h en Redis.
- ✅ Step-up auth dependency: `require_step_up()` con Redis primario + DB fallback (`User.last_step_up_at`). Actualizada en login, password verify, OAuth verify, passkey verify.
- ✅ Extender `AuditAction` enum con todos los nuevos valores.
- ✅ **Extender `audit_log`**: añadir `old_value`, `new_value`, `ip_address`, `user_agent`, `request_id`. Rename `stripe_metadata → metadata_`.
- ✅ **Middleware `audit_context`** — extrae `ip`, `user_agent`, `request_id` y los attach a `request.state.audit_ctx`. `AuditLogger.log()` lee automáticamente.
- ✅ **Tabla `user_login_history`** + hook en `AuthService.authenticate_user` que la pobla en **cada intento** — tanto exitoso (con `auth_method`, `refresh_token_family_id`) como fallido (con `failure_reason` enum). El hook lee `request.state.audit_ctx` para `ip_address`, `user_agent`, `request_id` (gracias al middleware `audit_context` ya registrado antes en el orden). Esto cubre password, OAuth (google/apple), webauthn — todos pasan por `authenticate_user` o equivalente.
- ✅ Deprecation strategy: helper que añade `Deprecation: true` + `Sunset:` a endpoints marcados (vía dependency, no middleware global).
- ✅ OpenAPI tags + descriptions ordenados por dominio.
- ✅ Frontend: extender `apiClient` con interceptor que desempaca `data`, mapea errores a `ApiError`. Mantener compat con endpoints viejos durante transición.

**Migraciones Alembic**:
- `m_001_extend_audit_actions.py` — añade valores al enum `AuditAction`.
- `m_001b_add_last_step_up_at.py` — añade `users.last_step_up_at` (fallback de Redis).
- `m_001c_extend_audit_log.py` — añade `old_value`, `new_value`, `ip_address`, `user_agent`, `request_id` a `audit_log`; renombra `stripe_metadata` → `metadata_`.
- `m_001d_create_user_login_history.py` — tabla `user_login_history`.

**Archivos backend nuevos**:
- [backend/app/core/envelope.py](backend/app/core/envelope.py) — generics + helpers
- [backend/app/core/idempotency.py](backend/app/core/idempotency.py)
- [backend/app/core/step_up.py](backend/app/core/step_up.py)
- [backend/app/core/cursor.py](backend/app/core/cursor.py)
- [backend/app/core/deprecation.py](backend/app/core/deprecation.py)
- [backend/app/middleware/request_id.py](backend/app/middleware/request_id.py)
- [backend/app/middleware/structured_logging.py](backend/app/middleware/structured_logging.py)
- [backend/app/exception_handlers.py](backend/app/exception_handlers.py)

**Archivos backend a modificar**:
- [backend/main.py](backend/main.py:1) — registrar middlewares + handlers
- [backend/app/core/limiter.py](backend/app/core/limiter.py) — añadir headers `X-RateLimit-*`
- [backend/domains/audit/models.py](backend/domains/audit/models.py:1) — extender enum
- [backend/shared/schemas.py](backend/shared/schemas.py) — añadir `Envelope`, `ErrorEnvelope`

**Archivos frontend**:
- [frontend/src/services/api.ts](frontend/src/services/api.ts:1) — interceptors, `ApiError` class
- [frontend/src/lib/api-error.ts](frontend/src/lib/api-error.ts) — clase + utilities

**Acceptance criteria**:
- Todos los endpoints `/auth/*` y `/api/v1/*` existentes retornan envelope `{data}` o `{error}`.
- Endpoint deprecated (`GET /auth/me`) retorna 200 + `Deprecation: true` + redirige funcionalmente.
- Test: idempotency-key duplicada retorna response cacheada.
- Test: step-up requerido → 401 con `WWW-Authenticate: StepUp`.

---

### **Fase 1 — Recurso central `/api/v1/users/me`** (1 sprint)

**Goal**: **🆕 Profile Hub completo** — `GET /users/me` con shape de bloques (`user`, `profile`, `stats`, `security`, `sessions`, `provider`, `vehicles`, `addresses`, `payment_methods`, `favorites`, `preferences`, `notifications`) controlados por `?include=`. Esta es la pieza central del Profile system.

**Entregables**:
- ✅ `GET /api/v1/users/me?include=<tokens>` — Profile Hub con shape compuesto:
  - SIEMPRE presente: bloque `user` (UserCore: id, email, email_verified, phone, phone_verified, role, available_roles, created_at) + `verification_badges`.
  - Opt-in: 11 bloques via `?include=profile,vehicles,favorites,sessions,security,provider,addresses,payment_methods,preferences,notifications,stats`.
  - Response incluye `meta.includes: [...]` listando bloques efectivamente cargados.
- ✅ Parser `IncludeSpec` que valida tokens contra whitelist por rol (ej: `provider` solo para detailers, `vehicles/favorites/preferences` solo para clients) — tokens inválidos para el rol se omiten silenciosamente, no error.
- ✅ **Step-up enforcement** sobre includes sensibles (`security`, `sessions`): si pedidos sin re-auth reciente → 401 `step_up_required` con `meta.requires_step_up: [...]`. Soporta `?on_step_up=skip` para refresh background.
- ✅ `PATCH /api/v1/users/me` — actualiza campos del bloque `profile` (first_name, last_name, pronouns, language, timezone). NO actualiza `user.email`/`user.phone` (esos van por `/email/change-request` y `/phone/change-request`).
- ✅ Deprecación de `GET /auth/me` y `PUT /auth/update` con `Sunset: 2026-08-01`.
- ✅ `ProfileHubService` que orquesta sub-services (UserService, ProviderService, VehicleService, PaymentMethodService, AuthSecurityService, AuthSessionService, etc.) según los tokens del include. Cada sub-service expone método `to_hub_block(user) -> dict | None` reutilizable.
- ✅ Caching Redis por combinación: key `profile:hub:{user_id}:{token_version}:{sorted_includes_hash}`, TTL 5 min. Cache invalidation en cualquier mutación que toque la entidad subyacente.
- ✅ Frontend `UserHubScreen` (refactor de `ProfileScreen` + `DetailerProfileScreen` unificados). Estrategia lazy loading:
  - **Post-login splash**: `GET /users/me?include=profile,stats` (carga inicial rápida).
  - **UserHubScreen mount**: usa la data del splash (cache React Query).
  - **SecurityScreen entry**: `GET /users/me?include=security,sessions` (con step-up modal si no reciente).
  - **VehiclesScreen entry**: `GET /users/me?include=vehicles` (o navega con cache previa).
  - **ProviderHubScreen mount**: `GET /users/me?include=profile,provider,stats`.

**Migraciones Alembic**:
- m_002, m_003, m_004 (columnas User/ClientProfile/ProviderProfile como antes).
- `m_004b_add_total_spent_cents.py` — nueva columna `ClientProfile.total_spent_cents BIGINT NOT NULL DEFAULT 0` con trigger PostgreSQL desde `payment_ledger` (CAPTURE entries).
- `m_004c_split_full_name.py` (opcional, ver decisión abajo) — añade `User.first_name`, `User.last_name`. **Decisión**: mantener `User.full_name` como single field (concatenación), exponer `first_name`/`last_name` en el bloque `profile` derivado por split simple (primera palabra = first_name, resto = last_name). Esto evita migración riesgosa de datos PII existentes y deja la separación como detalle de presentación.

**Acceptance criteria**:
- `GET /users/me` sin include → solo `user` + `verification_badges` (≤ 50ms warm).
- `?include=profile,stats` warm < 100ms.
- `?include=profile,stats,security,sessions` con step-up reciente warm < 200ms.
- `?include=security,sessions` sin step-up → 401 `step_up_required` con `WWW-Authenticate: StepUp`.
- `?include=security,sessions&on_step_up=skip` → 200 con bloques omitidos + `meta.skipped_due_to_step_up`.
- `?include=provider` con user=client → `provider` omitido, `meta.includes` no lo lista (no error).
- Tokens desconocidos en include → 400 `bad_request` con lista de tokens válidos.
- Tests: 15+ casos (cada bloque, combinaciones, step-up, role mismatch, deleted user, edge cases).

**Migraciones Alembic**:
- `m_002_user_profile_columns.py` — `users`: avatar_s3_key, cover_s3_key, pronouns, preferred_language, last_active_at, deleted_at, active_role, last_step_up_at.
- `m_003_client_profile_defaults.py` — `client_profiles`: default_vehicle_id, default_address_id, total_appointments_count, marketing_email_opt_in, frequency_preference.
- `m_004_provider_profile_public_fields.py` — `provider_profiles`: display_name, business_name, tagline, social_links, insurance_policy_number_encrypted, tax_id_encrypted, payout_method_id, cover_photo_s3_key.

**Archivos backend nuevos**:
- [backend/domains/users/services/profile_hub_service.py](backend/domains/users/services/profile_hub_service.py) — orquesta sub-services según `IncludeSpec`
- [backend/domains/users/services/include_spec.py](backend/domains/users/services/include_spec.py) — parser + whitelist + role check
- [backend/domains/users/schemas/hub.py](backend/domains/users/schemas/hub.py) — `UserCore`, `ProfileBlock`, `StatsBlock`, `SecurityBlock`, `SessionsBlock` (list[Session]), `ProviderBlock`, `VehiclesBlock`, `AddressesBlock`, `PaymentMethodsBlock`, `FavoritesBlock`, `PreferencesBlock`, `NotificationsBlock`, `VerificationBadges`, `HubResponse`
- [backend/domains/users/routers/me.py](backend/domains/users/routers/me.py)
- [backend/domains/users/routers/__init__.py](backend/domains/users/routers/__init__.py) — ensamble users_router
- [backend/domains/auth/services/auth_block_provider.py](backend/domains/auth/services/auth_block_provider.py) — expone `to_security_block(user)` y `to_sessions_block(user)` para que el Hub los consuma sin acoplarse a los modelos auth

**Archivos backend a modificar**:
- [backend/domains/users/models.py](backend/domains/users/models.py:1) — split en `models/` package, añadir columnas
- [backend/domains/providers/models.py](backend/domains/providers/models.py:1) — añadir public fields
- [backend/api/router.py](backend/api/router.py:1) — incluir `users_router`
- [backend/domains/auth/routers/core.py](backend/domains/auth/routers/core.py) — marcar `/auth/me`, `/auth/update` deprecated

**Frontend**:
- [frontend/src/screens/UserHubScreen.tsx](frontend/src/screens/UserHubScreen.tsx) — unifica ProfileScreen + DetailerProfileScreen
- [frontend/src/services/users.service.ts](frontend/src/services/users.service.ts) — `getMe()`, `updateMe()`
- [frontend/src/hooks/useMe.ts](frontend/src/hooks/useMe.ts) — React Query wrapper
- Añadir `@tanstack/react-query` a package.json

**Acceptance criteria**:
- `GET /api/v1/users/me` retorna aggregate completo en 1 query optimizada (selectin de relaciones).
- Cache hit warm (<5ms response).
- Frontend hub muestra ambos roles correctamente con stats reales.
- Tests: 8+ casos (client, detailer, dual-role, deleted, unverified).

---

### **Fase 2 — Avatar + Cover + S3 setup** (1 sprint)

**Goal**: storage funcional + flujo de avatar end-to-end.

**Entregables**:
- ✅ AWS S3 buckets aprovisionados: `raycarwash-public-assets`, `raycarwash-private-docs`.
- ✅ CloudFront distribution con signed URLs.
- ✅ IAM role + secret rotation strategy.
- ✅ Adapter `S3StorageAdapter` con métodos: `generate_upload_url`, `head_object`, `generate_download_url`, `delete_object`.
- ✅ Endpoints avatar/cover upload-url + confirm + delete.
- ✅ Frontend AvatarPicker component (Expo ImagePicker + crop + upload).
- ✅ Lambda image processing (resize variants s/m/l + WebP) — opcional Fase 2.5 si scope grande.

**Migraciones**: ninguna (columnas ya en Fase 1).

**Archivos backend nuevos**:
- [backend/domains/users/adapters/s3_adapter.py](backend/domains/users/adapters/s3_adapter.py)
- [backend/domains/users/services/avatar_service.py](backend/domains/users/services/avatar_service.py)
- [backend/domains/users/routers/avatar.py](backend/domains/users/routers/avatar.py)
- [backend/app/core/config.py](backend/app/core/config.py) — AWS_S3_BUCKET_PUBLIC, AWS_S3_BUCKET_PRIVATE, AWS_REGION, CLOUDFRONT_DOMAIN, AWS_KMS_KEY_ID

**Frontend**:
- [frontend/src/components/AvatarPicker.tsx](frontend/src/components/AvatarPicker.tsx)
- [frontend/src/services/s3-uploader.ts](frontend/src/services/s3-uploader.ts)
- Añadir `expo-image-picker`, `expo-image-manipulator` a package.json

**Acceptance criteria**:
- Avatar visible tras upload sin refresh manual (React Query invalidation).
- Backend HEAD valida mime real → rechaza si cliente mintió.
- Avatar URL firmada accesible sin token (CloudFront signed cookie / URL).
- Test: upload-url con mime no permitido → 422.

---

### **Fase 3 — Contact changes (users) + Centro de seguridad + History (auth)** (1-2 sprints)

**Goal**: cambio de email/teléfono con verificación (bajo `/users/me`) + centro de seguridad completo (bajo `/auth/*`, separación estricta) + endpoint de historial de seguridad.

**Entregables**:
- ✅ Modelo `PendingContactChange` (en `domains/users/`).
- ✅ Endpoints `/api/v1/users/me/email/*` y `/phone/*` con flujo verificación.
- ✅ Adapter Twilio para OTP SMS.
- ✅ Templates email transaccional: change-confirm (al nuevo), anti-takeover notification (al viejo), OTP fallback.
- ✅ Modelo `TotpCredential` en `domains/auth/` (secret_encrypted, backup_codes_hashes, enabled, last_used_at).
- ✅ Endpoints **bajo `/api/v1/auth/*`** (no users):
  - `GET /api/v1/auth/security` — summary consolidado.
  - `GET /api/v1/auth/history` — historial security mezcla `UserLoginHistory` + `AuditLog` filtrado a security actions (login, password_change, email_change, phone_change, two_fa_*, passkey_*, session_revoked). Cursor-paginated, filtros `type`/`from`/`to`.
  - `GET/DELETE /api/v1/auth/sessions[/:id]` — gestión de sessions (extender lo existente).
  - `GET/PATCH/DELETE /api/v1/auth/passkeys[/:id]` — gestión de WebAuthn credentials (nuevo router admin, los handshakes en `/webauthn/*` se mantienen).
  - `POST /api/v1/auth/two-fa/enroll|verify`, `DELETE /two-fa`, `POST /two-fa/backup-codes/regenerate`.
- ✅ Adapter opcional para `ip_location` lookup (MaxMind GeoLite o ipapi gratuito) — denormaliza al insert.
- ✅ Worker `workers/pending_contact_cleanup.py` cron horario.
- ✅ Worker `workers/login_history_purger.py` cron mensual (retención 12mo success / 90d failed).
- ✅ Frontend: ContactChangeFlow stack (bajo Profile) + SecurityScreen con tabs **"General"** (2FA, passkeys, password, sessions) y **"Activity"** (consume `/auth/history` con render por tipo).

**Migraciones Alembic**:
- `m_005_create_pending_contact_changes.py`.
- `m_005b_create_totp_credentials.py` — tabla en `domains/auth/`.

**Archivos backend nuevos**:
- [backend/domains/users/models/pending_contact_change.py](backend/domains/users/models/pending_contact_change.py)
- [backend/domains/users/services/contact_change_service.py](backend/domains/users/services/contact_change_service.py)
- [backend/domains/users/routers/contact.py](backend/domains/users/routers/contact.py)
- [backend/domains/auth/models/totp_credential.py](backend/domains/auth/models/totp_credential.py)
- [backend/domains/auth/services/totp_service.py](backend/domains/auth/services/totp_service.py)
- [backend/domains/auth/services/security_summary_service.py](backend/domains/auth/services/security_summary_service.py)
- [backend/domains/auth/routers/security.py](backend/domains/auth/routers/security.py) — summary
- [backend/domains/auth/routers/two_fa.py](backend/domains/auth/routers/two_fa.py)
- [backend/domains/auth/routers/passkeys_admin.py](backend/domains/auth/routers/passkeys_admin.py) — list/rename/revoke (handshake sigue en webauthn.py)
- [backend/infrastructure/twilio/](backend/infrastructure/twilio/) — adapter
- [backend/workers/pending_contact_cleanup.py](backend/workers/pending_contact_cleanup.py)

**Frontend**:
- [frontend/src/screens/SecurityScreen.tsx](frontend/src/screens/SecurityScreen.tsx)
- [frontend/src/screens/ContactChange/ChangeEmailScreen.tsx](frontend/src/screens/ContactChange/ChangeEmailScreen.tsx)
- [frontend/src/screens/ContactChange/ChangePhoneScreen.tsx](frontend/src/screens/ContactChange/ChangePhoneScreen.tsx)
- [frontend/src/screens/ContactChange/ConfirmOTPScreen.tsx](frontend/src/screens/ContactChange/ConfirmOTPScreen.tsx)
- [frontend/src/screens/SessionsScreen.tsx](frontend/src/screens/SessionsScreen.tsx)
- [frontend/src/screens/PasskeysScreen.tsx](frontend/src/screens/PasskeysScreen.tsx)
- [frontend/src/screens/TwoFactorSetupScreen.tsx](frontend/src/screens/TwoFactorSetupScreen.tsx)

**Acceptance criteria**:
- Email change requiere link de confirmación; usar email viejo aún funciona hasta confirm.
- Confirm de email bumps token_version (sessions invalidadas).
- Email anti-takeover llega al viejo email.
- OTP SMS max 5 intentos, locked 15 min al 6to.
- 2FA disable requiere step-up.

---

### **Fase 4 — Recursos del cliente** (1-2 sprints)

**Goal**: vehicles (con photos), payment-methods (Stripe sync), addresses, favorites, client-preferences.

**Entregables**:
- ✅ Modelos: `UserAddress`, `PaymentMethod`, `ClientFavorite`, `VehiclePhoto`.
- ✅ Endpoints `/users/me/vehicles/*` (migrar lógica desde `/api/v1/vehicles`), `/payment-methods/*`, `/addresses/*`, `/favorites/*`, `/client-preferences`.
- ✅ Webhooks Stripe: `payment_method.attached`, `payment_method.detached`, `payment_method.updated`, `setup_intent.succeeded` → sync local.
- ✅ Geocoding adapter (Google Maps Geocoding API o similar) para addresses → lat/lng + h3.
- ✅ Frontend: VehiclesScreen refactor + photos, PaymentMethodsScreen (Stripe CardField), AddressesScreen, FavoritesScreen, ClientPreferencesScreen.

**Migraciones Alembic**:
- `m_006_create_user_addresses.py`
- `m_007_create_payment_methods.py`
- `m_008_create_client_favorites.py`
- `m_009_create_vehicle_photos.py`
- `m_010_link_client_profile_defaults.py` — FK constraints sobre default_vehicle_id, default_address_id.

**Archivos backend nuevos**:
- Modelos + repos + services + routers para cada sub-recurso (8+ archivos).
- [backend/domains/users/adapters/stripe_payment_adapter.py](backend/domains/users/adapters/stripe_payment_adapter.py)
- [backend/infrastructure/geocoding/](backend/infrastructure/geocoding/) — adapter Google Maps
- [backend/domains/payments/webhook_router.py](backend/domains/payments/webhook_router.py:1) — handlers payment_method.*

**Frontend**:
- 5+ screens nuevas/refactor.
- [frontend/src/services/payment-methods.service.ts](frontend/src/services/payment-methods.service.ts)
- [frontend/src/services/addresses.service.ts](frontend/src/services/addresses.service.ts)
- [frontend/src/services/favorites.service.ts](frontend/src/services/favorites.service.ts)

**Acceptance criteria**:
- Add payment method via Stripe SetupIntent en frontend; webhook crea row local; aparece en lista sin refresh manual.
- Default unique constraints respetadas (sólo 1 default vehicle, 1 default address, 1 default payment method por user).
- Delete address default mientras hay appointments futuros → 409.
- Tests: 25+ cubriendo edge cases.

---

### **Fase 5 — Recursos del proveedor** (1-2 sprints)

**Goal**: provider-profile completo + services + portfolio + documents + verification + achievements + location.

**Entregables**:
- ✅ Modelos: `ProviderPortfolioPhoto`, `ProviderAchievement`, `Document`.
- ✅ Endpoints `/users/me/provider-*` (migrar lógica desde `/api/v1/detailers/me`).
- ✅ Deprecación de `/api/v1/detailers/me*` (siguen funcionando con `Sunset:`).
- ✅ Document storage: bucket privado + SSE-KMS + presigned con TTL 1h.
- ✅ Worker `workers/achievement_evaluator.py` cron diario.
- ✅ Worker `workers/document_expiry_checker.py` cron diario → notif "Your insurance expires in 30d".
- ✅ Stripe Identity webhook → `provider_verification` updates + auto-grant `verified` badge.
- ✅ Frontend: ProviderHubScreen + 6+ sub-screens.

**Migraciones Alembic**:
- `m_011_create_documents.py`
- `m_012_create_provider_portfolio_photos.py`
- `m_013_create_provider_achievements.py`

**Archivos backend nuevos**:
- Modelos + repos + services + routers para provider-* (10+ archivos).
- [backend/workers/achievement_evaluator.py](backend/workers/achievement_evaluator.py)
- [backend/workers/document_expiry_checker.py](backend/workers/document_expiry_checker.py)

**Frontend**:
- [frontend/src/screens/ProviderHubScreen.tsx](frontend/src/screens/ProviderHubScreen.tsx)
- [frontend/src/screens/ProviderProfileEditScreen.tsx](frontend/src/screens/ProviderProfileEditScreen.tsx)
- [frontend/src/screens/ProviderPortfolioScreen.tsx](frontend/src/screens/ProviderPortfolioScreen.tsx)
- [frontend/src/screens/ProviderDocumentsScreen.tsx](frontend/src/screens/ProviderDocumentsScreen.tsx)
- [frontend/src/screens/ProviderAchievementsScreen.tsx](frontend/src/screens/ProviderAchievementsScreen.tsx)
- [frontend/src/screens/ProviderVerificationScreen.tsx](frontend/src/screens/ProviderVerificationScreen.tsx)

**Acceptance criteria**:
- `POST /users/me/provider-profile` con role client crea ProviderProfile, asigna role detailer, NO setea is_accepting hasta KYC.
- `PATCH /users/me/provider-status {is_accepting: true}` con verification_status≠approved → 403 `kyc_required`.
- Achievement `verified` awarded en webhook Stripe Identity verified.
- Document expiry notif funciona (con cuenta test próxima a expirar).
- Frontend: ProviderHub muestra progress bar de KYC steps.

---

### **Fase 6 — Active role switcher con rotación de refresh** (1 sprint)

**Goal**: alternar rol activo en runtime con re-emisión de access **y rotación de refresh**.

**Entregables**:
- ✅ Endpoint `PATCH /api/v1/users/me/active-role` (rename de `/role`).
- ✅ Body: `{role: "client" | "detailer"}`. Validaciones:
  - Usuario tiene ese role asignado (sino 403 `permission_denied`).
  - Si target=detailer y `verification_status≠approved` → 403 `kyc_required`.
- ✅ **Rotación de refresh token** (igual que cambio de password): revocar refresh actual + emitir nuevo. Esto cierra la ventana en que un refresh robado pueda emitir access tokens con rol viejo.
- ✅ Modificación de `AuthService._build_token`: usa `User.active_role` (no first assigned role).
- ✅ Audit log: `ROLE_SWITCHED` con metadata `{from, to}`.
- ✅ Frontend `RoleSwitcher` component visible en UserHubScreen.
- ✅ `auth-controller.ts`: tras switch, guarda **ambos** tokens nuevos (access + refresh), invalida queries de React Query, `navigation.reset({name: target_stack})`.

**Migraciones**: ninguna (active_role ya en Fase 1).

**Archivos backend nuevos**:
- [backend/domains/users/routers/active_role.py](backend/domains/users/routers/active_role.py)
- [backend/domains/users/services/role_switch_service.py](backend/domains/users/services/role_switch_service.py) — orquesta validation + AuthService.rotate_refresh + emit access

**Archivos backend a modificar**:
- [backend/domains/auth/service.py](backend/domains/auth/service.py:1) — `_build_token` lee `active_role`; expone `rotate_refresh_token_family(user, current_refresh)` reutilizable
- [backend/api/router.py](backend/api/router.py) — incluir active_role router

**Frontend**:
- [frontend/src/components/RoleSwitcher.tsx](frontend/src/components/RoleSwitcher.tsx)
- [frontend/src/store/authStore.ts](frontend/src/store/authStore.ts:1) — `setTokens({access, refresh})`, `setActiveRole`, sync con SecureStore
- [frontend/src/utils/auth-controller.ts](frontend/src/utils/auth-controller.ts:1) — handler post-switch (queryClient.invalidateQueries(["users","me"]))

**Acceptance criteria**:
- Dual-role user puede alternar; access + refresh nuevos retornados.
- **Refresh viejo revocado**: si se intenta usar después del switch → 401 con `code: gone`.
- Single-role user: `PATCH /active-role` con target distinto → 403.
- KYC pendiente intentando switch a detailer → 403 `kyc_required`.
- Test: switch → next request `/users/me` retorna `provider_profile` no `client_profile`.
- Test: capturar refresh antes del switch, intentar usarlo después → falla (rotación correcta).

---

### **Fase 7 — Notifications + Privacy + Public view** (1 sprint)

**Goal**: preferencias granulares + privacy + vista pública con respeto de visibility.

**Entregables**:
- ✅ Modelos: `NotificationPreference`, `PrivacySetting`.
- ✅ Endpoints `/users/me/notifications/*`, `/devices/*`, `/privacy/*`.
- ✅ Deprecación `POST /api/v1/notifications/device-token`.
- ✅ Endpoint `GET /api/v1/users/{user_id}/public` con visibility checks.
- ✅ Integración con `notification_dispatcher` worker: respeta preferences + quiet_hours antes de enviar.
- ✅ Frontend: NotificationsScreen (matrix toggles), PrivacyScreen, PublicProfileScreen.

**Migraciones Alembic**:
- `m_014_create_notification_preferences.py`
- `m_015_create_privacy_settings.py`

**Archivos backend nuevos**:
- 4 modelos/repos/services/routers + extension del dispatcher.
- [backend/domains/users/routers/public.py](backend/domains/users/routers/public.py)

**Frontend**:
- [frontend/src/screens/NotificationsScreen.tsx](frontend/src/screens/NotificationsScreen.tsx)
- [frontend/src/screens/DevicesScreen.tsx](frontend/src/screens/DevicesScreen.tsx)
- [frontend/src/screens/PrivacyScreen.tsx](frontend/src/screens/PrivacyScreen.tsx)
- [frontend/src/screens/PublicProfileScreen.tsx](frontend/src/screens/PublicProfileScreen.tsx)

**Acceptance criteria**:
- Toggle `appointment_lifecycle.push=false` → dispatcher omite envío.
- Topic `security` ignora preferences (siempre se envía).
- Quiet hours respetados en push (no en SMS/email crítico).
- `GET /users/{id}/public` con target.privacy=PRIVATE → 404.
- Vista pública oculta last_active si `show_last_active=false`.

---

### **Fase 8 — GDPR (export + deletion) + Historiales especializados** (1-2 sprints)

**Goal**: compliance GDPR + suite de historiales (appointments, payments, vehicles, profile-changes, reviews) + activity feed unificado como resumen opcional.

**Entregables**:
- ✅ Modelos: `DataExportRequest`, `AccountDeletionRequest`.
- ✅ Endpoints `/users/me/account/exports/*`, `/account/deletion-request/*`.
- ✅ Worker `workers/data_export_builder.py` — agrega user + appointments + payments + reviews + vehicles + audit + login_history → JSON + PDFs → zip → S3 → email.
- ✅ Worker `workers/account_deletion_finalizer.py` cron diario.
- ✅ **Historiales especializados**:
  - `GET /users/me/appointments/history?status=&from=&to=&vehicle_id=` cursor-paginated, devuelve cada cita con service + vehicle + provider + payment + review embebidos.
  - `GET /users/me/payments/history?status=&from=&to=` con receipt URLs (Stripe `receipt_url` o generación PDF propia).
  - `GET /users/me/vehicles/history?include_deleted=true` con timeline por vehicle (mezcla de `appointments` + `vehicle_photos` + `audit_log`).
  - `GET /users/me/profile-changes?action=&from=&to=` lee `audit_log` filtrado a actions de perfil (PROFILE_UPDATED, AVATAR_CHANGED, ADDRESS_*, PAYMENT_METHOD_*, NOTIFICATION_PREFS_UPDATED, PRIVACY_SETTINGS_UPDATED).
  - `GET /users/me/reviews?role=given|received` cursor-paginated.
- ✅ Endpoint `GET /users/me/activity` (feed unificado): agrega los 5 anteriores con limit cap 20 — es resumen, no fuente de paginación profunda.
- ✅ Servicios backend con queries optimizadas (selectin + índices ya en place).
- ✅ Frontend: AccountSettingsScreen + AppointmentsHistoryScreen + PaymentHistoryScreen + ProfileChangeLogScreen + ActivityFeedScreen (resumen).

**Migraciones Alembic**:
- `m_016_create_account_deletion_requests.py`
- `m_017_create_data_export_requests.py`

**Archivos backend nuevos**:
- 2 modelos GDPR + repos + services + routers.
- [backend/workers/data_export_builder.py](backend/workers/data_export_builder.py)
- [backend/workers/account_deletion_finalizer.py](backend/workers/account_deletion_finalizer.py)
- [backend/domains/users/services/history_service.py](backend/domains/users/services/history_service.py) — appointments, payments, vehicles, profile-changes
- [backend/domains/users/services/activity_service.py](backend/domains/users/services/activity_service.py) — feed unificado
- [backend/domains/users/routers/history.py](backend/domains/users/routers/history.py) — registra `/appointments/history`, `/payments/history`, `/vehicles/history`, `/profile-changes`, `/reviews`, `/activity`

**Frontend**:
- [frontend/src/screens/AccountSettingsScreen.tsx](frontend/src/screens/AccountSettingsScreen.tsx)
- [frontend/src/screens/AppointmentsHistoryScreen.tsx](frontend/src/screens/AppointmentsHistoryScreen.tsx) — filtros + cada item expansible
- [frontend/src/screens/PaymentHistoryScreen.tsx](frontend/src/screens/PaymentHistoryScreen.tsx) — receipts + refunds
- [frontend/src/screens/ProfileChangeLogScreen.tsx](frontend/src/screens/ProfileChangeLogScreen.tsx) — desde PrivacyScreen
- [frontend/src/screens/ActivityFeedScreen.tsx](frontend/src/screens/ActivityFeedScreen.tsx) — feed resumen unificado
- [frontend/src/screens/ExportStatusScreen.tsx](frontend/src/screens/ExportStatusScreen.tsx)
- [frontend/src/screens/SecurityHistoryScreen.tsx](frontend/src/screens/SecurityHistoryScreen.tsx) — entregado en Fase 3 con `/auth/history`, pero referenciado aquí para completar la suite UI

**Acceptance criteria**:
- Request export → worker → zip generado → presigned download URL en respuesta del GET status.
- Delete request con appointments activos → 409.
- Cancelación de delete dentro de grace period → cuenta reactivada (`is_active=true`).
- Worker finalizer anonimiza correctamente: email reemplazado, FK intactas, audit log entry.
- Activity feed cursor-paginated funciona con datos mixtos.

---

### **Fase 9 — Polish, Analytics, performance y testing E2E** (1-2 sprints)

**Goal**: optimización + endpoints analíticos + recordatorios + calidad para escalar.

**Entregables**:
- ✅ **Analytics endpoints** `/users/me/analytics/*`:
  - `service-frequency?vehicle_id=` — avg_days_between_washes, count_per_month últimos 12mo, most_common_service.
  - `upcoming-reminders` — derivado: vehículos con `now - last_completed_at > avg * 1.2`. CTA "¿Listo para otro lavado?".
  - `monthly-spending?year=` — total/mes + breakdown por servicio.
  - `earnings?from=&to=` (detailer) + `rating-trend` (detailer).
- ✅ Worker `workers/service_reminder_dispatcher.py` cron diario — analiza últimas citas + frecuencia típica → push notification "Vehículo X no ha sido lavado en 45 días".
  - **Idempotency con tabla `reminder_sent`**: `(user_id, vehicle_id, reminder_type, scheduled_date)` con UNIQUE constraint. El worker INSERTs primero; si conflict → skip. Garantiza nunca duplicar el mismo recordatorio.
  - **Cálculo de "frecuencia típica"**: mediana de días entre citas completadas para `(user_id, vehicle_id, service_category)`. Para usuarios sin historial suficiente (<3 citas), usar defaults: `basic_wash=30d`, `interior_detail=60d`, `full_detail=90d`, `ceramic_coating=180d`, `paint_correction=180d`. Documentado en el código y en `docs/decisions.md`.
  - Disparo: `now - last_completed_at > median * 1.2` (20% de margen — no quiero spam si el usuario llegó 1 día tarde).
- ✅ Redis caching aggregate `/users/me` (TTL 5min, invalidation hooks en todas las mutaciones). Cache key incluye `include` set.
- ✅ DB indices nuevos: partial unique en defaults, composite en payment_methods, account_deletion_requests scheduled_for, login_history success/failed compounds.
- ✅ Frontend: skeleton loaders sectional en todas las screens nuevas.
- ✅ Optimistic updates en preferences, privacy, favorites toggles.
- ✅ Haptics en acciones destructivas y role-switch.
- ✅ E2E tests críticos (Detox o Maestro): register → onboarding → edit profile → role switch → KYC → become provider → accept booking → review → check history.
- ✅ Performance:
  - `GET /users/me` (default, sin `include`) p95 < 100ms warm, < 300ms cold.
  - Cada history endpoint p95 < 200ms con cursor.
  - **Load test (criterio explícito)**: `GET /users/me` default soporta **500 req/s con p95 < 200ms** sostenido por 5 min (k6 o Locust). Si no se cumple → revisar índices y caching antes de release.
- ✅ Documentación final: OpenAPI exportada, README de Profile, guía para nuevos endpoints (cómo añadir un sub-recurso).

**Migraciones Alembic**:
- `m_018_indexes_performance.py` — incluye:
  - `idx_appointments_user_status_scheduled` ON `appointments(user_id, status, scheduled_at DESC)` — para `/appointments/history`.
  - `idx_appointments_vehicle_scheduled` ON `appointments(vehicle_id, scheduled_at DESC)` — para filtro `?vehicle_id=`.
  - `idx_payments_user_created` ON `payment_ledger(user_id, created_at DESC)` — para `/payments/history`.
  - `idx_audit_log_user_action_time` ON `audit_log(actor_id, action, created_at DESC)` — para `/profile-changes`.
  - Partial unique en defaults (`payment_methods`, `user_addresses`, `vehicles` por user).
  - Login history compounds (success/failed + time).
- `m_019_create_reminder_sent.py` — tabla idempotency del reminder worker.
- `m_020_appointment_count_triggers.py` — triggers PostgreSQL que actualizan `ClientProfile.total_appointments_count` y `ProviderProfile.total_services_completed` + `earnings_lifetime_cents` en cambio de status a `completed`.

**Archivos**:
- [backend/domains/users/services/analytics_service.py](backend/domains/users/services/analytics_service.py) — queries agregadas
- [backend/domains/users/routers/analytics.py](backend/domains/users/routers/analytics.py)
- [backend/workers/service_reminder_dispatcher.py](backend/workers/service_reminder_dispatcher.py)
- Refactor sectional de UI.
- Cache decorators en aggregate service.
- Tests E2E setup.

**Acceptance criteria**:
- Cache warm: response 200 desde Redis en <5ms.
- Mutación `PATCH /users/me` invalida cache automáticamente.
- 90%+ cobertura en `domains/users/services/`.
- E2E test completo pasa en CI.
- Reminder worker dispara push para cuenta de test con last_completed_at > 30d sin causar duplicados (idempotency por `(user_id, vehicle_id, date_key)`).

---

## 11. Verificación end-to-end

### Tests por fase
Cada fase tiene tests dedicados:
- **Unit (pytest)**: services con repos mockeados.
- **Integration (TestClient + DB real)**: routers + middleware completo.
- **E2E (manual + Detox/Maestro en Fase 9)**: flujos cliente reales.

### Smoke tests obligatorios pre-deploy de cada fase
```powershell
cd backend
pytest tests/users/ -v --cov=domains/users
pytest tests/integration/ -v
alembic upgrade head ; alembic downgrade -1 ; alembic upgrade head  # round-trip

cd ../frontend
npm test
npx tsc --noEmit  # type check
```

### Security tests (cada fase relevante)
- Rate limit triggers (intentar 6 email-change-request/hora → 429).
- Step-up rechazado tras 5+ min sin re-auth.
- Token replay tras password change → 401.
- Account enumeration: `/email/change-request` con email ajeno → 202 (no leak).
- HEAD bypass: confirm avatar sin haber subido → 422.
- Cross-user access: `GET /users/{otro_user_id}/public` con target.privacy=PRIVATE → 404.

### Manual smoke (cada fase frontend)
- iOS Simulator + Android Emulator: navegar todas las screens nuevas, validar haptics, skeletons, role switcher.
- Tester real (no developer) hace flujo end-to-end y reporta UX issues.

---

## 12. Errores comunes a evitar (resumen crítico)

1. Cambio de email sin notificar al viejo + sin verificar el nuevo → account takeover.
2. No bump `token_version` en cambio password/email → atacante mantiene sesión.
3. Guardar PII de tarjetas en backend → PCI nightmare.
4. Hard-delete users con appointments/reviews → rompe FK. Usar anonimización.
5. `/users/me` sin rate limit → enumeration.
6. Cambio de role sin re-emitir token **y sin rotar refresh** → endpoints `require_role` fallan **y** atacante con refresh robado sigue obteniendo access tokens con rol viejo.
7. Avatar confirm sin HEAD S3 → cliente puede mentir sobre upload.
8. No incluir `token_version` en JWT verify → tokens no invalidables.
9. Confundir `legal_full_name` con `display_name` en provider → KYC mismatch.
10. `is_accepting_bookings=true` sin `verification_status=approved` → KYC bypass.
11. Olvidar `phone_hash` HMAC al cambiar phone → lookups rompen.
12. Routers con queries directas a DB → rompe layering, deuda futura.
13. Exponer `stripe_verification_session_id` en responses → token sensible filtrado.
14. No respetar `PrivacySetting` en endpoint público → leak GDPR.
15. Olvidar wrap de response en `{data: ...}` → frontend interceptor rompe.
16. Reusar `Idempotency-Key` en operaciones distintas → cache hit erróneo.
17. Cursor pagination con `ORDER BY` sobre campo no único → skip de items.
18. Mezclar `apiClient` y `authClient` en frontend tras unificación → llamadas a paths inválidos.
19. Implementar step-up solo con Redis (sin fallback DB) → outage de Redis bloquea operaciones sensibles aunque el usuario se autenticó hace segundos.
20. Confundir handshake criptográfico (`/auth/webauthn/register/begin|complete`) con gestión administrativa (`/auth/passkeys`). El primero NO puede vivir bajo `/users` porque opera con tokens de challenge específicos, no JWTs estándar.
21. `GET /users/me` devolviendo TODO siempre → query pesado con COUNTs innecesarios para vistas que no los usan. Usar `?include=` opt-in.

---

## 13. Archivos críticos (resumen final)

### Backend — nuevos
- `backend/app/core/{idempotency,step_up,cursor,deprecation}.py`
- `backend/app/middleware/{request_id,structured_logging}.py`
- `backend/app/exception_handlers.py`
- `backend/domains/users/models/` (10+ archivos)
- `backend/domains/users/services/` (12+ archivos: aggregate, contact_change, role_switch, payment_methods, addresses, documents, etc.)
- `backend/domains/users/routers/` (17+ archivos — sin security/passkeys/sessions/2fa, esos van bajo auth)
- `backend/domains/users/adapters/{s3_adapter,stripe_payment_adapter}.py`
- `backend/domains/auth/models/totp_credential.py`
- `backend/domains/auth/services/{totp_service,security_summary_service}.py`
- `backend/domains/auth/routers/{security,two_fa,passkeys_admin}.py` (sessions ya existe; extender)
- `backend/infrastructure/twilio/`, `backend/infrastructure/geocoding/`
- `backend/workers/{achievement_evaluator,account_deletion_finalizer,data_export_builder,document_expiry_checker,pending_contact_cleanup}.py`
- `backend/shared/schemas.py` extension: `Envelope[T]`, `PaginatedEnvelope[T]`, `ErrorEnvelope`, `Meta`
- `backend/alembic/versions/m_001..m_018_*.py` (18+ migraciones, incluyendo `last_step_up_at` y `totp_credentials`)

### Backend — modificar
- [backend/main.py](backend/main.py:1)
- [backend/api/router.py](backend/api/router.py:1)
- [backend/app/core/config.py](backend/app/core/config.py)
- [backend/app/core/limiter.py](backend/app/core/limiter.py)
- [backend/domains/audit/models.py](backend/domains/audit/models.py:1) (extender con old_value/new_value/ip/UA/request_id; rename `stripe_metadata`)
- [backend/domains/audit/repository.py](backend/domains/audit/repository.py) (lee `request.state.audit_ctx` automáticamente)
- [backend/domains/auth/service.py](backend/domains/auth/service.py:1) (active_role en token, rotación de refresh reutilizable, hook a UserLoginHistory en authenticate_user)
- [backend/domains/auth/routers/core.py](backend/domains/auth/routers/core.py) (deprecation headers)
- [backend/domains/providers/router.py](backend/domains/providers/router.py:1) (deprecation `/detailers/me`)
- [backend/domains/payments/webhook_router.py](backend/domains/payments/webhook_router.py) (payment_method.*)
- [backend/shared/schemas.py](backend/shared/schemas.py)

### Frontend — nuevos
- `frontend/src/screens/UserHubScreen.tsx`
- `frontend/src/screens/SecurityScreen.tsx`
- `frontend/src/screens/PaymentMethodsScreen.tsx`
- `frontend/src/screens/AddressesScreen.tsx`
- `frontend/src/screens/FavoritesScreen.tsx`
- `frontend/src/screens/ClientPreferencesScreen.tsx`
- `frontend/src/screens/ProviderHubScreen.tsx` + 5 sub-screens
- `frontend/src/screens/NotificationsScreen.tsx`, `DevicesScreen.tsx`, `PrivacyScreen.tsx`
- `frontend/src/screens/PublicProfileScreen.tsx`
- `frontend/src/screens/AccountSettingsScreen.tsx`, `ActivityFeedScreen.tsx`, `ExportStatusScreen.tsx`
- `frontend/src/screens/ContactChange/` (3 screens)
- `frontend/src/screens/SessionsScreen.tsx`, `PasskeysScreen.tsx`, `TwoFactorSetupScreen.tsx`
- `frontend/src/components/{RoleSwitcher,AvatarPicker,VerificationBadge}.tsx`
- `frontend/src/services/{users,payment-methods,addresses,favorites,documents,privacy,s3-uploader}.service.ts`
- `frontend/src/hooks/useMe.ts`, `useProfileMutations.ts`
- `frontend/src/lib/api-error.ts`

### Frontend — modificar
- [frontend/src/services/api.ts](frontend/src/services/api.ts:1) (envelope interceptor)
- [frontend/src/navigation/AppNavigator.tsx](frontend/src/navigation/AppNavigator.tsx:1) (registrar screens)
- [frontend/src/store/authStore.ts](frontend/src/store/authStore.ts:1) (active_role, switch helper)
- [frontend/src/utils/auth-controller.ts](frontend/src/utils/auth-controller.ts:1)
- [frontend/src/screens/EditProfileScreen.tsx](frontend/src/screens/EditProfileScreen.tsx:1) (refactor sections)
- [frontend/package.json](frontend/package.json:1) (`@tanstack/react-query`, `expo-image-picker`, `expo-image-manipulator`)

### Reusar (sin tocar arquitectura)
- `domains/auth/*` — toda la infra de tokens, WebAuthn, OAuth se mantiene
- `domains/vehicles/Vehicle` model (CRUD migra a users router pero el modelo se queda)
- `domains/providers/ProviderProfile` model
- `domains/notifications/DeviceToken`
- `domains/audit/AuditLog`, `domains/audit/repository.py`

---

## 14. Setup de desarrollo + Mocks + Docker

### 14.1 Stack local (Docker Compose)

`docker-compose.yml` (extender el existente):

```yaml
version: "3.9"
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: raycarwash
      POSTGRES_PASSWORD: dev
      POSTGRES_DB: raycarwash
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    command: redis-server --appendonly yes
    volumes:
      - redisdata:/data

  mailhog:                          # captura emails en dev
    image: mailhog/mailhog:latest
    ports:
      - "1025:1025"                 # SMTP
      - "8025:8025"                 # UI: http://localhost:8025

  rq-worker:                        # workers RQ
    build: ./backend
    command: rq worker default low high
    depends_on: [redis, postgres]
    environment:
      RAYCARWASH_ENV: development
      DATABASE_URL: postgresql+asyncpg://raycarwash:dev@postgres/raycarwash
      REDIS_URL: redis://redis:6379/0
    volumes:
      - ./backend:/app
      - ./storage:/app/storage

  rq-scheduler:                     # cron jobs via rq-scheduler
    build: ./backend
    command: rqscheduler --host redis --port 6379 --db 0 --verbose
    depends_on: [redis]

volumes:
  pgdata:
  redisdata:
```

**Comandos iniciales**:
```powershell
docker-compose up -d postgres redis mailhog
cd backend
alembic upgrade head
python -m app.db.seed_rbac      # seedea roles + permisos
uvicorn main:app --reload --port 8000
# en otra terminal:
rq worker default low high
```

### 14.2 Adapter abstracto + selección por entorno

**Patrón uniforme**: cada servicio externo tiene una interfaz `Protocol` (PEP 544) y dos implementaciones. El `app/core/dependencies.py` provee la implementación según `RAYCARWASH_ENV`.

#### `FileStorageAdapter` (S3 / Local)

```python
# infrastructure/storage/base.py
from typing import Protocol

class FileStorageAdapter(Protocol):
    async def generate_upload_url(self, key: str, mime: str, max_size: int) -> dict: ...
    async def head_object(self, key: str) -> dict: ...
    async def generate_download_url(self, key: str, ttl_seconds: int) -> str: ...
    async def delete_object(self, key: str) -> None: ...

# infrastructure/storage/local.py
class LocalStorageAdapter:
    """Dev-only: guarda en ./storage/{bucket}/{key}, sirve via FastAPI static."""
    BASE_PATH = Path("./storage")

    async def generate_upload_url(self, key, mime, max_size):
        # Genera un "presigned" URL apuntando al endpoint local POST /dev/upload
        # con HMAC signature embedded para validar.
        return {"url": f"/dev/upload?key={quote(key)}&sig={self._sign(key)}", "method": "POST", "headers": {"Content-Type": mime}}

    async def head_object(self, key):
        p = self.BASE_PATH / key
        if not p.exists(): raise ObjectNotFound
        return {"size": p.stat().st_size, "content_type": guess_type(p.name)[0]}
    # ... etc

# infrastructure/storage/s3.py
class S3StorageAdapter:
    # TODO(prod): implementar con boto3 + presigned URLs reales + SSE-KMS
    pass

# app/core/dependencies.py
def get_storage_adapter() -> FileStorageAdapter:
    if settings.RAYCARWASH_ENV == "production":
        return S3StorageAdapter()  # TODO(prod)
    return LocalStorageAdapter()
```

Frontend (mobile + webs) consume el endpoint `/me/avatar/upload-url`. En dev recibe URL local; en prod recibe URL de S3. **Mismo contrato cliente**.

#### `PaymentMethodAdapter` (Stripe real / Stripe test)

```python
# infrastructure/payments/base.py
class PaymentMethodAdapter(Protocol):
    async def create_setup_intent(self, customer_id: str, idempotency_key: str) -> dict: ...
    async def detach_payment_method(self, pm_id: str) -> None: ...
    async def list_payment_methods(self, customer_id: str) -> list[dict]: ...

# infrastructure/payments/stripe_test.py
class StripeTestAdapter:
    """Usa Stripe API con clave de test (sk_test_...). Mismas operaciones que prod."""
    # implementación real con stripe lib, solo cambia la clave
```

**No hay "mock" de Stripe**: usamos Stripe test mode. Stripe CLI redirige webhooks a `http://localhost:8000/api/v1/payments/webhooks/stripe`. Test cards: `4242 4242 4242 4242`.

#### `EmailAdapter` (SendGrid / MailHog / Console)

```python
# infrastructure/email/base.py
class EmailAdapter(Protocol):
    async def send(self, to: str, template_id: str, data: dict) -> None: ...

# infrastructure/email/mailhog.py
class MailHogAdapter:
    """SMTP to mailhog:1025, captured in MailHog UI."""

# infrastructure/email/sendgrid.py
class SendGridAdapter:
    # TODO(prod): SendGrid API
```

#### `SmsAdapter` (Twilio trial / Console)

```python
# infrastructure/sms/console.py
class ConsoleSmsAdapter:
    """Loguea el OTP a stdout. Frontend dev muestra el valor en una toast."""
    async def send_otp(self, phone: str, code: str):
        print(f"[DEV-SMS] {phone}: {code}")

# infrastructure/sms/twilio.py
class TwilioAdapter:
    # implementación con twilio lib (trial gratuito o paid)
```

#### `GeocodingAdapter` (Google Maps / Nominatim)

```python
# infrastructure/geocoding/nominatim.py
class NominatimAdapter:
    """OSM Nominatim, rate-limit 1 req/s — suficiente para dev."""

# infrastructure/geocoding/google.py
class GoogleMapsGeocodingAdapter:
    # capa gratuita 200 USD/mes free credit, o paid
```

#### `IpGeolocationAdapter` (MaxMind / ipapi / null)

```python
# infrastructure/iploc/null.py
class NullIpLocationAdapter:
    """Devuelve None — login history queda sin ip_location en dev."""

# infrastructure/iploc/ipapi.py
class IpApiAdapter:
    """ipapi.co free tier, 1k req/día."""
```

### 14.3 Variables de entorno (.env.example a actualizar)

```env
# Entorno
RAYCARWASH_ENV=development              # development | staging | production

# Database & Redis (Docker Compose)
DATABASE_URL=postgresql+asyncpg://raycarwash:dev@localhost/raycarwash
REDIS_URL=redis://localhost:6379/0

# JWT keys (mantener los actuales)
JWT_PRIVATE_KEY_PATH=./jwt_private.pem
JWT_PUBLIC_KEY_PATH=./jwt_public.pem
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=14

# Encryption (PII)
ENCRYPTION_KEY=<32-byte-base64>
PHONE_LOOKUP_KEY=<32-byte-base64>

# Storage
STORAGE_LOCAL_PATH=./storage
# TODO(prod): AWS_S3_BUCKET_PUBLIC, AWS_S3_BUCKET_PRIVATE, AWS_REGION, CLOUDFRONT_DOMAIN, AWS_KMS_KEY_ID

# Email (MailHog en dev)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=dev@raycarwash.local
# TODO(prod): SENDGRID_API_KEY

# SMS
SMS_PROVIDER=console                    # console | twilio
# TODO(prod): TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER

# Stripe (test mode en dev)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_IDENTITY_TEMPLATE_ID=vit_...

# Geocoding
GEOCODING_PROVIDER=nominatim            # nominatim | google
# TODO(prod): GOOGLE_MAPS_API_KEY

# IP geolocation
IP_GEOLOCATION_PROVIDER=null            # null | ipapi
# TODO(prod): MAXMIND_LICENSE_KEY

# Rate limiting (slowapi)
RATE_LIMIT_AUTH_PER_MINUTE=5

# Step-up auth
STEP_UP_TTL_MINUTES=5
```

### 14.4 RQ workers — listado y triggers

Todos los workers se ejecutan en el contenedor `rq-worker`. Cron jobs via `rq-scheduler`.

| Worker | Trigger | Frequency | Queue |
|---|---|---|---|
| `pending_contact_cleanup` | cron | hourly | low |
| `login_history_purger` | cron | monthly | low |
| `audit_log_redactor` | cron | monthly | low |
| `account_deletion_finalizer` | cron | daily 03:00 | low |
| `data_export_builder` | event-driven | on POST /export | high |
| `achievement_evaluator` | cron | daily 02:00 | low |
| `document_expiry_checker` | cron | daily 01:00 | low |
| `service_reminder_dispatcher` | cron | daily 09:00 | high |

**Setup `rq-scheduler`** (en `backend/workers/schedule.py`):
```python
from rq_scheduler import Scheduler
# Define cron de cada job. Idempotent: scheduler check existing jobs.
```

### 14.5 Checklist de implementación por fase

#### Fase 0 — Foundations
- [ ] Crear `app/core/{cursor.py, idempotency.py, step_up.py, deprecation.py}`
- [ ] Crear `app/middleware/{request_id.py, structured_logging.py, audit_context.py}`
- [ ] Extender `shared/schemas.py` con `Envelope[T]`, `PaginatedEnvelope[T]`, `ErrorEnvelope`, `Meta`
- [ ] Crear `app/exception_handlers.py` y registrarlo en `main.py`
- [ ] Crear `EnvelopeRouter` base class en `app/core/envelope_router.py`
- [ ] Test `tests/api/test_envelope_compliance.py` (CI red si falta `response_model`)
- [ ] Migración `m_001_extend_audit_actions.py`
- [ ] Migración `m_001b_add_last_step_up_at.py`
- [ ] Migración `m_001c_extend_audit_log.py`
- [ ] Migración `m_001d_create_user_login_history.py`
- [ ] Crear `domains/auth/models/user_login_history.py`
- [ ] Modificar `domains/auth/service.py:authenticate_user` para popular login_history
- [ ] Crear `infrastructure/storage/{base.py, local.py}` (LocalStorageAdapter)
- [ ] Endpoint `/dev/upload` para upload local (presigned mock)
- [ ] Frontend mobile: `lib/api-error.ts`, interceptor envelope en `services/api.ts`
- [ ] Frontend admin web: cliente HTTP equivalente
- [ ] Frontend marketing web: cliente HTTP equivalente
- [ ] Añadir RQ a `requirements.txt` (`rq`, `rq-scheduler`)
- [ ] `docker-compose.yml` extendido con rq-worker, rq-scheduler, mailhog
- [ ] Actualizar `.env.example` con todas las vars nuevas
- [ ] Doc en `docs/decisions.md`: ADR-001 a ADR-008

#### Fase 1 — Recurso `/users/me`
- [ ] Migraciones m_002, m_003, m_004 (columnas User/ClientProfile/ProviderProfile)
- [ ] Crear `domains/users/services/aggregate_service.py`
- [ ] Crear `domains/users/schemas/me.py` con `MeResponse` + `?include=` parser
- [ ] Crear `domains/users/routers/me.py`
- [ ] Marcar deprecated `GET /auth/me`, `PUT /auth/update` en `domains/auth/routers/core.py`
- [ ] Cache aggregate en Redis (`profile:me:{user_id}:{token_version}:{include_hash}`)
- [ ] Frontend mobile: `UserHubScreen.tsx`, `useMe()` hook con React Query
- [ ] Añadir `@tanstack/react-query` a `frontend/package.json`
- [ ] Frontend admin: `web/app/dashboard/users/[id]/page.tsx` Overview tab
- [ ] Frontend marketing: `marketing/app/[locale]/account/page.tsx` overview
- [ ] Tests: 8+ casos (client, detailer, dual, deleted, unverified, varied include sets)

#### Fase 2 — Avatar + Storage
- [ ] Endpoints `/users/me/avatar/{upload-url, confirm, delete}` + `/cover/*`
- [ ] Adapter `LocalStorageAdapter` completo (HEAD, presigned, delete)
- [ ] Endpoint `POST /dev/upload` con validación HMAC
- [ ] `TODO(prod): S3StorageAdapter` skeleton
- [ ] Frontend mobile: `AvatarPicker.tsx`, `s3-uploader.ts`
- [ ] Añadir `expo-image-picker`, `expo-image-manipulator`
- [ ] Frontend admin: mostrar avatar en user detail
- [ ] Frontend marketing: AvatarPicker equivalente con react-dropzone
- [ ] Tests: upload-confirm flow, mime validation, size limit, HEAD verification

#### Fase 3 — Contact + Security center + History
- [ ] Migración `m_005_create_pending_contact_changes.py`
- [ ] Migración `m_005b_create_totp_credentials.py`
- [ ] Modelos + repos + services + routers
- [ ] Endpoints `/users/me/email/*`, `/users/me/phone/*`
- [ ] Endpoints `/auth/two-fa/*`, `/auth/security`, `/auth/history`, `/auth/passkeys` (admin)
- [ ] Adapter `ConsoleSmsAdapter` + interface `SmsAdapter`
- [ ] Adapter `MailHogAdapter` configurado vía SMTP
- [ ] Templates email transaccionales (change-confirm, anti-takeover, OTP fallback, etc.)
- [ ] Worker `pending_contact_cleanup` (RQ scheduled hourly)
- [ ] Worker `login_history_purger` (RQ scheduled monthly)
- [ ] Frontend mobile: SecurityScreen con tabs General + Activity, ContactChangeFlow stack
- [ ] Frontend admin: Security tab en user detail (consume /admin/users/{id}/security/history)
- [ ] Frontend marketing: Security page mirror
- [ ] Tests: contact change flows, OTP retry/lockout, anti-takeover, step-up dependency

#### Fase 4 — Client resources
- [ ] Migraciones m_006 a m_010 (addresses, payment_methods, favorites, vehicle_photos, FK defaults)
- [ ] Modelos + repos + services + routers
- [ ] Adapter Stripe (`StripeTestAdapter`) — usar Stripe test mode
- [ ] Adapter `NominatimAdapter` para geocoding
- [ ] Webhooks Stripe: `payment_method.{attached,detached,updated}`, `setup_intent.succeeded`
- [ ] Frontend mobile: PaymentMethodsScreen (Stripe CardField), AddressesScreen, FavoritesScreen, ClientPreferencesScreen, VehiclesScreen refactor + photos
- [ ] Frontend admin: read-only de payment methods + addresses
- [ ] Frontend marketing: mirror pages
- [ ] Tests: payment method sync via webhook, default unique constraints, geocoding mock

#### Fase 5 — Provider resources
- [ ] Migraciones m_011, m_012, m_013 (documents, portfolio, achievements)
- [ ] Worker `achievement_evaluator` (RQ scheduled daily)
- [ ] Worker `document_expiry_checker` (RQ scheduled daily)
- [ ] Endpoints `/users/me/provider-*`
- [ ] Deprecation de `/api/v1/detailers/me*`
- [ ] Frontend mobile: ProviderHubScreen + 6 sub-screens
- [ ] Frontend admin: Documents tab (approve/reject KYC docs)
- [ ] Tests: provider activation flow, KYC bypass blocked, achievement awarding

#### Fase 6 — Active role switcher
- [ ] Endpoint `PATCH /users/me/active-role` con rotación de refresh
- [ ] Modificar `AuthService._build_token` para leer `active_role`
- [ ] Frontend mobile: `RoleSwitcher.tsx`, auth-controller update
- [ ] Frontend admin: no aplica (admins no cambian rol)
- [ ] Frontend marketing: no aplica (web es solo cliente)
- [ ] Tests: switch valida KYC, rotación de refresh efectiva, refresh viejo → 401

#### Fase 7 — Notifications + Privacy + Public view
- [ ] Migraciones m_014, m_015
- [ ] Endpoints `/users/me/notifications/*`, `/users/me/privacy`, `/users/{id}/public`
- [ ] Integración con `notification_dispatcher` worker
- [ ] Frontend mobile: NotificationsScreen, DevicesScreen, PrivacyScreen, PublicProfileScreen
- [ ] Frontend admin: read-only privacy/notifications en user detail
- [ ] Frontend marketing: NotificationsScreen, PrivacyScreen
- [ ] Tests: visibility privacy → 404 if PRIVATE, quiet hours respected, security topic always on

#### Fase 8 — GDPR + Historiales especializados
- [ ] Migraciones m_016, m_017
- [ ] Workers `data_export_builder`, `account_deletion_finalizer` (RQ)
- [ ] Endpoints `/users/me/account/*`, history endpoints
- [ ] Frontend mobile: AccountSettingsScreen, AppointmentsHistoryScreen, PaymentHistoryScreen, ProfileChangeLogScreen, ActivityFeedScreen, ExportStatusScreen
- [ ] Frontend admin: Activity tab en user detail
- [ ] Frontend marketing: mirror history pages
- [ ] Tests: export builder genera zip correcto, deletion grace + cancel + finalizer, history filters

#### Fase 9 — Polish + Analytics + Load tests
- [ ] Migración m_018, m_019, m_020 (indices, reminder_sent, triggers)
- [ ] Endpoints `/users/me/analytics/*`
- [ ] Worker `service_reminder_dispatcher` con idempotency table
- [ ] Redis caching aggregate (TTL 5 min)
- [ ] Skeleton loaders, optimistic updates, haptics
- [ ] E2E tests Detox/Maestro
- [ ] Load test k6: `GET /users/me` default — 500 req/s p95 < 200ms
- [ ] Documentación OpenAPI exportada
- [ ] Frontend webs: skeleton loaders, polish

### 14.6 Branching strategy

- Trabajo en `feat/profile-phaseX` branches → PR a `main`.
- Cada PR cierra una fase (o un slice de fase si es muy grande).
- CI corre: backend pytest + frontend tsc + envelope compliance test + lint.
- Squash merge a main para mantener historial limpio.
- Tag semver tras cada fase mergeada: `v0.profile.0` … `v0.profile.9`.

---

## 15. Decisiones de diseño (ADRs)

Documento corto que debe materializarse en `docs/decisions.md` durante Fase 0. Explica el **por qué** detrás de las decisiones clave para que el equipo mantenga la coherencia.

### ADR-001: Separación estricta `/api/v1/auth/*` vs `/api/v1/users/me/*`

**Status**: Accepted (2026-05-14)
**Context**: la API actual fragmenta endpoints entre `/auth/me`, `/auth/update`, `/api/v1/detailers/me`, `/api/v1/vehicles`, `/api/v1/notifications/device-token`. Frontend hace 3-4 calls paralelos solo para abrir el perfil.
**Decision**: rediseñar con dos dominios claros — `/auth/*` posee credenciales/sesiones/autenticadores; `/users/me/*` posee persona/datos/preferencias.
**Consequences**:
- (+) SRP estricto, cada dominio testeable independientemente, fácil onboarding para integradores externos.
- (+) Frontend habla con un solo dominio para todo el perfil del usuario.
- (-) Lógica que cruza ambos (ej: `security_summary` en aggregate) requiere composición explícita vía `?include=`.
- (-) Migración requiere deprecation pattern + 2 sprints de coexistencia.
**Alternatives rejected**:
- Aliasing `/users/me/security/*` a `/auth/*`: dilucida responsabilidad.
- Único namespace `/api/v1/profile/*` aggregator: sigue fragmentado por debajo.

### ADR-002: Patrón `?include=` para sub-recursos opt-in

**Status**: Accepted (2026-05-14), **Superseded por ADR-002b (2026-05-15)**
**Context**: `GET /users/me` puede crecer hasta tener `stats`, `security_summary`, `defaults`, etc. — payloads pesados con queries costosas (COUNTs).
**Decision**: por defecto devolver mínimo necesario; sub-recursos costosos se piden con `?include=stats,security_summary,defaults,provider_private,recent_activity`.
**Consequences**:
- (+) Hub rápido (90% de las aperturas no necesitan stats).
- (+) Evolución sin breaking change — nuevos sub-recursos siempre arrancan opt-in.
- (+) Cache keys más granulares (1 entry por combinación de `include`).
- (-) Frontend necesita hacer 2 calls si requiere stats: `useMe()` + `useMe({include: "stats"})` — mitigado con React Query.
**Alternatives rejected**:
- Sparse fieldsets JSON:API (`?fields[user]=...`): más flexible pero overkill para nuestro tamaño.
- Devolver todo siempre: payload pesado, queries pesadas, escalabilidad mala.

### ADR-002b: Profile Hub con shape compuesto por bloques (supersede ADR-002)

**Status**: Accepted (2026-05-15)
**Context**: el patrón ADR-002 estaba bien pero el shape del response era plano (campos sueltos). Para escalar a 11+ sub-recursos y que el frontend pueda renderizar por bloque sin parsear estructura ad-hoc, evoluciona a **Profile Hub con bloques nombrados**.
**Decision**: `data` del response es un objeto compuesto: `{user, verification_badges, profile?, vehicles?, favorites?, sessions?, security?, provider?, addresses?, payment_methods?, preferences?, notifications?, stats?}`. Solo `user` y `verification_badges` siempre presentes; los demás opt-in via `?include=`. `meta.includes` confirma qué se cargó. Step-up se aplica a tokens sensibles (`security`, `sessions`). Soporte `?on_step_up=skip` para background refresh.
**Consequences**:
- (+) Shape predecible: cada bloque es self-contained, fácil de renderizar y de cachear.
- (+) Frontend pide exactamente lo que la pantalla necesita — lazy loading natural.
- (+) Step-up granular sobre tokens, no sobre todo el endpoint.
- (+) Permite evolución a `?fields[block]=...` en el futuro (sparse fieldsets dentro de bloques) sin breaking changes.
- (-) Más complejidad en el `ProfileHubService` orquestador — mitigado con `to_hub_block(user)` interface en cada sub-service.
**Alternatives rejected**:
- Mantener shape plano (ADR-002 original): no escala visualmente con 11+ sub-recursos.
- Endpoints separados por bloque (`/users/me/profile`, `/users/me/security`): N+1 calls, peor UX, peor caching.

### ADR-003: Rotación de refresh token en cambio de rol activo

**Status**: Accepted (2026-05-14)
**Context**: `PATCH /users/me/active-role` cambia el rol que el JWT trae en `role` claim. Si solo se emite nuevo access token (15-30 min TTL), un refresh robado antes del switch sigue emitiendo access tokens con el rol viejo durante 7 días.
**Decision**: rotar el refresh token igual que en cambio de password — revocar familia actual + emitir nueva.
**Consequences**:
- (+) Cierra ventana de explotación de refresh robado.
- (-) Frontend debe persistir nuevo refresh en SecureStore tras switch — mismo flujo que ya maneja en cambio password.
**Alternatives rejected**:
- Mantener refresh sin rotar: vulnerabilidad de 7 días no aceptable.
- Bump `token_version` (invalidaría TODAS las sesiones del user): muy invasivo para una acción tan rutinaria como switch role.

### ADR-004: Step-up auth con Redis primary + DB fallback

**Status**: Accepted (2026-05-14)
**Context**: dependency `require_step_up()` chequea re-auth ≤5min. Solo Redis crearía punto único de falla.
**Decision**: dual-layer — Redis primario, columna `User.last_step_up_at` como fallback. Ambos se actualizan en cada auth event (login, password verify, OAuth, passkey).
**Consequences**:
- (+) Availability: outage de Redis no bloquea operaciones sensibles si el user se autenticó hace segundos.
- (+) Misma lógica de validación en ambas capas (≤ 5min threshold).
- (-) 1 UPDATE pequeño extra en cada login — costo despreciable.

### ADR-005: Historiales especializados en vez de feed unificado

**Status**: Accepted (2026-05-14)
**Context**: un solo feed `/users/me/activity` que mezcle todo es difícil de filtrar, de paginar profundo, y de optimizar.
**Decision**: 5 endpoints especializados con shapes optimizados (`/auth/history`, `/appointments/history`, `/payments/history`, `/vehicles/history`, `/profile-changes`) + `/activity` como resumen unificado opcional (no fuente de paginación profunda).
**Consequences**:
- (+) Cada history tiene índices DB específicos y queries optimizadas.
- (+) Filtros granulares por tipo (status, vehicle_id, action, etc.).
- (+) Frontend renderiza diferente por tipo sin if/else gigantes.
- (-) Más endpoints que mantener (mitigado: services compartidos).
**Important**: el feed unificado **excluye eventos de seguridad** — esos viven solo en `/auth/history` (fuente única de verdad).

### ADR-006: Append-only audit_log con redacción ≥90d

**Status**: Accepted (2026-05-14)
**Context**: `old_value`/`new_value` JSONB crecen rápido y pueden contener PII (email viejo, dirección vieja).
**Decision**: retener completos 90d → redactar campos sensibles → archivar a Glacier ≥3 años → eliminar de Postgres.
**Consequences**:
- (+) Cumplimiento GDPR data minimization.
- (+) Postgres queda lean (audit_log crece controlado).
- (-) Forensics post-90d requieren recuperar export de S3.

### ADR-007: Response envelope explícito por endpoint (no middleware)

**Status**: Accepted (2026-05-14)
**Context**: el envelope `{data, meta, links}` puede wrappearse via middleware o declararse explícitamente.
**Decision**: explícito — `response_model=Envelope[T]` en cada endpoint. Enforcement via `EnvelopeRouter` base class (fail-fast) + test de compliance en CI.
**Consequences**:
- (+) OpenAPI auto-generado refleja el shape real con tipos completos.
- (+) Sin overhead de middleware que inspeccione cada response.
- (+) Imposible olvidar envelope (CI red).
- (-) Más boilerplate por endpoint — mitigado con generics.

### ADR-008: Storage S3 separado por sensibilidad

**Status**: Accepted (2026-05-14)
**Decision**: dos buckets:
- `raycarwash-public-assets` (avatars, covers, vehicle photos, provider portfolio) — CloudFront público con signed URLs (24h).
- `raycarwash-private-docs` (KYC, insurance, exports GDPR) — SSE-KMS, bucket privado, presigned URLs (1h).
**Consequences**:
- (+) Surface de PCI/PII contenida al bucket privado.
- (+) Avatars sirven rápido via CDN sin ir al backend.
- (-) Dos pipelines de upload — mismo adapter abstrae ambos.

---

## 16. Resumen ejecutivo

Diseño de Profile con **separación estricta de dominios bajo `/api/v1/`**:

- **`/api/v1/auth/*`** posee credenciales, sesiones, passkeys (gestión + handshakes), 2FA TOTP, password change, security summary. Es el dominio de **identidad y autenticación**.
- **`/api/v1/users/me/*`** posee perfil, preferencias, vehículos, direcciones, métodos de pago, favoritos, notificaciones, privacidad, provider-* (sub-recursos del usuario en modo detailer), GDPR (export, deletion). Es el dominio de **persona y datos**.

La API se uniformiza con: envelope `{data, meta, links}` o `{error}` **declarado explícitamente** por endpoint vía `response_model=Envelope[T]` (no middleware), cursor pagination, `Idempotency-Key`, **step-up auth con Redis primario + DB fallback** (`User.last_step_up_at`), audit logging extendido, rate-limit headers, versionado `/v1/` con deprecation pattern.

Decisiones clave: (1) **Profile Hub** `GET /users/me?include=` con shape compuesto por bloques nombrados — `user` y `verification_badges` siempre presentes; los 11 tokens opt-in son `profile`, `vehicles`, `favorites`, `sessions`, `security`, `provider`, `addresses`, `payment_methods`, `preferences`, `notifications`, `stats` (ver ADR-002b); `meta.includes` confirma qué se cargó y step-up se exige sobre los tokens sensibles (`security`, `sessions`); (2) **`PATCH /users/me/active-role`** rota refresh token + emite nuevo access (cierra ventana de refresh robado), distinto del bypass de no-rotación; (3) **deprecación gradual** con `Sunset:` header durante 2 sprints para migrar clientes.

El sistema agrega **13 entidades nuevas** (UserAddress, PaymentMethod, Document, NotificationPreference, PrivacySetting, PendingContactChange, ClientFavorite, ProviderPortfolioPhoto, ProviderAchievement, AccountDeletionRequest, DataExportRequest, TotpCredential, UserLoginHistory), extiende User/ClientProfile/ProviderProfile y AuditLog (con `old_value`, `new_value`, `ip_address`, `user_agent`, `request_id`), y se entrega en **9 fases deployable independientemente** (Fase 0 fundaciones → Fase 9 polish, analytics & escala).

**Sistema de historial diferenciado por tipo** (no un único feed genérico): `/auth/history` (logins + cambios de credenciales), `/users/me/appointments/history` (con detalles completos), `/users/me/payments/history` (con receipts), `/users/me/vehicles/history` (timeline), `/users/me/profile-changes` (audit de datos personales), `/users/me/reviews`, y `/users/me/activity` como resumen unificado opcional en el hub. Suite de endpoints analíticos en Fase 9 (`/analytics/service-frequency`, `/upcoming-reminders`, `/monthly-spending`, `/earnings`, `/rating-trend`) + worker de service reminders push.

Frontend rediseñado con **RoleSwitcher explícito** (Cliente ↔ Detailer), UserHubScreen unificado, React Query para state remoto, S3 + CloudFront para storage, y screens dedicadas por tipo de historial (AppointmentsHistoryScreen, PaymentHistoryScreen, ProfileChangeLogScreen, SecurityHistoryScreen). Seguridad reforzada por step-up con fallback, anti-takeover en cambios de contacto, PII clasificada, S3 bucket separado por sensibilidad con KMS, captura automática de ip/user_agent en audit log vía middleware. Escalable a multi-ciudad, multi-idioma y read replicas cuando aplique.

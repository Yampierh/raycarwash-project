# RayCarwash — Backend Documentation

**Versión:** Sprint 3 · **Stack:** FastAPI + PostgreSQL · **Ciudad:** Fort Wayne, Indiana

---

## 1. ¿Qué es RayCarwash?

Marketplace de detailing móvil. Un **cliente** registra su vehículo, elige un servicio, ve la disponibilidad de un **detailer**, y agenda una cita. El detailer va a domicilio. El pago se procesa con Stripe.

---

## 2. Estructura de carpetas

```
raycarwash/
├── main.py                          ← Punto de entrada: registra routers, lifespan, middleware
├── .env.example                     ← Variables de entorno requeridas (copiar a .env)
├── requirements.txt
├── alembic.ini                      ← Configuración de migraciones
├── alembic/
│   ├── env.py                       ← Alembic async-compatible con SQLAlchemy 2.0
│   └── versions/                    ← Archivos de migración generados
│
└── app/
    ├── core/
    │   └── config.py                ← Settings (pydantic-settings, .env, validaciones)
    │
    ├── db/
    │   ├── session.py               ← Engine asyncpg + get_db (dependency FastAPI)
    │   └── seed.py                  ← SIZE_MULTIPLIERS + catálogo de servicios
    │
    ├── models/
    │   └── models.py                ← ORM SQLAlchemy 2.0 (todas las tablas)
    │
    ├── schemas/
    │   └── schemas.py               ← Pydantic v2 (request/response contracts)
    │
    ├── repositories/                ← Capa de acceso a datos (SQL puro, sin lógica)
    │   ├── user_repository.py
    │   ├── vehicle_repository.py
    │   ├── service_repository.py
    │   ├── appointment_repository.py
    │   ├── detailer_repository.py
    │   ├── review_repository.py
    │   └── audit_repository.py
    │
    ├── services/                    ← Lógica de negocio (aquí viven las reglas)
    │   ├── auth.py                  ← bcrypt, JWT, get_current_user dependency
    │   ├── appointment_service.py   ← Motor de precios + disponibilidad + state machine
    │   ├── review_service.py        ← Validaciones de review post-COMPLETED
    │   └── payment_service.py       ← Scaffold de Stripe (stub listo para activar)
    │
    └── routers/                     ← Adaptadores HTTP (solo traducen HTTP ↔ Python)
        ├── auth_router.py
        ├── vehicle_router.py
        ├── service_router.py
        ├── appointment_router.py
        ├── detailer_router.py
        ├── payment_router.py
        └── review_router.py
```

---

## 3. Arquitectura en capas

```
HTTP Request
     │
     ▼
┌──────────────────┐
│   Router         │  Solo valida parámetros HTTP, llama al Service.
│  (routers/)      │  No contiene ninguna regla de negocio.
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Service        │  Toda la lógica de negocio vive aquí.
│  (services/)     │  Llama a uno o varios Repositories.
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Repository      │  Solo SQL. Devuelve objetos ORM. Sin lógica.
│ (repositories/)  │  Los Services no saben de SQLAlchemy.
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   PostgreSQL     │  asyncpg driver, pool gestionado por el Engine.
└──────────────────┘
```

**Regla de oro:** si una función tiene un `if` de negocio, pertenece al Service, no al Router ni al Repository.

---

## 4. Modelos de base de datos

### 4.1 Tablas principales

| Tabla              | Descripción |
|--------------------|-------------|
| `users`            | Clientes, detailers y admins. Un campo `role` discrimina. |
| `detailer_profiles`| Extensión 1:1 de `users` para detailers (horarios, bio, rating). |
| `vehicles`         | Vehículos registrados por clientes. El campo `size` determina el precio. |
| `services`         | Catálogo de servicios con precios base y por tamaño. |
| `appointments`     | La reserva que une client ↔ detailer ↔ vehicle ↔ service. |
| `reviews`          | Rating post-servicio (solo tras COMPLETED). 1 por cita. |
| `audit_logs`       | Trail de auditoría inmutable (solo INSERT, nunca UPDATE/DELETE). |

### 4.2 Enums importantes

```python
class UserRole(str, Enum):
    CLIENT = "client"
    DETAILER = "detailer"
    ADMIN = "admin"

class VehicleSize(str, Enum):
    SMALL = "small"    # Sedán / Coupe     → multiplier ×1.0
    MEDIUM = "medium"  # SUV / Crossover   → multiplier ×1.2
    LARGE = "large"    # Camioneta grande  → multiplier ×1.5
    XL = "xl"          # Van / Sprinter    → multiplier ×2.0

class AppointmentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED_BY_CLIENT = "cancelled_by_client"
    CANCELLED_BY_DETAILER = "cancelled_by_detailer"
    NO_SHOW = "no_show"
```

### 4.3 Soft deletes

**Todos** los modelos importantes tienen `is_deleted` (bool) y `deleted_at` (datetime UTC). Los datos nunca se borran físicamente. Todos los queries de los repositories filtran `is_deleted == False` por defecto.

---

## 5. Sistema de precios

El precio se calcula **en el momento de crear la cita** y queda grabado de forma inmutable en `appointment.estimated_price` (en centavos USD). Aunque el precio base del servicio cambie después, la cita ya registrada mantiene su precio original.

### Fórmula

```
estimated_price = ceil(service.base_price_cents × SIZE_MULTIPLIERS[vehicle.size])
duration_minutes = ceil(service.base_duration_minutes × SIZE_MULTIPLIERS[vehicle.size])
```

### Tabla de precios (catálogo seeded)

| Servicio        | Base (SMALL) | MEDIUM ×1.2 | LARGE ×1.5 | XL ×2.0  |
|-----------------|-------------|-------------|------------|----------|
| Express Wash    | $50.00      | $60.00      | $75.00     | $100.00  |
| Interior Detail | $150.00     | $180.00     | $225.00    | $300.00  |
| Diamond Detail  | $250.00     | $300.00     | $375.00    | **$500.00** |

> **Ejemplo real:** GMC Sierra (XL) + Diamond Detail → `ceil(25000 × 2.0) = 50000¢ = $500.00`

> `ceil()` siempre redondea hacia arriba en precios y duraciones: protege ingresos y da más tiempo al detailer.

---

## 6. API Reference

> **Base URL:** `https://api.raycarwash.com`
> **Auth:** `Authorization: Bearer <access_token>` en todos los endpoints protegidos.
> **Respuesta de error estándar:** `{ "code": "ERROR_CODE", "message": "..." }`

### Auth

| Método | Endpoint         | Auth | Descripción |
|--------|-----------------|------|-------------|
| POST   | `/auth/token`   | ❌   | Login. Body: `application/x-www-form-urlencoded` con `username` y `password`. Devuelve `access_token` + `refresh_token`. |
| POST   | `/auth/refresh` | ❌   | Rota el refresh token. Devuelve un par nuevo de tokens. |
| GET    | `/auth/me`      | ✅   | Perfil del usuario autenticado. |

> ⚠️ `/auth/token` usa **form-encoded**, no JSON. En Axios: `Content-Type: application/x-www-form-urlencoded`.

### Users

| Método | Endpoint           | Auth | Descripción |
|--------|--------------------|------|-------------|
| POST   | `/api/v1/users`    | ❌   | Registro. Role `admin` está bloqueado por el schema. |

### Services (público)

| Método | Endpoint                       | Auth | Descripción |
|--------|-------------------------------|------|-------------|
| GET    | `/api/v1/services`            | ❌   | Lista todos los servicios activos con precios por tamaño. |
| GET    | `/api/v1/services/{id}`       | ❌   | Detalle de un servicio específico. |

### Vehicles

| Método | Endpoint               | Auth | Descripción |
|--------|------------------------|------|-------------|
| POST   | `/api/v1/vehicles`     | ✅ CLIENT | Registra un vehículo. `owner_id` se extrae del JWT. |
| GET    | `/api/v1/vehicles`     | ✅ CLIENT | Lista los vehículos del usuario autenticado. |

### Appointments

| Método | Endpoint                                   | Auth | Descripción |
|--------|--------------------------------------------|------|-------------|
| POST   | `/api/v1/appointments`                     | ✅ CLIENT | Crea una cita. Calcula precio, verifica disponibilidad con advisory lock. |
| GET    | `/api/v1/appointments/mine`                | ✅   | Lista paginada. Clientes ven sus citas; detailers ven las suyas. |
| GET    | `/api/v1/appointments/{id}`                | ✅   | Detalle. Solo participantes o admin. |
| PATCH  | `/api/v1/appointments/{id}/status`         | ✅   | Avanza la state machine. Ver sección 7. |

### Detailers

| Método | Endpoint                               | Auth | Descripción |
|--------|----------------------------------------|------|-------------|
| GET    | `/api/v1/detailers/{id}/availability`  | ❌   | Slots de 30 min para una fecha. Acepta `service_id` + `vehicle_size` para calcular disponibilidad real. |
| GET    | `/api/v1/detailers/{id}/profile`       | ❌   | Perfil público: bio, rating, horarios. |
| POST   | `/api/v1/detailers/location`           | ✅ DETAILER | Actualiza coordenadas GPS del detailer en turno. |

### Payments

| Método | Endpoint                          | Auth | Descripción |
|--------|----------------------------------|------|-------------|
| POST   | `/api/v1/payments/create-intent` | ✅ CLIENT | Crea un PaymentIntent de Stripe (idempotente). Devuelve `client_secret`. |

### Reviews

| Método | Endpoint                              | Auth | Descripción |
|--------|---------------------------------------|------|-------------|
| POST   | `/api/v1/reviews`                     | ✅ CLIENT | Crea una review. Solo tras cita COMPLETED. 1 por cita. |
| GET    | `/api/v1/reviews/detailer/{id}`       | ❌   | Reviews paginadas de un detailer. |

### Infrastructure

| Método | Endpoint    | Auth | Descripción |
|--------|-------------|------|-------------|
| GET    | `/health`   | ❌   | Liveness probe. Devuelve `{ status, db_reachable }`. |

---

## 7. State Machine — Ciclo de vida de una cita

```
                        [DETAILER / ADMIN]
    ┌──────────┐ ─────────────────────────── ► ┌───────────┐
    │ PENDING  │                               │ CONFIRMED │
    └──────────┘ ◄──────────────────────────── └───────────┘
         │         [CLIENT / DETAILER / ADMIN]       │
         │                                            │ [DETAILER / ADMIN]
         │                                            ▼
         │                                    ┌─────────────┐
         │                                    │ IN_PROGRESS │
         │                                    └─────────────┘
         │                                            │
         │                                            │ [DETAILER / ADMIN]
         │                                            ▼
         │                                    ┌───────────┐
         │                                    │ COMPLETED │ ← requiere actual_price
         │                                    └───────────┘
         │
         ├──► CANCELLED_BY_CLIENT    (client / admin)
         ├──► CANCELLED_BY_DETAILER  (detailer / admin)
         └──► NO_SHOW               (detailer / admin, desde IN_PROGRESS)
```

**Reglas:**
- Estados terminales (`COMPLETED`, `CANCELLED_*`, `NO_SHOW`) no tienen transiciones salientes.
- `PATCH /appointments/{id}/status` con `status: "completed"` **requiere** `actual_price` en el body (centavos USD).
- El service stampa `started_at` al pasar a `IN_PROGRESS` y `completed_at` al pasar a `COMPLETED`.

---

## 8. Disponibilidad y buffer de viaje

El endpoint de disponibilidad genera un grid de slots de **30 minutos** dentro del horario laboral del detailer y marca cada uno como `is_available: true/false`.

**Un slot queda bloqueado si:**
1. Ya pasó (o está dentro de 1 hora desde ahora — mínimo de anticipo).
2. La ventana del servicio completo (`duration + 30 min de buffer de viaje`) no cabe antes del final del día.
3. La ventana del servicio se solapa con alguna cita existente (incluyendo su buffer de viaje).

**Buffer de viaje:** 30 minutos fijos después de cada cita. El detailer no puede iniciar una nueva cita hasta que `estimated_end_time + 30 min` haya pasado.

**Parámetros del endpoint:**
```
GET /api/v1/detailers/{id}/availability
  ?request_date=2025-12-20          ← YYYY-MM-DD (requerido)
  &service_id=<uuid>                ← opcional, para calcular duración real
  &vehicle_size=xl                  ← requerido si se envía service_id
```

---

## 9. Seguridad

### JWT
- **Access token:** 30 minutos. Se adjunta a cada request como `Authorization: Bearer <token>`.
- **Refresh token:** 7 días. Se envía **únicamente** a `POST /auth/refresh`. Debe guardarse en Keychain/Keystore (nunca en AsyncStorage).
- **Type discriminator:** los tokens tienen un campo interno `"type": "access"` o `"type": "refresh"`. Usar un refresh token como access token devuelve 401.

### Protecciones aplicadas
| Amenaza | Mitigación |
|---------|-----------|
| Enumeración de usuarios | Login devuelve 401 genérico + `dummy_verify()` en bcrypt (tiempo constante) |
| IDOR en vehículos | `owner_id` se extrae del JWT, nunca del body |
| IDOR en citas | Solo participantes o admin pueden leer/modificar |
| Race condition en bookings | `pg_advisory_xact_lock` por UUID del detailer |
| SQL injection | SQLAlchemy ORM con parámetros vinculados |
| Datos sensibles en respuesta | `password_hash`, `is_deleted`, `deleted_at` excluidos de todos los schemas de lectura |

### Concurrencia (advisory locks)
Cuando dos requests intentan crear una cita para el mismo detailer al mismo tiempo:
1. El primero en llegar adquiere `pg_advisory_xact_lock(hash(detailer_id))`.
2. El segundo bloquea hasta que el primero hace COMMIT o ROLLBACK.
3. El segundo re-verifica el overlap y falla con 409 si el slot ya fue tomado.

---

## 10. Pago con Stripe

El flujo sigue el patrón recomendado por Stripe para apps móviles:

```
Cliente                  Backend                    Stripe
   │                        │                          │
   │──POST /create-intent──►│                          │
   │                        │──CreatePaymentIntent────►│
   │                        │◄──{client_secret}────────│
   │◄──{client_secret}──────│                          │
   │                        │                          │
   │──stripe.confirmPayment(client_secret)────────────►│
   │                        │                          │
   │◄──payment_intent.succeeded (webhook)──────────────│
```

Los datos de tarjeta **nunca tocan el backend**. Esto permite certificación PCI SAQ A (la más simple).

> **Estado actual:** El endpoint existe y es funcional (devuelve un `client_secret` stub). Para activar Stripe real, reemplazar los bloques `TODO_STRIPE` en `payment_service.py` con llamadas al SDK.

---

## 11. Quickstart local

### Prerrequisitos
- Python 3.12+
- PostgreSQL 15+

### Instalación

```bash
git clone <repo>
cd raycarwash

# Entorno virtual
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# Dependencias
pip install -r requirements.txt

# Variables de entorno
cp .env.example .env
# Editar .env:
#   DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/raycarwash_db
#   SECRET_KEY=<openssl rand -hex 32>
#   STRIPE_SECRET_KEY=sk_test_...  (opcional para MVP)

# Crear base de datos
createdb raycarwash_db

# Levantar servidor
uvicorn main:app --reload --port 8000
```

La app en startup:
1. Crea las tablas automáticamente (`create_all` — solo para dev).
2. Inserta el catálogo de 3 servicios si no existe.

Swagger disponible en `http://localhost:8000/docs` (solo con `DEBUG=true`).

### Migraciones (staging/producción)

```bash
# Generar migración tras cambios en models.py
alembic revision --autogenerate -m "describe_change"

# Revisar el archivo generado en alembic/versions/

# Aplicar
alembic upgrade head
```

> En producción: ejecutar `alembic upgrade head` en CI/CD **antes** de deployar el código nuevo. Nunca usar `create_all` en producción.

### Tests

```bash
# Requiere una DB de test: createdb raycarwash_test
pytest -v
```

---

## 12. Variables de entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://user:pass@host:5432/db` |
| `SECRET_KEY` | ✅ | 256-bit hex. `openssl rand -hex 32` |
| `STRIPE_SECRET_KEY` | ⚠️ | `sk_test_*` en dev, `sk_live_*` en prod |
| `STRIPE_WEBHOOK_SECRET` | ⚠️ | Para verificar webhooks de Stripe |
| `DEBUG` | ❌ | `true` activa Swagger UI y SQL logging |
| `TRAVEL_BUFFER_MINUTES` | ❌ | Default: 30 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | Default: 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | ❌ | Default: 7 |
| `ALLOWED_ORIGINS` | ❌ | Default: `["http://localhost:3000","http://localhost:8081"]` |

---

## 13. Decisiones técnicas clave

| Decisión | Razón |
|----------|-------|
| `asyncpg` sobre `psycopg2` | I/O no bloqueante real. psycopg2 con async engine causa deadlocks. |
| SQLAlchemy 2.0 `Mapped[]` style | Tipado estático completo. mypy/IDEs infieren tipos de columnas sin hacks. |
| Advisory locks (no `FOR UPDATE`) | `FOR UPDATE` no bloquea cuando no hay filas previas (slot vacío). El lock por UUID del detailer serializa concurrent bookings sin afectar otros detailers. |
| Precios en centavos enteros | Elimina errores de floating-point. `50000` es inequívoco; `500.0000000001` no. |
| `ceil()` en precios y duraciones | Redondear hacia arriba protege ingresos y da más tiempo al detailer. Nunca hacia abajo. |
| Soft deletes | Mantiene integridad referencial, auditoría, y cumplimiento GDPR (sabes qué borrar). |
| Schemas separados de modelos | Evita exponer campos internos (`password_hash`, `is_deleted`) por accidente. Es el principal vector del OWASP A01. |
| Tokens JWT como refresh tokens (MVP) | Stateless, sin tabla extra. Trade-off: no revocables individualmente. Sprint 4: tabla `refresh_tokens` con `revoked_at`. |

---

## 14. Integración con el frontend

### Flujo de booking end-to-end

```
1. GET  /api/v1/services
   → Mostrar catálogo con precios por tamaño

2. GET  /api/v1/vehicles
   → Mostrar vehículos del cliente (requiere auth)

3. GET  /api/v1/detailers/{id}/availability
     ?request_date=YYYY-MM-DD&service_id=...&vehicle_size=xl
   → Mostrar grid de slots disponibles

4. POST /api/v1/appointments
   {
     "detailer_id": "...",
     "vehicle_id": "...",
     "service_id": "...",
     "scheduled_time": "2025-12-20T17:00:00Z",  ← Z obligatorio
     "service_address": "4321 Dupont Rd, Fort Wayne, IN 46825"
   }
   → Devuelve cita con estimated_price calculado

5. POST /api/v1/payments/create-intent
   { "appointment_id": "..." }
   → Devuelve client_secret para Stripe SDK

6. stripe.confirmPayment({ clientSecret })
   → Pago directo con Stripe (datos de tarjeta nunca llegan al backend)

7. PATCH /api/v1/appointments/{id}/status
   { "status": "confirmed" }
   → Detailer confirma la cita (tras confirmar el pago via webhook)
```

### Tipos de respuesta más usados

```typescript
// Cita creada
{
  id: string
  estimated_price: number   // centavos → dividir entre 100 para dólares
  estimated_end_time: string // ISO 8601 UTC
  travel_buffer_end_time: string
  status: "pending"
}

// Slot de disponibilidad
{
  start_time: string   // ISO 8601 UTC
  end_time: string     // start + 30 min
  is_available: boolean
}

// Servicio
{
  price_small: number   // centavos para SMALL
  price_medium: number  // centavos para MEDIUM
  price_large: number   // centavos para LARGE
  price_xl: number      // centavos para XL  ← usar este para GMC Sierra
}
```

---

## 15. Roadmap — Sprint 4

| Prioridad | Tarea |
|-----------|-------|
| 🔴 | Activar Stripe SDK real (`TODO_STRIPE` en `payment_service.py`) |
| 🔴 | `POST /webhooks/stripe` para recibir `payment_intent.succeeded` |
| 🔴 | Reemplazar `create_all` por `alembic upgrade head` en CI/CD |
| 🟠 | Tabla `refresh_tokens` con `revoked_at` (revocación individual) |
| 🟠 | `GET /api/v1/detailers` — lista de detailers activos con filtro por zona |
| 🟠 | `POST /api/v1/detailers/profile` — onboarding de nuevos detailers |
| 🟠 | Rate limiting con `slowapi` en `POST /auth/token` |
| 🟡 | Timezone real (America/Indiana/Indianapolis) en slot generation |
| 🟡 | WebSocket o Redis para pings de GPS de alta frecuencia |
| 🟡 | `GET /api/v1/users/{id}` — perfil de cliente para panel de admin |

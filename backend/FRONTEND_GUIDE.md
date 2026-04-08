# Frontend Guide — RayCarwash API

**Versión:** Sprint 4 (actual) + Sprint 5 (roadmap)
**Stack backend:** FastAPI + PostgreSQL · **Ciudad:** Fort Wayne, Indiana

---

## Decisiones de producto confirmadas

| Tema | Decisión |
|------|---------|
| Asignación de detailer | Sistema muestra matches ordenados por proximidad/rating. El mejor queda preseleccionado pero el cliente elige libremente. |
| Fecha/hora | Opcional — si no se especifica → modo ASAP (detailer más cercano disponible ahora). Si se especifica → búsqueda en esa fecha. |
| Addons | Extras opcionales apilables sobre el servicio principal (precio + duración se suman). |
| Múltiples vehículos | El cliente puede lavar varios carros en una sola cita. Precio y duración totales = suma por cada vehículo. |

---

## Flujo del cliente (correcto)

```
1. Registro / Login
2. Registrar vehículo(s)
3. Iniciar reserva:
   a. Seleccionar vehículo(s) a lavar (uno o varios)
   b. Seleccionar servicio principal  (ej. Full Detail)
   c. Seleccionar addons opcionales   (ej. Clay Bar +$30, Odor Eliminator +$20)
4. ¿Cuándo? (campo opcional)
   → Sin fecha → modo ASAP: sistema busca el detailer más cercano disponible ahora
   → Con fecha → sistema muestra detailers con slots ese día
5. Sistema muestra lista de detailers compatibles:
   - Ordenados por: proximidad + rating + disponibilidad
   - El mejor queda preseleccionado automáticamente
   - El cliente puede elegir cualquier otro y ver sus slots disponibles
6. Cliente confirma detailer + slot → cita creada (status: PENDING)
7. Detailer confirma                → status: CONFIRMED
8. Cliente paga con Stripe
9. Detailer llega                  → status: IN_PROGRESS
10. Servicio termina               → status: COMPLETED
11. Cliente deja review
```

## Flujo del detailer

```
1. Registro → Login
2. POST /api/v1/detailers/profile  (onboarding: bio, horarios, radio de servicio)
3. (App activa) POST /api/v1/detailers/location  cada 30 segundos
4. GET  /api/v1/appointments/mine                ver solicitudes entrantes
5. PATCH status → confirmed                      confirmar cita
6. PATCH status → in_progress                    iniciar servicio
7. PATCH status → completed + actual_price       finalizar
8. PATCH /api/v1/detailers/profile { is_accepting_bookings: false }  pausar
```

---

## Base URL

```
https://api.raycarwash.com   ← producción
http://localhost:8000        ← local dev
```

---

## Autenticación

### Cómo funciona
- **JWT Bearer tokens** en el header `Authorization: Bearer <access_token>`
- Access token expira en **30 minutos**
- Refresh token expira en **7 días** — guardar en Keychain/Keystore (nunca AsyncStorage)

### Login
```
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=user@email.com&password=mi_password
```
Respuesta:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```
> Rate limit: **10 intentos/minuto por IP** → HTTP 429 si se excede.

### Renovar token
```
POST /auth/refresh?refresh_token=eyJ...
```
Respuesta: mismo formato que login (ambos tokens renovados).

### Perfil propio
```
GET /auth/me
Authorization: Bearer <access_token>
```

### Registro
```
POST /api/v1/users
Content-Type: application/json

{
  "email": "user@email.com",
  "full_name": "Jane Doe",
  "phone_number": "+12605550100",   ← opcional
  "password": "min8chars",
  "role": "client"                  ← "client" | "detailer"
}
```
Respuesta: `UserRead` (201 Created)

> Después de registrarse como `detailer`, llamar a `POST /api/v1/detailers/profile` para completar el onboarding.

---

## Modelos de datos (TypeScript)

### UserRead
```typescript
{
  id: string;              // UUID
  email: string;
  full_name: string;
  phone_number: string | null;
  role: "client" | "detailer" | "admin";
  is_active: boolean;
  is_verified: boolean;
  created_at: string;      // ISO 8601 UTC
  updated_at: string;
}
```

### VehicleRead
```typescript
{
  id: string;
  owner_id: string;
  make: string;            // "Kia"
  model: string;           // "K5"
  year: number;            // 2023
  vin: string | null;
  series: string | null;   // "GT-Line"
  body_class: string | null; // "Sedan"
  color: string;
  license_plate: string;
  suggested_size: "small" | "medium" | "large" | "xl" | null; // calculado
  created_at: string;
  updated_at: string;
}
```

### ServiceRead
```typescript
{
  id: string;
  name: string;
  description: string | null;
  category: "basic_wash" | "interior_detail" | "full_detail" | "ceramic_coating" | "paint_correction";
  base_price_cents: number;         // precio base en centavos
  base_duration_minutes: number;
  price_small: number;              // centavos según tamaño
  price_medium: number;
  price_large: number;
  price_xl: number;
  duration_small_minutes: number;
  duration_medium_minutes: number;
  duration_large_minutes: number;
  duration_xl_minutes: number;
  is_active: boolean;
}
```
> Divide entre 100 para mostrar dólares: `price_small / 100 → $X.XX`

### AppointmentRead
```typescript
{
  id: string;
  client_id: string;
  detailer_id: string;
  vehicle_id: string;
  service_id: string;
  scheduled_time: string;          // ISO 8601 UTC
  estimated_end_time: string;      // UTC
  travel_buffer_end_time: string;  // UTC
  status: AppointmentStatus;
  estimated_price: number;         // centavos
  actual_price: number | null;     // centavos, solo en COMPLETED
  started_at: string | null;       // UTC
  completed_at: string | null;     // UTC
  stripe_payment_intent_id: string | null;
  client_notes: string | null;
  detailer_notes: string | null;
  service_address: string;
  service_latitude: number | null;
  service_longitude: number | null;
  created_at: string;
  updated_at: string;
}

type AppointmentStatus =
  | "pending"
  | "confirmed"
  | "in_progress"
  | "completed"
  | "cancelled_by_client"
  | "cancelled_by_detailer"
  | "no_show";
```

### DetailerProfileRead
```typescript
{
  id: string;
  user_id: string;
  bio: string | null;
  years_of_experience: number | null;
  is_accepting_bookings: boolean;
  service_radius_miles: number;
  timezone: string;                // IANA: "America/Indiana/Indianapolis"
  working_hours: {
    monday:    { start: string; end: string; enabled: boolean };
    tuesday:   { start: string; end: string; enabled: boolean };
    wednesday: { start: string; end: string; enabled: boolean };
    thursday:  { start: string; end: string; enabled: boolean };
    friday:    { start: string; end: string; enabled: boolean };
    saturday:  { start: string | null; end: string | null; enabled: boolean };
    sunday:    { start: string | null; end: string | null; enabled: boolean };
  };
  average_rating: number | null;   // 1.00 – 5.00
  total_reviews: number;
  created_at: string;
}
```

### DetailerPublicRead (tarjeta de discovery)
```typescript
{
  user_id: string;
  full_name: string;
  bio: string | null;
  years_of_experience: number | null;
  service_radius_miles: number;
  is_accepting_bookings: boolean;
  average_rating: number | null;
  total_reviews: number;
  distance_miles: number | null;   // solo cuando buscas por lat/lng
}
```

### ReviewRead
```typescript
{
  id: string;
  appointment_id: string;
  reviewer_id: string;
  detailer_id: string;
  rating: number;        // 1–5
  comment: string | null;
  created_at: string;
}
```

### TimeSlotRead
```typescript
{
  start_time: string;   // ISO 8601 UTC
  end_time: string;     // start + 30 minutos
  is_available: boolean;
}
```

### PaginatedResponse\<T\>
```typescript
{
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
```

---

## Endpoints completos (Sprint 4)

### Servicios — Público
```
GET  /api/v1/services           → ServiceRead[]
GET  /api/v1/services/{id}      → ServiceRead
```

### Vehículos — Requiere CLIENT
```
POST /api/v1/vehicles               → VehicleRead (201)
GET  /api/v1/vehicles               → VehicleRead[]
GET  /api/v1/vehicles/lookup/{vin}  → { make, model, year, series, body_class, suggested_size }
```
Body para POST:
```json
{
  "make": "Kia",
  "model": "K5",
  "year": 2023,
  "body_class": "Sedan",
  "color": "Blue",
  "license_plate": "FWT-821",
  "vin": "1HGCM82633A003241",   // opcional
  "series": "GT-Line"            // opcional
}
```

### Detailers — Público (sin auth)
```
GET /api/v1/detailers                    → PaginatedResponse<DetailerPublicRead>
GET /api/v1/detailers/{id}/profile       → DetailerProfileRead
GET /api/v1/detailers/{id}/availability  → TimeSlotRead[]
```

Query params para discovery:
```
?lat=41.13&lng=-85.13&radius_miles=25&min_rating=4.0&page=1&page_size=20
```

Query params para availability:
```
?request_date=2025-06-15&service_id=uuid&vehicle_size=medium
```
> `vehicle_size` es requerido cuando se envía `service_id`

### Detailer Onboarding — Requiere DETAILER
```
POST  /api/v1/detailers/profile  → DetailerProfileRead (201)
PATCH /api/v1/detailers/profile  → DetailerProfileRead
POST  /api/v1/detailers/location → LocationResponse
```

Body para POST /profile:
```json
{
  "bio": "Profesional con 5 años de experiencia",
  "years_of_experience": 5,
  "service_radius_miles": 25,
  "timezone": "America/Indiana/Indianapolis",
  "working_hours": {
    "monday": { "start": "09:00", "end": "17:00", "enabled": true },
    "sunday": { "start": null, "end": null, "enabled": false }
  }
}
```
> `working_hours` es opcional. Default: lunes–sábado 08:00–18:00.

Body para PATCH /profile (solo campos a cambiar):
```json
{ "is_accepting_bookings": false }
```

Body para POST /location:
```json
{ "latitude": 41.1306, "longitude": -85.1289 }
```

### Citas — Requiere auth
```
POST  /api/v1/appointments              → AppointmentRead (201)  [CLIENT]
GET   /api/v1/appointments/mine         → PaginatedResponse      [CLIENT | DETAILER]
GET   /api/v1/appointments/{id}         → AppointmentRead        [participante]
PATCH /api/v1/appointments/{id}/status  → AppointmentRead        [según rol]
```

Body para POST (Sprint 4 — un solo vehículo):
```json
{
  "detailer_id": "uuid",
  "vehicle_id": "uuid",
  "service_id": "uuid",
  "scheduled_time": "2025-06-15T14:00:00Z",
  "service_address": "4321 Dupont Rd, Fort Wayne, IN 46825",
  "service_latitude": 41.1306,
  "service_longitude": -85.1289,
  "client_notes": "Carro muy sucio"
}
```

Body para PATCH /status:
```json
{
  "status": "confirmed",
  "detailer_notes": "Estaré puntual",
  "actual_price": 5000
}
```
> `actual_price` es **obligatorio** únicamente cuando `status = "completed"`.

### Tabla de transiciones de estado
| Desde | Hacia | Quién puede |
|-------|-------|-------------|
| pending | confirmed | detailer / admin |
| pending | cancelled_by_client | client / admin |
| pending | cancelled_by_detailer | detailer / admin |
| confirmed | in_progress | detailer / admin |
| confirmed | cancelled_by_client | client / admin |
| confirmed | cancelled_by_detailer | detailer / admin |
| in_progress | completed | detailer / admin |
| in_progress | no_show | detailer / admin |

**Política de cancelación (reembolso):**
- Cancelación > 24 h antes → reembolso 100 %
- Cancelación 2–24 h antes → reembolso 50 %
- Cancelación < 2 h antes → sin reembolso

### Pagos — Requiere CLIENT
```
POST /api/v1/payments/create-intent  → PaymentIntentResponse
```
Body: `{ "appointment_id": "uuid" }`

Respuesta:
```json
{
  "payment_intent_id": "pi_xxx",
  "client_secret": "pi_xxx_secret_xxx",
  "amount_cents": 5000,
  "currency": "usd",
  "status": "requires_payment_method"
}
```
> Pasar `client_secret` al Stripe SDK del frontend. La cita debe estar en `confirmed`.

### Reviews — CLIENT puede crear, público puede leer
```
POST /api/v1/reviews                  → ReviewRead (201)  [CLIENT]
GET  /api/v1/reviews/detailer/{id}    → PaginatedResponse<ReviewRead>
```
Body para POST:
```json
{
  "appointment_id": "uuid",
  "rating": 5,
  "comment": "Excelente servicio"
}
```
> Solo se puede dejar review si el appointment está en `completed`.

### Health
```
GET /health → { "status": "ok" | "degraded", "db_reachable": bool, ... }
```

---

## Integración con Stripe (frontend)

```typescript
import { loadStripe } from '@stripe/stripe-js';

// 1. Pedir client_secret al backend
const { client_secret } = await api.post('/api/v1/payments/create-intent', {
  appointment_id: appointmentId,
});

// 2. Cobrar con Stripe SDK — la tarjeta NUNCA pasa por el backend
const stripe = await loadStripe('pk_test_...');
const result = await stripe.confirmCardPayment(client_secret, {
  payment_method: { card: cardElement },
});

if (result.error) {
  // mostrar error al usuario
} else if (result.paymentIntent.status === 'succeeded') {
  // pago exitoso — el webhook del backend ya registró el resultado
}
```

---

## Manejo de errores

### Códigos HTTP
| HTTP | Cuándo |
|------|--------|
| 400 | Error de negocio (auto-booking, rol incorrecto) |
| 401 | Token inválido, expirado o faltante |
| 403 | Sin permisos para esta acción |
| 404 | Recurso no encontrado |
| 409 | Conflicto (email ya registrado, slot ocupado) |
| 413 | Payload mayor a 5 MB |
| 422 | Validación fallida (campos inválidos o faltantes) |
| 429 | Rate limit excedido |

### Formato del cuerpo de error
```json
{
  "code": "EMAIL_TAKEN",
  "message": "An account with 'user@email.com' already exists.",
  "details": null
}
```

---

## Headers importantes
```
Authorization: Bearer <access_token>   ← auth (todos los endpoints protegidos)
Content-Type: application/json         ← para bodies JSON
X-Process-Time-Ms: <ms>               ← tiempo de procesamiento (útil para debug)
```

---

## Timezones

- Todos los timestamps en la API están en **UTC** (ISO 8601 terminando en `Z` o `+00:00`)
- `DetailerProfile.timezone` contiene el IANA name del detailer (ej. `"America/Indiana/Indianapolis"`)
- El frontend debe convertir los slots de UTC a la timezone local del usuario para mostrarlos
- Ejemplo: slot `14:00Z` en `America/Indiana/Indianapolis` (UTC-4 en verano) = `10:00 AM`

---

## Paginación

Todos los endpoints de lista aceptan `?page=1&page_size=20` y retornan:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5
}
```

---

## Stack recomendado para el frontend

**React Native (Expo):**
- HTTP: Axios con interceptores para refresh token automático
- Auth storage: `expo-secure-store` para refresh_token; memoria para access_token
- Pagos: `@stripe/stripe-react-native`
- Mapas: `react-native-maps` (mostrar detailers cercanos)
- Estado global: Zustand o Redux Toolkit

**Next.js (web):**
- HTTP: Axios / SWR / React Query
- Auth: NextAuth.js con JWT strategy
- Pagos: `@stripe/react-stripe-js`

---

## Sprint 5 — Nuevas funcionalidades en roadmap

Estas APIs **aún no existen** en el backend pero serán implementadas en Sprint 5 para soportar el flujo completo.

### Nuevo endpoint de matching

```
GET /api/v1/matching
  ?service_id=uuid
  &addon_ids=uuid1,uuid2
  &vehicle_ids=uuid1,uuid2
  &lat=41.13
  &lng=-85.12
  &requested_time=2025-06-15T14:00:00Z   ← omitir para modo ASAP
```

Respuesta (array ordenado, índice 0 = recomendado):
```typescript
{
  user_id: string;
  full_name: string;
  average_rating: number | null;
  distance_miles: number;
  total_price_cents: number;        // (servicio × tamaño × n vehículos) + addons
  total_duration_minutes: number;
  next_available_slot: string | null; // ISO 8601 UTC, null si no hay disponibilidad hoy
  available_slots: TimeSlotRead[];    // próximos 5 slots
  is_asap_available: boolean;         // puede llegar en < 2 h
}[]
```

### Nuevo modelo `Addon`
```typescript
{
  id: string;
  name: string;             // "Clay Bar Treatment"
  description: string | null;
  price_cents: number;      // 3000 = $30.00
  duration_minutes: number;
  is_active: boolean;
}
```

Endpoint: `GET /api/v1/addons` → `Addon[]`

### Cambios en `AppointmentCreate` (Sprint 5)
```json
{
  "detailer_id": "uuid",
  "vehicle_ids": ["uuid1", "uuid2"],    // ← reemplaza vehicle_id
  "service_id": "uuid",
  "addon_ids": ["uuid1", "uuid2"],      // ← nuevo
  "scheduled_time": "2025-06-15T14:00:00Z",  // ← sigue siendo opcional (ASAP)
  "service_address": "...",
  "service_latitude": 41.13,
  "service_longitude": -85.12,
  "client_notes": "..."
}
```

> **Mientras llega Sprint 5:** usar el endpoint actual con `vehicle_id` (singular) y `scheduled_time` obligatorio.

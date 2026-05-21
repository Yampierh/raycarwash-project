# Documentación Técnica — RayCarWash Portal

> **Última actualización**: 21 de mayo de 2026
> **Versión**: 1.3 (client/detailer pages expansion)

---

## 1. Estado Actual del Sistema

### 1.1 Visión General

**Nombre**: RayCarWash Portal  
**Tipo**: Webapp full-stack Next.js 16 (App Router)  
**Puerto por defecto**: 3001  
**Mercado**: Fort Wayne, IN  
**Propósito**: Sitio público de marketing + Webapp progresiva para clientes y detailers

El proyecto `web/portal/` es una webapp completa que cumple tres funciones:
1. **Sitio público de marketing** — Landing pages, SEO, captación de clientes
2. **Webapp progresiva para clientes** — Dashboard, vehículos, booking, perfil
3. **Webapp progresiva para detailers** — Dashboard, jobs, servicios, ganancias

### 1.2 Stack Tecnológico

| Capa | Tecnología |
|------|-------------|
| Framework | Next.js 16 (App Router) |
| UI | React 19 + Tailwind CSS 4 |
| Idioma | TypeScript |
| i18n | next-intl v4 |
| Estado | Zustand v5 + SWR v2 |
| Formularios | React Hook Form + Zod |
| Pago | Stripe Elements (@stripe/react-stripe-js) |
| Auth Social | @react-oauth/google |
| Icons | lucide-react |
| Utilidades | clsx, date-fns |

### 1.3 Estructura de Directorios

```
web/portal/
├── app/                              # Next.js App Router
│   ├── [locale]/                     # Locale-aware routes (en, es)
│   │   ├── (marketing)/              # Landing pages públicas
│   │   │   ├── page.tsx              # Home /
│   │   │   ├── about/page.tsx
│   │   │   ├── contact/page.tsx
│   │   │   ├── detailers/page.tsx
│   │   │   ├── trust/                # Páginas de confianza
│   │   │   │   ├── insurance/page.tsx
│   │   │   │   └── detailers/page.tsx
│   │   │   └── legal/                # Legales
│   │   │       ├── privacy/page.tsx
│   │   │       └── terms/page.tsx
│   │   ├── (auth)/                   # Autenticación
│   │   │   ├── login/page.tsx
│   │   │   ├── signup/
│   │   │   │   ├── page.tsx          # Registro básico
│   │   │   │   └── role/page.tsx     # Selección rol (client/detailer)
│   │   │   └── onboarding/
│   │   │       ├── page.tsx          # Complete profile
│   │   │       └── detailer/page.tsx # Wizard KYC detailer
│   │   ├── (app)/                    # App autenticada
│   │   │   ├── layout.tsx            # AppShell wrapper
│   │   │   ├── dashboard/page.tsx   # Redirector según rol
│   │   │   ├── client/              # Dashboard cliente
│   │   │   │   ├── layout.tsx       # Guard: rol == client
│   │   │   │   ├── home/page.tsx
│   │   │   │   ├── book/page.tsx    # Booking completo
│   │   │   │   ├── vehicles/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   ├── [id]/page.tsx
│   │   │   │   │   └── new/page.tsx
│   │   │   │   ├── appointments/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   └── [id]/page.tsx
│   │   │   │   ├── profile/page.tsx
│   │   │   │   ├── addresses/page.tsx
│   │   │   │   ├── payment-methods/page.tsx
│   │   │   │   ├── favorites/page.tsx
│   │   │   │   └── security/page.tsx
│   │   │   └── detailer/            # Dashboard detailer
│   │   │       ├── layout.tsx       # Guard: rol == detailer
│   │   │       ├── home/page.tsx
│   │   │       ├── jobs/
│   │   │       │   └── [id]/page.tsx
│   │   │       ├── services/page.tsx
│   │   │       ├── profile/page.tsx
│   │   │       ├── earnings/page.tsx
│   │   │       ├── schedule/page.tsx
│   │   │       ├── portfolio/page.tsx
│   │   │       ├── documents/page.tsx
│   │   │       ├── verification/page.tsx
│   │   │       └── reviews/page.tsx
│   │   └── welcome/page.tsx          # Landing post-login
│   ├── robots.ts                     # SEO
│   └── sitemap.ts                    # SEO
│
├── components/
│   ├── auth/
│   │   ├── GoogleButton.tsx          # OAuth Google
│   │   ├── GoogleAuthProvider.tsx    # Context provider
│   │   └── RoleToggle.tsx            # Client/Provider toggle
│   ├── forms/
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Select.tsx
│   │   ├── Checkbox.tsx
│   │   └── FormError.tsx
│   ├── sections/                      # Landing page sections
│   │   ├── Hero.tsx
│   │   ├── HowItWorks.tsx
│   │   ├── Services.tsx
│   │   ├── ForDetailers.tsx
│   │   ├── Testimonials.tsx
│   │   ├── FAQ.tsx
│   │   ├── ContactCTA.tsx
│   │   └── TrustBadges.tsx
│   ├── app/                           # Componentes de la app
│   │   ├── AppShell.tsx              # Sidebar + header
│   │   ├── VehicleForm.tsx           # CRUD vehículos
│   │   ├── CheckoutForm.tsx          # Stripe payment
│   │   ├── PageHeader.tsx
│   │   ├── EmptyState.tsx
│   │   └── AppointmentStatusBadge.tsx
│   ├── Navbar.tsx
│   ├── Footer.tsx
│   └── LanguageSwitcher.tsx
│
├── lib/
│   ├── api/
│   │   ├── auth-client.ts            # /auth/* endpoints
│   │   ├── client.ts                 # /api/v1/* + interceptors
│   │   ├── api-error.ts              # Error handling
│   │   ├── user.ts                   # /auth/me, /auth/update
│   │   ├── users-hub.ts              # /api/v1/users/me (Profile Hub)
│   │   ├── vehicles.ts               # CRUD vehículos
│   │   ├── appointments.ts           # Citas
│   │   ├── catalog.ts                # Servicios y addons
│   │   ├── matching.ts               # Búsqueda detailers
│   │   ├── payments.ts               # Stripe payment intents
│   │   ├── reviews.ts                # Reseñas (no usado aún)
│   │   └── detailer.ts               # Detailer profile
│   ├── auth.ts                       # JWT decode, role extraction
│   ├── auth-flow.ts                  # Post-login redirects
│   ├── store/
│   │   └── auth.ts                   # Zustand auth store
│   └── hooks/
│       ├── useMe.ts
│       ├── useMeHub.ts
│       ├── useVehicles.ts
│       ├── useAppointments.ts
│       ├── useServices.ts
│       ├── useAddons.ts
│       ├── useDetailerMe.ts
│       └── useDetailerServices.ts
│
├── messages/                         # i18n
│   ├── en.json (725 líneas)
│   └── es.json
│
├── i18n/
│   ├── routing.ts                    # next-intl config
│   ├── navigation.ts                  # Link, useRouter, etc.
│   └── request.ts                     # getRequestConfig
│
├── proxy.ts                          # Next 16 middleware rename
├── next.config.ts
├── tsconfig.json
├── package.json
├── .env.example
└── .env.local
```

### 1.4 Rutas Completas del Sistema

| Ruta | Descripción | Auth |
|------|-------------|------|
| `/[locale]/` | Landing page | ❌ |
| `/[locale]/about` | About us | ❌ |
| `/[locale]/contact` | Contacto + CTA | ❌ |
| `/[locale]/detailers` | Become a detailer | ❌ |
| `/[locale]/trust/insurance` | Insurance policy | ❌ |
| `/[locale]/trust/detailers` | How detailers are vetted | ❌ |
| `/[locale]/legal/privacy` | Privacy policy (placeholder) | ❌ |
| `/[locale]/legal/terms` | Terms of Service (placeholder) | ❌ |
| `/[locale]/login` | Login | ❌ |
| `/[locale]/signup` | Registro | ❌ |
| `/[locale]/signup/role` | Elegir rol | ❌ |
| `/[locale]/onboarding` | Completar perfil | ✅ (onboarding_token) |
| `/[locale]/onboarding/detailer` | Wizard KYC | ✅ (onboarding_token) |
| `/[locale]/dashboard` | Redirect según rol | ✅ |
| `/[locale]/client/home` | Dashboard cliente | ✅ (rol: client) |
| `/[locale]/client/book` | **Booking completo** | ✅ |
| `/[locale]/client/vehicles` | Mis vehículos | ✅ |
| `/[locale]/client/vehicles/new` | Agregar vehículo | ✅ |
| `/[locale]/client/vehicles/[id]` | Editar vehículo | ✅ |
| `/[locale]/client/appointments` | Mis citas | ✅ |
| `/[locale]/client/appointments/[id]` | Detalle cita | ✅ |
| `/[locale]/client/profile` | Mi perfil | ✅ |
| `/[locale]/detailer/home` | Dashboard detailer | ✅ (rol: detailer) |
| `/[locale]/detailer/jobs/[id]` | Detalle trabajo | ✅ |
| `/[locale]/detailer/services` | Mis servicios | ✅ |
| `/[locale]/detailer/profile` | Mi perfil | ✅ |
| `/[locale]/detailer/earnings` | Ganancias | ✅ |

### 1.5 Sistema de Autenticación

**Arquitectura de clientes HTTP**:

```typescript
// lib/api/auth-client.ts - Endpoints /auth/*
const authClient = axios.create({ baseURL: `${BASE_URL}/auth` });
authClient.interceptors.request.use((config) => {
  const token = accessToken ?? onboardingToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// lib/api/client.ts - Endpoints /api/v1/*
const apiClient = axios.create({ baseURL: `${BASE_URL}/api/v1` });
apiClient.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});
```

**Store Zustand** (`lib/store/auth.ts`):

```typescript
type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  onboardingToken: string | null;
  roles: string[];
  roleIntent: "client" | "detailer" | null;
  activeRole: "client" | "detailer" | "admin" | null;
  user: AuthUser | null;
  nextStep: "complete_profile" | "detailer_onboarding" | "ready" | null;
  hydrated: boolean;

  setSession: (tokens) => void;
  setRoleIntent: (intent) => void;
  setUser: (user) => void;
  clear: () => void;
  isAuthenticated: () => boolean;
};
```

**Características**:
- Persistido en localStorage (`raycarwash-auth`)
- Rehidratación automática con detección de token expirado
- Interceptors con inyección automática de tokens
- Auto-refresh en 401 con cola de espera para requests concurrentes
- Google OAuth (se oculta si no hay `NEXT_PUBLIC_GOOGLE_CLIENT_ID`)
- JWT decode con soporte multi-rol
- Redirect post-login inteligente según roles + intent

### 1.6 Integración con Backend

**Endpoints consumidos por el frontend marketing**:

| Dominio | Endpoints HTTP | Descripción |
|---------|----------------|-------------|
| Auth | `POST /auth/register` | Registro nuevo usuario |
| Auth | `POST /auth/login` | Login email/password |
| Auth | `POST /auth/google` | OAuth Google (PKCE) |
| Auth | `PUT /auth/complete-profile` | Onboarding (name, phone) |
| Auth | `GET /auth/me` | Usuario actual |
| Auth | `POST /auth/logout` | Logout |
| Auth | `POST /auth/refresh` | Refresh token |
| Users Hub | `GET /api/v1/users/me?include=...` | Profile Hub (ADR-002b) |
| Users Hub | `PATCH /api/v1/users/me` | Actualizar perfil |
| Vehicles | `GET /api/v1/vehicles` | Listar vehículos |
| Vehicles | `POST /api/v1/vehicles` | Crear vehículo |
| Vehicles | `PUT /api/v1/vehicles/{id}` | Actualizar vehículo |
| Vehicles | `DELETE /api/v1/vehicles/{id}` | Eliminar vehículo |
| Vehicles | `GET /api/v1/vehicles/lookup/{vin}` | VIN decode NHTSA |
| Appointments | `GET /api/v1/appointments/mine` | Citas del usuario |
| Appointments | `GET /api/v1/appointments/{id}` | Detalle cita |
| Appointments | `PATCH /api/v1/appointments/{id}` | Actualizar cita |
| Appointments | `POST /api/v1/appointments` | Crear cita |
| Services | `GET /api/v1/services` | Catálogo servicios |
| Addons | `GET /api/v1/addons` | Catálogo addons |
| Matching | `GET /api/v1/matching?lat=&lng=&date=` | Encontrar detailers |
| Payments | `POST /api/v1/payments/create-intent` | Crear PaymentIntent |
| Fares | `POST /api/v1/fares/estimate` | Estimar precio |
| Detailer | `GET /api/v1/detailers/me` | Perfil detailer |
| Detailer | `PATCH /api/v1/detailers/me` | Actualizar perfil |
| Detailer | `GET /api/v1/detailers/me/services` | Servicios del detailer |

### 1.7 Sistema i18n

**Configuración** (`i18n/routing.ts`):

```typescript
export const routing = defineRouting({
  locales: ["en", "es"],
  defaultLocale: "en",
  localePrefix: "always",  // URLs: /en/... y /es/...
});
```

**Mensajes**: 725 keys por idioma en `messages/en.json` y `messages/es.json`

**Namespaces**:
- `meta` — SEO metadata
- `nav`, `hero`, `how`, `services`, `detailers`, `testimonials`, `faq`, `contact`, `footer`
- `roleToggle`, `login`, `signup`, `signupRole`, `onboarding`, `detailerOnboarding`
- `about`, `app`, `clientHome`, `clientVehicles`, `vehicleForm`, `clientAppointments`
- `book`, `checkout`, `clientProfile`, `detailerHome`, `detailerJob`
- `detailerServices`, `detailerProfile`, `detailerEarnings`, `welcome`, `legal`, `notFound`

### 1.8 Renderizado y Performance

| Tipo de página | Renderizado | SEO |
|----------------|-------------|-----|
| Landing pages (`/`, `/about`, etc.) | Server Components (SSR) | ✅ JSON-LD, meta, sitemap |
| Auth (`/login`, `/signup`) | Client Components + SSR hydrate | ❌ (no requerido) |
| Dashboard (`/client/*`, `/detailer/*`) | Client Components (CSR) | ❌ (no requerido) |

**Decisión de diseño**: Las páginas autenticadas son 100% CSR por:
- Dependencia del token de acceso en localStorage
- Interactividad inmediata sin waiting para SSR
- No hay requisito SEO en dashboards autenticados

### 1.9 Estado de la Aplicación

- **Zustand**: Auth store con persistencia localStorage
- **SWR**: Hooks para data fetching en `lib/hooks/`:
  - `useMe()` → GET /auth/me
  - `useMeHub(includes)` → GET /api/v1/users/me?include=...
  - `useVehicles()` → GET /api/v1/vehicles
  - `useAppointments()` → GET /api/v1/appointments/mine
  - `useServices()` → GET /api/v1/services
  - `useAddons()` → GET /api/v1/addons
  - `useDetailerMe()` → GET /api/v1/detailers/me
  - `useDetailerServices()` → GET /api/v1/detailers/me/services

### 1.10 Componentes UI

**Forms** (`components/forms/`):
- `Button` — variants: primary, secondary, ghost, danger | sizes: sm, md, lg
- `Input` — with label, error, type support
- `Select` — options array
- `Checkbox`
- `FormError` — mensajes de error

**Landing** (`components/sections/`):
- `Hero` — CTA principal + trust bullets
- `HowItWorks` — 4 pasos
- `Services` — 3 paquetes + pricing
- `ForDetailers` — beneficios para detailers
- `Testimonials` — reviews
- `FAQ` — accordion
- `ContactCTA` — descarga app
- `TrustBadges` — confianza

**App** (`components/app/`):
- `AppShell` — sidebar + header + mobile drawer
- `VehicleForm` — crear/editar vehículo con VIN lookup
- `CheckoutForm` — Stripe Elements integration
- `PageHeader` — título + breadcrumbs
- `EmptyState` — placeholder when no data
- `AppointmentStatusBadge` — status pills

### 1.11 Variables de Entorno

```env
# API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Admin dashboard (para redirect)
NEXT_PUBLIC_ADMIN_URL=http://localhost:3000

# Base URL para SEO
NEXT_PUBLIC_BASE_URL=http://localhost:3001

# Mobile apps (para redirect post-login)
NEXT_PUBLIC_APPSTORE_URL=https://apps.apple.com/
NEXT_PUBLIC_PLAYSTORE_URL=https://play.google.com/

# Contacto
NEXT_PUBLIC_CONTACT_EMAIL=hello@raycarwash.com

# OAuth Google (opcional — sin él, se oculta el botón)
NEXT_PUBLIC_GOOGLE_CLIENT_ID=

# Stripe (requerido para pagos)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=
```

### 1.12 Flujo de Booking Completo

El booking está **100% implementado** en `/client/book`:

1. **Step 0**: Seleccionar servicio + vehículos + add-ons
2. **Step 1**: Fecha + Dirección (geolocalización automática del navegador con fallback a Fort Wayne)
3. **Step 2**: Matching → selección de detailer + time slot
4. **Step 3**: Confirmar → crear cita → crear PaymentIntent → Stripe checkout

**Características**:
- Multi-vehículo por cita
- Add-ons opcionales
- Geolocalización con fallback
- Manejo de conflictos de slot (409) con auto-refresh manteniendo detailer seleccionado
- Patrón escrow: authorize now, capture later

---

## 2. Problemas Detectados y Arreglos Inmediatos (P0/P1)

### 2.1 P0 — Sistema de Notificaciones Globales
| Aspecto | Detalle |
|---------|---------|
| **Síntoma** | No hay feedback toast para acciones exitosas. |
| **Causa raíz** | No existe sistema de toast/snackbar implementado. |
| **Impacto** | Usuarios no saben si sus acciones se completaron, afectando la percepción de la "presentación" y la confianza. |
| **Solución** | Instalar `sonner`, crear `ToastProvider`, crear hook `useToast()`. |
| **Archivos** | `app/[locale]/layout.tsx`, `lib/toast.ts` (nuevo). |
| **Esfuerzo** | M (1-2 días). |

### 2.2 P0 — Error Boundary y Manejo de Errores
| Aspecto | Detalle |
|---------|---------|
| **Síntoma** | 401 hace logout automático sin explicación al usuario. |
| **Causa raíz** | No hay Error Boundary global, interceptores aislados. |
| **Impacto** | Confusión, abandono de flujos. La falta de un manejo de errores elegante impacta la "presentación" de la robustez. |
| **Solución** | Crear `app/error.tsx`, personalizar interceptor para toast + redirect. |
| **Archivos** | `app/[locale]/error.tsx`, `lib/api/client.ts`. |
| **Esfuerzo** | S (0.5-1 día). |

### 2.3 P0 — Legal Pages con Contenido de Ejemplo
| Aspecto | Detalle |
|---------|---------|
| **Síntoma** | `/legal/privacy` y `/legal/terms` tienen "This is a placeholder..." |
| **Causa raíz** | Nunca se reemplazaron con políticas reales. |
| **Impacto** | Riesgo legal, no cumple con regulaciones. La "presentación" de un sitio profesional y digno de confianza se ve comprometida. |
| **Solución** | Contratar legales para redactar políticas reales. |
| **Archivos** | `messages/en.json` (líneas 708-718), páginas legales. |
| **Esfuerzo** | L (2-3 semanas, requiere trabajo legal). |

### 2.4 P1 — Dashboards sin Suspense
| Aspecto | Detalle |
|---------|---------|
| **Síntoma** | Primera paint vacía, luego aparece contenido. |
| **Causa raíz** | No hay `<Suspense>` boundaries alrededor de hooks SWR. |
| **Impacto** | Percepción de lentitud. La "presentación" sufre una UX pobre. |
| **Solución** | Envolver componentes de datos con `<Suspense fallback={<Skeleton/>}>` para mejorar la percepción de velocidad y reactividad. |
| **Archivos** | Todas las páginas de dashboard. |
| **Esfuerzo** | M (2-3 días). |

### 2.5 P1 — Google OAuth sin Credenciales en Desarrollo
| Aspecto | Detalle |
|---------|---------|
| **Síntoma** | Botón de Google se oculta si no hay `GOOGLE_CLIENT_ID`. |
| **Causa raíz** | No hay documentación para developers. |
| **Impacto** | Fricción en onboarding para nuevos devs. |
| **Solución** | Añadir link a docs de Google Cloud en `.env.example`. |
| **Archivos** | `.env.example`, `README.md`. |
| **Esfuerzo** | S (30 minutos). |

### 2.6 P1 — APIs Defined but Not Integrated
| Aspecto | Detalle |
|---------|---------|
| **Síntoma** | `lib/api/reviews.ts` existe pero no se usa. |
| **Causa raíz** | No era scope del MVP. |
| **Impacto** | Sin historial de reseñas visible para clientes o detailers. |
| **Solución** | Crear vista de historial de reseñas, integrar en Profile Hub. |
| **Archivos** | `lib/api/reviews.ts`, páginas de dashboard. |
| **Esfuerzo** | M (3-5 días). |

---

## 3. Roadmap de Funcionalidades por Rol

### 3.1 Cliente Avanzado

| Funcionalidad | Descripción | Complejidad | Fase |
|---------------|-------------|-------------|------|
| Historial completo de servicios | Vista atractiva con filtros, búsqueda y exportación (PDF/CSV para impuestos o contabilidad personal). | M | 1 |
| Gráficos de gastos | Gasto mensual/anual por vehículo, desglose de ingresos por servicio/tipo de vehículo. (Recomendado: `recharts`). | M | 1 |
| Garage virtual con fotos | Upload múltiple de fotos (antes/después, daños específicos), notas para cada vehículo (historial de salud del vehículo). | M | 2 |
| Booking recurrente | Suscripciones (ej. semanal, bimensual, mensual) con descuentos por planes de mantenimiento y una presentación clara de los beneficios. | L | 2 |
| Booking multi-vehículo | Flota familiar/empresarial. | M | 2 |
| Gestión de flotas B2B | Interfaz para gestionar múltiples vehículos, ubicaciones, asignación de servicios y facturas consolidadas. | L | 3 |

### 3.2 Detailer Profesional

| Funcionalidad | Descripción | Complejidad | Fase |
|---------------|-------------|-------------|------|
| Panel financiero | Ingresos, gastos, ganancias, proyecciones. Desglose por servicio/vehículo/cliente, registro de gastos (consumibles, gasolina), gráficos de tendencias. (Recomendado: `recharts`). | M | 2 |
| Chat con clientes | Mensajería integrada (`socket.io-client`) para comunicación eficiente y resolución de dudas, manteniendo la información en la plataforma. | L | 2 |
| Portfolio público | Galería de trabajos (fotos antes/después). Vinculado con sistema de reseñas para construir confianza. | M | 2 |
| CRM de clientes | Vista por cliente con historial de servicios, vehículos atendidos, preferencias, notas del detailer. Recordatorios automáticos de seguimiento. | M | 3 |
| Precios dinámicos | Surge pricing controlado. | L | 3 |

### 3.3 Experiencia Compartida

| Funcionalidad | Descripción | Complejidad | Fase |
|---------------|-------------|-------------|------|
| Notificaciones push web | Service Workers (`vite-plugin-pwa`) para notificaciones en el navegador (citas, ofertas, mensajes de chat). | M | 2 |
| Gamificación | Badges, leaderboards para motivar a detailers ("Top Detailer") o clientes ("Cliente Premium"). | S | 3 |
| Modo oscuro | Dark mode completo para una UX moderna. | S | 1 |

---

## 4. Estrategias de Contenido y SEO

Para impulsar el crecimiento en el mercado local de Fort Wayne, IN:

-   **Optimización de Imágenes:** Asegurar el uso de `next/image` para optimización automática (lazy loading, redimensionamiento, formatos modernos como WebP). Esto es crítico para el rendimiento del sitio y el SEO.
-   **Contenido Localizado SEO:** Crear más contenido SEO específico para Fort Wayne, IN (ej. blogs sobre "mejores sitios de lavado de coches en Fort Wayne", "preparar tu coche para el invierno en Indiana", "por qué contratar un detailer móvil en Fort Wayne").
-   **Testimonios y Casos de Éxito:** Ampliar la sección de testimonios. Incluir fotos (con permiso) y detalles (ej. "Cliente en el centro de Fort Wayne") para construir prueba social.
-   **Configuración SEO (profunda):** Verificar que todas las páginas tengan meta títulos, descripciones y datos estructurados (JSON-LD) precisos. Implementar correctamente las etiquetas `hreflang` para `next-intl` para evitar duplicidad de contenido y mejorar el SEO internacional.
-   **Páginas de Servicios Detalladas:** Cada servicio (lavado exterior, interior, pulido, etc.) debe tener su propia página detallada con beneficios, precios, duración estimada y un CTA claro para reservar.
-   **Preguntas Frecuentes (FAQ) Dinámicas:** Expandir la sección de FAQ con preguntas reales de clientes y detailers, usando un formato de acordeón y, si es posible, con funcionalidad de búsqueda.
-   **Comparativas (Ej. vs. Lavaderos Tradicionales):** Contenido que explique claramente los beneficios de RayCarWash frente a las opciones tradicionales.
-   **Auditoría de Rendimiento en CI:** Integrar Lighthouse CI en el pipeline de CI/CD para detectar automáticamente regresiones de rendimiento, crucial para la experiencia de usuario y el SEO.
-   **Accessibility Linting:** Añadir un linter de accesibilidad (ej. `eslint-plugin-jsx-a11y`) a la configuración de ESLint para capturar problemas comunes durante el desarrollo.
-   **Third-Party Script Loading Optimization:** Optimizar la carga de scripts externos (ej. `@stripe/stripe-react-js`, `@react-oauth/google`) utilizando `next/script` con estrategias como `lazyOnload` o `afterInteractive` para evitar el bloqueo del hilo principal.
-   **Pre-rendering para Contenido Crítico:** Para el contenido de marketing crítico para el SEO, priorizar el renderizado estático o del lado del servidor (`getStaticProps`, `getServerSideProps`) sobre la obtención de datos del lado del cliente.

---

## 5. Presentación y Engagement (Aspectos Visuales y de Interacción)

La "presentación" es clave para la primera impresión y la retención:

-   **Animaciones y Transiciones Sutiles:** Utilizar microinteracciones fluidas en elementos de la UI (botones, navegación, carga de contenido una vez implementado Suspense) para una experiencia más moderna y pulida.
-   **Ilustraciones/Imágenes de Alta Calidad:** Invertir en imágenes profesionales de coches limpios, detailers trabajando y clientes satisfechos. Evitar fotos de stock genéricas para transmitir autenticidad.
-   **Video Demo (Hero Section):** Un video corto en la sección "Hero" mostrando el proceso de "RayCarWash en acción" (detailer llegando, trabajando, coche brillante) sería muy impactante y comunicaría el valor rápidamente.
-   **Calculadora de Precios Instantánea:** En la landing page, una herramienta interactiva que permita al usuario introducir rápidamente el tipo de coche y el servicio deseado para obtener un "precio estimado" al instante. Esto reduce la fricción en el proceso de decisión.
-   **Chatbot de Soporte:** Implementar un chatbot para responder preguntas frecuentes, con la opción de escalar a un agente humano en horarios definidos para consultas más complejas.

---

## 6. Arquitectura Técnica para Funcionalidades Futuras

### 6.1 Nuevas Dependencias Recomendadas

| Librería | Propósito |
|----------|-----------|
| `sonner` | Toasts/notificaciones |
| `recharts` | Gráficos y visualizaciones (para dashboards de gastos/ganancias) |
| `sheetjs` / `xlsx` | Export CSV/Excel (para historial financiero/servicios) |
| `jspdf` | Export PDF (para historial financiero/servicios) |
| `socket.io-client` | WebSocket client (para chat) |
| `vite-plugin-pwa` | Service Workers + PWA (para notificaciones push web) |
| `eslint-plugin-jsx-a11y` | Linting de accesibilidad |

### 6.2 Nuevos Endpoints de Backend Requeridos

**Suscripciones**:
- `POST/GET/PATCH/DELETE /api/v1/subscriptions`
- Worker: `subscription_scheduler`

**Chat**:
- `GET/POST /api/v1/conversations`
- WebSocket: `/ws/chat`

**Reseñas**:
- `POST /api/v1/appointments/{id}/reviews`
- `GET /api/v1/providers/{id}/reviews`

**Detailer financiero**:
- `GET /api/v1/detailers/me/earnings`
- `GET/POST /api/v1/detailers/me/expenses`

### 6.3 Infraestructura Adicional

- **Storage**: S3 bucket para fotos de vehículos, portfolio, before/after
- **WebSocket Server**: Chat, location sharing, notifications, timeline
- **Workers**: Subscription scheduler, notification sender, badge evaluator

---

## 7. Métricas de Éxito

### 7.1 Cliente

| Métrica | Target |
|---------|--------|
| Landing → Registro | >15% |
| Onboarding completion | >70% |
| Booking rate (30 días) | >25% |
| Repeat booking (30 días) | >40% |
| NPS | >50 |

### 7.2 Detailer

| Métrica | Target |
|---------|--------|
| Job acceptance rate | >80% |
| Monthly earnings avg | >$2,500 |
| 90-day retention | >75% |
| Average rating | >4.5 |

### 7.3 Plataforma

| Métrica | Target |
|---------|--------|
| GMV monthly | Growing MoM |
| Matching success rate | >85% |
| Payment success rate | >99% |

---

## 8. Diferencias Clave vs Frontend Móvil

| Aspecto | Marketing (Web) | Frontend Móvil (React Native) |
|---------|-----------------|------------------------------|
| Plataforma | Web (Next.js 16) | Mobile (Expo) |
| Booking | ✅ Completo | ✅ Completo |
| Auth | Web (Google PKCE) | Mobile (secure-store) |
| Pagos | Stripe Elements | Stripe Mobile SDK |
| Push notifications | ✅ Web Push (PWA) | ✅ Expo Push |
| GPS/Location | Browser geolocation | Native location |

---

## 9. Notas Técnicas Importantes

### 9.1 Patrones de Implementación

-   **Layouts anidados**: Root → Locale → (marketing|auth|app) → Page
-   **Route Groups**: `(marketing)`, `(auth)`, `(app)` sin afectar URL
-   **Auth Guards**: Client/detailer layouts verifican `activeRole` y redirect
-   **Redirect logic**: `/dashboard` determina destino según rol

### 9.2 Profile Hub

Implementado en `lib/api/users-hub.ts` siguiendo ADR-002b:

**Includes disponibles**: `profile`, `stats`, `preferences`, `notifications`, `vehicles`, `addresses`, `payment_methods`, `favorites`, `provider`, `security`, `sessions`

```typescript
const { data, meta } = await getHub(['profile', 'stats']);
```

### 9.3 Patrones de Código para Contribuidores

```typescript
// Página autenticada
"use client";
import { useAuthStore } from "@/lib/store/auth";

// Data fetching
import { useVehicles } from "@/lib/hooks/useVehicles";

// Formularios
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
```

---

## 10. Pendientes / Tech Debt

-   [ ] **P0 - Sistema de notificaciones globales (toasts):** Implementar feedback visual para acciones exitosas.
-   [ ] **P0 - Error Boundary global:** Manejo robusto de errores inesperados y mensajes claros al usuario.
-   [ ] **P0 - Legal pages con contenido real:** Reemplazar placeholders con políticas de privacidad y términos de servicio redactadas legalmente.
-   [ ] **P1 - Dashboards sin Suspense:** Implementar `<Suspense>` boundaries con esqueletos de carga para mejorar la percepción de rendimiento en dashboards.
-   [ ] **P1 - Integración de reseñas en dashboard:** Crear vistas para mostrar y gestionar reseñas.
-   [ ] **P1 - Documentación de Google OAuth para dev:** Añadir guía para configurar `GOOGLE_CLIENT_ID` en desarrollo.
-   [ ] **Roadmap Cliente - Historial completo de servicios:** Desarrollar filtros, búsqueda y opción de exportación (PDF/CSV).
-   [ ] **Roadmap Cliente - Gráficos de gastos:** Implementar visualizaciones de gasto mensual/anual por vehículo.
-   [ ] **Roadmap Cliente - Garage virtual con fotos:** Permitir subir fotos y añadir notas a los vehículos.
-   [ ] **Roadmap Cliente - Booking recurrente:** Implementar lógica y UI para servicios programados regularmente.
-   [ ] **Roadmap Cliente - Gestión de flotas B2B:** Desarrollar interfaz para clientes con múltiples vehículos/ubicaciones.
-   [ ] **Roadmap Detailer - Panel financiero:** Construir un dashboard detallado de ingresos, gastos y ganancias.
-   [ ] **Roadmap Detailer - Chat con clientes:** Integrar un sistema de mensajería directa.
-   [ ] **Roadmap Detailer - Portfolio público:** Permitir a los detailers mostrar sus trabajos.
-   [ ] **Roadmap Detailer - CRM de clientes:** Desarrollar funcionalidades básicas de gestión de clientes.
-   [ ] **Roadmap Experiencia Compartida - Notificaciones push web:** Implementar notificaciones push en el navegador.
-   [ ] **Roadmap Experiencia Compartida - Gamificación:** Integrar elementos de juego (badges, leaderboards).
-   [ ] **Roadmap Experiencia Compartida - Modo oscuro:** Desarrollar una versión de la UI con tema oscuro.
-   [ ] **SEO - Optimización de Imágenes:** Asegurar uso de `next/image` y formatos eficientes.
-   [ ] **SEO - Contenido Localizado:** Crear artículos y guías específicas para Fort Wayne, IN.
-   [ ] **SEO - Configuración Profunda:** Revisar y optimizar meta-tags, JSON-LD, `hreflang`.
-   [ ] **SEO - Páginas de Servicios Detalladas:** Crear páginas individuales para cada servicio.
-   [ ] **SEO - Preguntas Frecuentes (FAQ) Dinámicas:** Expandir y mejorar la sección FAQ.
-   [ ] **SEO - Comparativas:** Crear contenido que diferencie a RayCarWash de la competencia.
-   [ ] **Performance - Auditoría en CI:** Integrar Lighthouse CI en el pipeline.
-   [ ] **Calidad - Accessibility Linting:** Añadir `eslint-plugin-jsx-a11y` al CI/CD.
-   [ ] **Performance - Carga de Scripts de Terceros:** Optimizar la carga de scripts de Stripe y Google.
-   [ ] **Performance - Pre-rendering de Contenido Crítico:** Priorizar SSR/SSG para contenido estático importante.
-   [ ] **Presentación - Animaciones y Transiciones Sutiles:** Añadir microinteracciones.
-   [ ] **Presentación - Imágenes de Alta Calidad:** Invertir en fotografía profesional.
-   [ ] **Presentación - Video Demo (Hero Section):** Integrar un video corto explicativo.
-   [ ] **Presentación - Calculadora de Precios Instantánea:** Añadir herramienta interactiva en la landing.
-   [ ] **Presentación - Chatbot de Soporte:** Implementar un chatbot para FAQs.

---

*Documento mantenido por el equipo de desarrollo RayCarWash*
*Para actualizar: editar directamente este archivo tras cambios significativos*

# RAYCARWASH App 🚗✨

**RAYCARWASH** es una plataforma móvil de servicios de detailing a domicilio que conecta a clientes con detailers profesionales. Construida con un enfoque en la escalabilidad, permite la gestión de múltiples vehículos, seguimiento de citas en tiempo real y una experiencia de usuario fluida basada en roles.

> Premium on-demand mobile detailing platform for Fort Wayne, IN.

---

## Status

| Layer | Status |
|-------|--------|
| Frontend (React Native / Expo) | ✅ Complete — Sprint 5 |
| Backend (FastAPI / Python) | 🔴 Pending implementation |

---

## 🛠️ Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | React Native + Expo | 0.81.5 / ~54.0.33 |
| Navigation | React Navigation (stack + bottom tabs) | ^7.x |
| HTTP Client | Axios with auto-refresh interceptors | ^1.13.6 |
| Authentication | Email/password · Google OAuth · Apple Sign-In | — |
| Token Storage | expo-secure-store | ~15.0.8 |
| Location | expo-location + Open-Meteo (weather) | ~19.0.8 |
| Calendar | react-native-calendars | ^1.1314.0 |
| Icons | @expo/vector-icons (Ionicons + MaterialCommunityIcons) | ^15.0.3 |
| Type Safety | TypeScript strict mode | 5.9.2 |

---

## 🚀 Características Principales

### Para Clientes 👤

- **Gestión de Flota:** Agrega y administra múltiples vehículos con decodificación automática de VIN.
- **Flujo de Reserva en 4 Pasos:**
  1. **Selección:** Elige uno o varios vehículos de tu garaje.
  2. **Servicios:** Configura servicios base y add-ons por cada vehículo.
  3. **Agenda:** Selección de fecha o modo "ASAP" (lo antes posible).
  4. **Detailer:** Matching inteligente basado en ubicación, precio estimado y disponibilidad.
- **Fidelización:** Sistema de niveles (Bronze a Platinum) basado en el historial de servicios.

### Para Detailers 🛠️

- **Onboarding Profesional:** Configuración de bio, especialidades y radio de servicio.
- **Gestión de Operaciones:** Panel con ganancias totales, estados de citas (Pending, Confirmed, In Progress) y cronómetro en vivo para trabajos activos.
- **Catálogo Personalizado:** Control total sobre qué servicios ofrecer y la posibilidad de sobreescribir precios base.

---

## User Roles

| Role | Description |
|------|-------------|
| **Client** | Books detailing services for one or more vehicles |
| **Detailer** | Receives bookings, manages jobs and pricing |

---

## 📂 Project Structure

```
RAYCARWASH-app/
├── app.json                    Expo config (bundle ID, plugins, permissions)
├── src/
│   ├── config/
│   │   ├── app.config.ts       Central config: API URL, emails, fallback coords
│   │   └── oauth.ts            Google OAuth client IDs
│   ├── hooks/
│   │   ├── useAppNavigation.ts Typed navigation hook
│   │   ├── useLocation.ts      GPS + reverse geocoding
│   │   └── useWeather.ts       Open-Meteo weather fetch
│   ├── navigation/
│   │   ├── AppNavigator.tsx    Root stack + client + detailer tab navigators
│   │   ├── navigationRef.ts    Imperative navigation ref
│   │   └── types.ts            RootStackParamList, UserRole enum
│   ├── screens/                17 screens (see table below)
│   ├── services/               8 API service modules
│   ├── theme/
│   │   └── colors.ts           Colors.background, .card, .primary, .text
│   └── utils/
│       ├── auth-redirect.ts    navigateAfterAuth() — role-based post-login routing
│       ├── formatters.ts       STATUS_COLORS, getInitials, formatPrice, getCountdown…
│       ├── pricing.ts          getServicePrice() — vehicle size → price tier
│       └── storage.ts          saveToken / getToken / clearAuthTokens
```

---

## Screens

### Both Roles
| Screen | Purpose |
|--------|---------|
| `LoginScreen` | Email/password + Google + Apple Sign-In |
| `RegisterScreen` | Registration with Client / Professional role toggle |

### Client Flow
| Screen | Purpose |
|--------|---------|
| `HomeScreen` | Dashboard: greeting, weather card, fleet carousel, upcoming appointments |
| `VehiclesScreen` | Vehicle fleet list — view, book, or manage each vehicle |
| `ProfileScreen` | Account info, member tier, stats, settings |
| `EditProfileScreen` | Edit name, phone, service address |
| `AddVehicleScreen` | Register vehicle — manual entry or VIN auto-decode |
| `VehicleDetailScreen` | Edit / delete a vehicle |
| `SelectVehiclesScreen` | Booking Step 1 — select vehicles to detail |
| `BookingScreen` | Booking Step 2 — pick service + add-ons per vehicle |
| `ScheduleScreen` | Booking Step 3 — pick a date or ASAP mode |
| `DetailerSelectionScreen` | Booking Step 4 — smart-matched detailers + time slot picker |
| `BookingSummaryScreen` | Review total, confirm, create appointment |

### Detailer Flow
| Screen | Purpose |
|--------|---------|
| `DetailerHomeScreen` | Operations: live jobs, elapsed timer, status transitions, earnings |
| `DetailerOnboardingScreen` | First-time setup: bio, experience, radius, specialties |
| `DetailerProfileScreen` | Business dashboard: stats, accepting-bookings toggle, service links |
| `DetailerServicesScreen` | Activate services + set custom prices |

---

## Navigation Map

```
Login ──► Register
  │
  ▼  navigateAfterAuth() checks role via GET /auth/me
  │
  ├── Main  [Client Tabs]
  │     ├── Home
  │     ├── Vehicles
  │     └── Profile
  │
  │   Shared modals (accessible from any client screen):
  │     AddVehicle · VehicleDetail · EditProfile
  │
  │   Booking flow (4 steps):
  │     SelectVehicles → Booking → Schedule
  │     → DetailerSelection → BookingSummary
  │
  └── DetailerMain  [Detailer Tabs]
        ├── DetailerHome  (Operations)
        └── DetailerProfile
              └── DetailerServices  (modal)

  DetailerOnboarding  (one-time, on first detailer login when no profile exists)
```

**Appointment status flow**

```
pending ──► confirmed ──► in_progress ──► completed
   │             │
   └─────────────┴──────► cancelled_by_client / cancelled_by_detailer
```

**Member tiers** (based on completed appointments count)

| Tier | Min Jobs | Badge Color |
|------|---------|------------|
| Bronze | 0 | `#B45309` |
| Silver | 3 | `#94A3B8` |
| Gold | 8 | `#F59E0B` |
| Platinum | 15 | `#E2E8F0` |

---

## ⚙️ Setup

### Prerequisites
- Node ≥ 18 · npm ≥ 9
- `npm install -g expo-cli`
- iOS Simulator (Xcode) or Android Emulator (Android Studio)

### Install
```bash
git clone https://github.com/Yampierh/RAYCARWASH-app.git
cd RAYCARWASH-app
npm install
```

### Configure

**API server** — `src/config/app.config.ts`:
```ts
export const APP_CONFIG = {
  apiBaseUrl: "http://<your-server-ip>:8000",  // ← change this
  supportEmail: "support@raycarwash.com",
  // ...
};
```

**Google OAuth** (optional) — `src/config/oauth.ts`:
```ts
export const GOOGLE_CLIENT_IDS = {
  web:     "YOUR_WEB_CLIENT_ID",
  ios:     "YOUR_IOS_CLIENT_ID",
  android: "YOUR_ANDROID_CLIENT_ID",
};
```

### Run
```bash
npx expo start          # Expo Go — scan QR with phone
npx expo run:ios        # iOS simulator
npx expo run:android    # Android emulator
```

---

## 🔐 Autenticación y Seguridad

La app utiliza `expo-secure-store` para manejar tokens de acceso y de refresco de forma segura. Soporta login tradicional, Google OAuth y Apple Sign-In. Los interceptores de Axios manejan errores 401 y re-encolan peticiones pendientes durante el refresco de token.

---

## 📈 Lógica de Precios

El sistema calcula los precios dinámicamente según el tamaño del vehículo registrado (`small`, `medium`, `large`, `xl`), mapeando el `body_class` del vehículo con los tiers de precio de cada servicio.

---

## API Reference

**Base URLs**
```
Auth:   {apiBaseUrl}/auth/
API v1: {apiBaseUrl}/api/v1/
```

All protected endpoints require `Authorization: Bearer <access_token>`.

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| POST | `/auth/token` | — | Login (`x-www-form-urlencoded`: `username`, `password`) |
| POST | `/auth/refresh?refresh_token=…` | — | Refresh access token |
| GET | `/auth/me` | ✓ | Current user profile |
| PUT | `/auth/update` | ✓ | Update `full_name`, `phone_number`, `service_address` |
| POST | `/auth/google` | — | Google OAuth exchange `{ access_token }` |
| POST | `/auth/apple` | — | Apple Sign-In `{ identity_token, full_name? }` |
| POST | `/auth/password-reset` | — | Request password reset email `{ email }` |

### Users

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| POST | `/api/v1/users` | — | Register `{ full_name, email, password, phone_number?, role }` |

### Vehicles

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| GET | `/api/v1/vehicles` | ✓ | All vehicles for current user |
| POST | `/api/v1/vehicles` | ✓ | Add vehicle |
| PUT | `/api/v1/vehicles/{id}` | ✓ | Update vehicle |
| DELETE | `/api/v1/vehicles/{id}` | ✓ | Delete vehicle |
| GET | `/api/v1/vehicles/lookup/{vin}` | ✓ | VIN decode → make, model, year, body_class |

### Services & Add-ons

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| GET | `/api/v1/services` | — | Catalog with `price_small/medium/large/xl` and `duration_minutes` |
| GET | `/api/v1/addons` | — | Add-ons catalog with `price_cents` |

### Detailers (Public)

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| GET | `/api/v1/detailers` | — | List with geo filters: `lat`, `lng`, `radius_miles`, `min_rating` |
| GET | `/api/v1/detailers/{id}/availability` | — | Time slots for `request_date`, `service_id?`, `vehicle_size?` |
| GET | `/api/v1/matching` | — | Smart match: `lat`, `lng`, `date`, `service_id`, `vehicle_sizes`, `addon_ids` → `MatchedDetailer[]` |

### Detailer Profile (Private)

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| GET | `/api/v1/detailers/me` | ✓ Detailer | Own profile with `total_earnings_cents`, `total_services`, `specialties[]` |
| PUT | `/api/v1/detailers/me` | ✓ Detailer | Upsert profile — `bio`, `years_of_experience`, `service_radius_miles`, `specialties` |
| PATCH | `/api/v1/detailers/me/status` | ✓ Detailer | Toggle visibility `{ is_accepting_bookings: bool }` |
| GET | `/api/v1/detailers/me/services` | ✓ Detailer | Catalog with detailer's `is_active` + `custom_price_cents` per service |
| PATCH | `/api/v1/detailers/me/services/{id}` | ✓ Detailer | Toggle service on/off + set custom price |

### Appointments

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| POST | `/api/v1/appointments` | ✓ Client | Create multi-vehicle appointment |
| GET | `/api/v1/appointments/mine` | ✓ Both | Paginated — client bookings or detailer jobs per JWT role |
| GET | `/api/v1/appointments/{id}` | ✓ Both | Single appointment with nested `client`, `vehicles`, `detailer` |
| PATCH | `/api/v1/appointments/{id}/status` | ✓ Both | Update status — `actual_price` required when `completed` |

**Multi-vehicle appointment payload:**
```json
{
  "detailer_id": "uuid",
  "scheduled_time": "ISO 8601 UTC",
  "service_address": "123 Main St, Fort Wayne, IN",
  "service_latitude": 41.1306,
  "service_longitude": -85.1289,
  "vehicles": [
    { "vehicle_id": "uuid", "service_id": "uuid", "addon_ids": ["uuid"] }
  ],
  "client_notes": "optional"
}
```

---

## Configuration Reference

| Key | File | Default | Purpose |
|-----|------|---------|---------|
| `apiBaseUrl` | `src/config/app.config.ts` | `http://192.168.0.10:8000` | Backend server |
| `supportEmail` | `src/config/app.config.ts` | `support@raycarwash.com` | Shown in Help / Support |
| `privacyUrl` | `src/config/app.config.ts` | `https://raycarwash.com/privacy` | Privacy Policy link |
| `termsUrl` | `src/config/app.config.ts` | `https://raycarwash.com/terms` | Terms of Service link |
| `appStoreUrl` | `src/config/app.config.ts` | `""` | iOS App Store deep link |
| `playStoreUrl` | `src/config/app.config.ts` | `""` | Google Play Store deep link |
| `fallbackCoords` | `src/config/app.config.ts` | Fort Wayne, IN (41.1306 / -85.1289) | Used when GPS is denied |
| `GOOGLE_CLIENT_IDS` | `src/config/oauth.ts` | `""` (all three) | Google OAuth (web, iOS, Android) |

---

## Service Modules

| File | Key Exports |
|------|------------|
| `services/auth.service.ts` | `loginWithBackend`, `registerUser`, `refreshAccessToken`, `loginWithGoogle`, `loginWithApple`, `requestPasswordReset`, `logout` |
| `services/user.service.ts` | `getUserProfile`, `updateUserProfile` |
| `services/vehicle.service.ts` | `getMyVehicles`, `addVehicle`, `decodeVehicleVin`, `updateVehicle`, `deleteVehicle` |
| `services/service.service.ts` | `getServices` |
| `services/addon.service.ts` | `getAddons` |
| `services/appointment.service.ts` | `createAppointment`, `getMyAppointments`, `getAppointmentById`, `patchAppointmentStatus` |
| `services/detailer.service.ts` | `getDetailers`, `getDetailerAvailability`, `getMatching` |
| `services/detailer-private.service.ts` | `getMyDetailerProfile`, `upsertDetailerProfile`, `toggleAcceptingBookings`, `getMyDetailerServices`, `updateDetailerService` |

---

## Roadmap

### 🔴 P1 — Backend (nothing works without this)

| Task | Details |
|------|---------|
| Auth + users | `POST /token`, `/refresh`, `/users`, `GET /auth/me`, `PUT /auth/update` |
| Vehicles CRUD | Full CRUD + VIN decode (NHTSA API or similar) |
| Services + add-ons catalog | Static catalog seeded in DB; price tiers per vehicle size |
| Detailer private profile | `GET/PUT /detailers/me`, status toggle, services management |
| Smart matching engine | Filter by radius + date + service + vehicle sizes → precompute price + available 30-min slots |
| Appointments | Multi-vehicle creation, paginated `mine`, full status transitions with `actual_price` on complete |

### 🟠 P2 — Production Hardening

| Task | File | Details |
|------|------|---------|
| Wire support / privacy / terms links | `ProfileScreen`, `DetailerProfileScreen` | `Linking.openURL(APP_CONFIG.privacyUrl)` — currently empty `onPress` |
| Change password screen | New `ChangePasswordScreen` | `POST /auth/change-password` — currently routes to support email |
| Push notifications | New `useNotifications` hook | `expo-notifications`: alert detailer on new booking, client on status change |
| Stripe payments | `BookingSummaryScreen` | Authorize card on booking; capture on completion |
| App Store / Play Store rating | `ProfileScreen` | Wire `Linking.openURL(APP_CONFIG.appStoreUrl)` once URLs are set |

### 🟡 P3 — Feature Completeness

| Task | Details |
|------|---------|
| Appointments history screen | Register `Appointments` route — the "History" quick-action in `HomeScreen` targets an unregistered route |
| Real promotional offers | `GET /api/v1/promotions` — replace hardcoded "Summer Shine Special" in `HomeScreen` |
| Reviews system | `POST /api/v1/appointments/{id}/review` after `status = completed` |
| Detailer portfolio | `expo-image-picker` + S3 / Cloudinary for before/after photos |
| Real-time job alerts | WebSocket or polling for detailer incoming bookings |
| Google OAuth credentials | Fill `GOOGLE_CLIENT_IDS` in `src/config/oauth.ts` |

### 🟢 P4 — Polish

| Task | Details |
|------|---------|
| Splash screen asset | Replace placeholder in `app.json` |
| App Store submission | Bundle ID `com.raycarwash.app` — need assets, screenshots, metadata |
| React error boundaries | Wrap root navigator |
| Accessibility labels | `accessibilityLabel` on all interactive elements |
| i18n / Spanish | Significant Hispanic market in Fort Wayne |

---

## Known Gaps in Current Code

| Location | Gap | Planned Fix |
|----------|-----|-------------|
| `ProfileScreen.tsx:274` | Payment Methods → "coming soon" alert | Stripe integration |
| `ProfileScreen.tsx:291` | Notifications → "coming soon" alert | `expo-notifications` |
| `ProfileScreen.tsx:307` | Change Password → routes to support email | New screen + `POST /auth/change-password` |
| `ProfileScreen.tsx:335` | Rate the App → "coming soon" alert | `Linking.openURL(APP_CONFIG.appStoreUrl)` |
| `DetailerProfileScreen.tsx` | Contact Support / Terms / Privacy → empty `onPress` | `Linking.openURL` wired to `APP_CONFIG` |
| `HomeScreen.tsx` | "Summer Shine Special" — hardcoded offer | `GET /api/v1/promotions` |
| `AppNavigator.tsx` | "History" quick-action targets unregistered `Appointments` route | Add `AppointmentsScreen` + register route |

---

## License

Private — © 2026 RAY Car Wash. All rights reserved.

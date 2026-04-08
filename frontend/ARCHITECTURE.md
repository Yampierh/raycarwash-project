# RAYCARWASH App - Complete Codebase Documentation

## 1. ROOT CONFIGURATION FILES

### package.json

**Location:** `/home/user/RAYCARWASH-app/package.json`

- **Name:** raycarwash-app
- **Version:** 1.0.0
- **Main:** index.js
- **Scripts:**
  - `start`: expo start
  - `reset-project`: node ./scripts/reset-project.js
  - `android`: expo start --android
  - `ios`: expo start --ios
  - `web`: expo start --web
  - `lint`: expo lint
    **Key Dependencies:**
- React Navigation (bottom-tabs, native-stack)
- Expo ecosystem (location, auth, camera, secure storage, etc.)
- React 19.1.0 & React Native 0.81.5
- react-native-paper (UI components)
- axios (HTTP client)
- react-native-calendars (calendar UI)
- expo-location, expo-secure-store, expo-auth-session
  **Dev Dependencies:**
- TypeScript 5.9.2
- ESLint with expo config

### app.json

**Location:** `/home/user/RAYCARWASH-app/app.json`

- **Slug:** raycarwash-app
- **Scheme:** raycarwash
- **Bundle ID:** com.raycarwash.app
- **Orientation:** portrait
- **New Arch:** enabled
- **Plugins:**
  - expo-splash-screen (with custom splash icon)
  - expo-secure-store
  - expo-barcode-scanner
  - expo-apple-authentication
  - expo-location (with location permission text)
- **Android Permissions:** ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION
- **Experiments:** typedRoutes (false), reactCompiler (true)

### tsconfig.json

**Location:** `/home/user/RAYCARWASH-app/tsconfig.json`

- Extends "expo/tsconfig.base"
- Strict mode enabled
- Path alias: `@/*` → `./`
- Includes all `.ts` and `.tsx` files

---

## 2. ALL FILES UNDER src/ (with descriptions)

### **CONFIG FILES**

#### `/src/config/app.config.ts`

Central app configuration with API base URL, support email, URLs for privacy/terms, app store links, and fallback coordinates for Fort Wayne, IN.

#### `/src/config/oauth.ts`

## OAuth client configuration with empty placeholders for Google Client IDs (web, iOS, Android) and notes on Apple authentication setup.

### **NAVIGATION FILES**

#### `/src/navigation/AppNavigator.tsx`

Root navigation structure with:

- **Stack Navigator** (initialRoute: Login)
- **Tab Navigator** (for clients): Home, Vehicles, Profile
- **Detailer Tab Navigator**: Operations (DetailerHome), Profile (DetailerProfile)
- **Auth Routes**: Login, Register
- **Shared Overlay Screens**: AddVehicle, VehicleDetail, SelectVehicles, Schedule, DetailerSelection, BookingSummary, Booking
- **Detailer Routes**: DetailerOnboarding, DetailerServices

#### `/src/navigation/types.ts`

Defines:

- `UserRole` enum: CLIENT, DETAILER, ADMIN
- `UserProfile` interface (extends backend UserProfile with role)
- `RootStackParamList` with full navigation type definitions for all 20+ screens and their parameters

#### `/src/navigation/navigationRef.ts`

## Navigation ref container for imperative navigation outside of component tree.

### **HOOK FILES**

#### `/src/hooks/useLocation.ts`

- Requests foreground location permission
- Fetches current position (latitude, longitude)
- Performs reverse geocoding to get city, region, zipcode
- Returns: `{ city, region, zipcode, lat, lng, loading, permissionDenied }`
- Uses expo-location

#### `/src/hooks/useWeather.ts`

- Fetches weather from Open-Meteo API
- Maps WMO weather codes to conditions (Clear, Rain, Snow, Thunderstorm, etc.)
- Evaluates `isGoodForDetailing` (true for clear/cloudy, false for rain/snow)
- Returns: `{ temperature, condition, icon, isGoodForDetailing, loading }`
- Returns temperature in Fahrenheit

#### `/src/hooks/useAppNavigation.ts`

## Typed navigation hook that wraps `useNavigation<AppNavigationProp>` for type-safe navigation access throughout the app.

### **SERVICE FILES** (API Layer)

#### `/src/services/api.ts`

Axios client configuration with interceptors:

- **authClient**: `baseURL: /auth` (no token for login)
- **apiClient**: `baseURL: /api/v1` (with token injection)
- **Request Interceptor**: Injects Bearer token from secure storage
- **Response Interceptor**: 401 handling with auto-refresh token logic + re-queueing of pending requests
- On refresh failure, clears tokens and redirects to Login

#### `/src/services/auth.service.ts`

Authentication endpoints:

- `loginWithBackend(email, password)` → POST /token (form-urlencoded)
- `registerUser(payload)` → POST /users
- `refreshAccessToken(refreshToken)` → POST /refresh?refresh_token=...
- `loginWithGoogle(accessToken)` → POST /auth/google
- `loginWithApple(identityToken, fullName?)` → POST /auth/apple
- `requestPasswordReset(email)` → POST /auth/password-reset
- `logout()` → Clears stored tokens

#### `/src/services/user.service.ts`

User profile endpoints:

- `getUserProfile()` → GET /me (returns UserProfile with email, full_name, phone, role, is_active, is_verified, service_address, timestamps)
- `updateUserProfile(userData)` → PUT /update (updates full_name, phone_number, service_address)

#### `/src/services/vehicle.service.ts`

Vehicle management:

- `getMyVehicles()` → GET /vehicles
- `addVehicle(vehicleData)` → POST /vehicles
- `decodeVehicleVin(vin)` → GET /vehicles/lookup/{vin} (returns make, model, year, series, body_class)
- `deleteVehicle(id)` → DELETE /vehicles/{id}
- `updateVehicle(id, data)` → PUT /vehicles/{id}
  **Vehicle interface**: id, vin, make, model, year, series, license_plate, color, body_class, notes

#### `/src/services/appointment.service.ts`

Appointment lifecycle (Sprint 5 multi-vehicle support):

- `createAppointment(payload)` → POST /appointments (multi-vehicle with addons)
- `getMyAppointments(page, page_size)` → GET /appointments/mine (paginated)
- `getAppointmentById(id)` → GET /appointments/{id}
- `patchAppointmentStatus(id, payload)` → PATCH /appointments/{id}/status
  **Payload structure**: detailer_id, scheduled_time (ISO UTC), service_address, coordinates, vehicles array (vehicle_id, service_id, addon_ids)

#### `/src/services/addon.service.ts`

Add-ons catalog:

- `getAddons()` → GET /addons (returns Addon[] with id, name, price_cents, description)

#### `/src/services/service.service.ts`

Service catalog:

- `getServices()` → GET /services (returns Service[] with id, name, description, category, price_small/medium/large/xl in cents, duration_minutes)

#### `/src/services/detailer.service.ts`

Public detailer endpoints:

- `getDetailers(params?)` → GET /detailers (public listing with lat/lng/radius/rating filters)
- `getDetailerAvailability(detailerId, params)` → GET /detailers/{id}/availability (time slots for date)
- `getMatching(params)` → GET /matching (smart matching with prices, duration, available slots)
  **Returns:** MatchedDetailer with distance_miles, estimated_price, estimated_duration, available_slots

#### `/src/services/detailer-private.service.ts`

Authenticated detailer endpoints:

- `getMyDetailerProfile()` → GET /detailers/me (with earnings, total_services, specialties)
- `upsertDetailerProfile(payload)` → PUT /detailers/me (bio, years_of_experience, service_radius_miles, specialties)
- `toggleAcceptingBookings(accepting)` → PATCH /detailers/me/status
- `getMyDetailerServices()` → GET /detailers/me/services (with custom_price_cents per service)
- `updateDetailerService(serviceId, payload)` → PATCH /detailers/me/services/{serviceId}

---

### **UTILITY FILES**

#### `/src/utils/storage.ts`

Secure token management using expo-secure-store:

- `saveToken(token)` / `getToken()` / `removeToken()` (access token)
- `saveRefreshToken(token)` / `getRefreshToken()` / `removeRefreshToken()` (refresh token)
- `clearAuthTokens()` (clear both)

#### `/src/utils/formatters.ts`

Display helpers:

- `STATUS_COLORS` map (pending, confirmed, in_progress, completed, cancelled, no_show)
- `COLOR_MAP` (20+ color names → hex codes)
- `getInitials(name)` → "JD" from "John Doe"
- `getMemberStatus(washes)` → Tier label (Bronze/Silver/Gold/Platinum)
- `getCarIcon(bodyClass)` → Icon name for vehicle type
- `getColorDot(color)` → Hex color code
- `getCountdown(iso)` → "2d 3h" format
- `formatPrice(cents)` → "$50" format
- `getGreeting()` → Time-based greeting
- `getFirstName(name)` → First word of name

#### `/src/utils/auth-redirect.ts`

Post-login navigation logic:

- `navigateAfterAuth(navigation)` → Fetches user profile and redirects:
  - Client → Main (tab navigator)
  - Detailer without profile → DetailerOnboarding
  - Detailer with profile → DetailerMain

#### `/src/utils/pricing.ts`

Vehicle size-based pricing:

- `getServicePrice(vehicle, service)` → Maps body_class to price_small/medium/large/xl and returns dollars

---

### **THEME FILES**

#### `/src/theme/colors.ts`

Centralized theme colors:

- `background`: #0B0F1A (dark navy)
- `card`: #121826 (dark slate)
- `primary`: #3B82F6 (blue)
- `text`: #FFFFFF
- `secondaryText`: #9CA3AF (gray)

---

## 3. SCREEN FILES (25 screens)

### **Authentication Screens**

#### `/src/screens/LoginScreen.tsx`

Email/password login with social auth (Google, Apple):

- Form validation with error display
- Password visibility toggle
- Google OAuth flow using expo-auth-session
- Apple Sign-In using expo-apple-authentication
- Password reset request
- Redirects to RegisterScreen or navigates after successful auth
- Calls `navigateAfterAuth()` to route based on user role

#### `/src/screens/RegisterScreen.tsx`

User registration with role selection:

- Client/Detailer role toggle (enum-based)
- Form fields: full_name, email, phone_number, password, confirm_password
- Password strength meter (Weak/Fair/Good/Strong)
- Email validation & password confirmation
- Terms acceptance checkbox
- Google OAuth integration
- Phone number optional field

---

### **Client Main Screens (Tab Navigator)**

#### `/src/screens/HomeScreen.tsx`

Client home dashboard:

- User greeting (Good morning/afternoon/evening)
- Weather display with detailing suitability (useWeather hook)
- Quick service shortcuts (Full Detail, Exterior, Interior, Headlights)
- Recent vehicles fleet carousel
- Upcoming/recent appointments list with status colors
- Book new service button
- Uses useLocation for weather data

#### `/src/screens/VehiclesScreen.tsx`

Vehicle fleet management:

- Lists all user vehicles with make, model, year, color
- Color dot indicator
- Car icon based on body_class
- Tap to view/edit vehicle details
- "Add Vehicle" button
- Pull-to-refresh

#### `/src/screens/ProfileScreen.tsx`

Client profile summary:

- User info (name, email, phone)
- Membership tier (Bronze/Silver/Gold/Platinum based on wash count)
- Completed washes count
- Vehicles summary
- Quick links: Edit Profile, Support, Privacy, Terms
- Logout

---

### **Booking Flow Screens (Client)**

#### `/src/screens/SelectVehiclesScreen.tsx`

Multi-vehicle selection (Step 1):

- Lists user vehicles
- Multi-select checkbox UX
- Selected count display
- Proceed to BookingScreen with selectedVehicles param

#### `/src/screens/BookingScreen.tsx`

Service + Add-ons selection (Step 2):

- Displays all available services (from GET /services)
- Lists all available add-ons (from GET /addons)
- Per-vehicle service picker (base service required, addons optional)
- Calculates total price based on vehicle sizes + selected services/addons
- Uses pricing utility to map body_class → price tier
- Passes to ScheduleScreen with selections, vehicles, total

#### `/src/screens/ScheduleScreen.tsx`

Date selection (Step 3):

- Calendar UI (react-native-calendars)
- Select appointment date
- Proceed to DetailerSelectionScreen

#### `/src/screens/DetailerSelectionScreen.tsx`

Detailer + time slot selection (Step 4):

- Uses useLocation for current coordinates
- Calls GET /matching with date, service_id, vehicle_sizes, addons
- Displays matched detailers with:
  - Distance, rating, availability
  - Estimated price & duration
  - Time slot selector
- Passes to BookingSummaryScreen with selected detailer & time

#### `/src/screens/BookingSummaryScreen.tsx`

Review & confirm booking:

- Shows detailer name, address, time
- Lists selected vehicles & services
- Total price breakdown
- Calls POST /appointments (multi-vehicle payload)
- Navigates to success or error handling

---

### **Vehicle Management Screens**

#### `/src/screens/AddVehicleScreen.tsx`

Add new vehicle:

- VIN input with optional auto-lookup (GET /vehicles/lookup/{vin})
- Manual input: make, model, year, body_class, color, license_plate
- Color & body type picker modals
- Form validation
- Calls POST /vehicles

#### `/src/screens/VehicleDetailScreen.tsx`

Edit/delete vehicle:

- Pre-filled with current vehicle data
- Edit: vin, make, model, year, body_class, color, license_plate, notes
- Save changes (PUT /vehicles/{id})
- Delete with confirmation (DELETE /vehicles/{id})
- Color & body type picker modals

---

### **Profile Editing**

#### `/src/screens/EditProfileScreen.tsx`

User profile editor:

- Edit: full_name, phone_number, service_address
- Address field auto-focus when navigated from detailer onboarding
- Calls PUT /update
- Validation: full_name required

---

### **Detailer Main Screens (Tab Navigator)**

#### `/src/screens/DetailerHomeScreen.tsx`

Detailer operations dashboard:

- User greeting & earnings summary
- Toggle "Accepting Bookings" status (PATCH /detailers/me/status)
- Appointments list with filters:
  - Pending (yellow), Confirmed (blue), In Progress (green), Completed (gray), Cancelled (red)
- Appointment actions: Confirm, Start, Complete (mark actual_price), Cancel
- Vehicle info & client notes display
- Countdown timer to appointment
- Linking to contact/maps

#### `/src/screens/DetailerProfileScreen.tsx`

Detailer profile page:

- Profile info: name, email, bio, years of experience
- Stats: total earnings, total services, average rating, reviews
- Specialties list
- Service radius
- Edit Profile link
- Manage Services link
- Logout

---

### **Detailer Onboarding/Setup**

#### `/src/screens/DetailerOnboardingScreen.tsx`

First-time detailer setup:

- Bio input (required)
- Years of experience (0-60)
- Service radius picker (5/10/15/25 miles)
- Specialties multi-select (8 options: Ceramic Coating, Interior Deep Clean, Paint Correction, etc.)
- Submit calls PUT /detailers/me (upsert)
- Navigates to DetailerMain after success

#### `/src/screens/DetailerServicesScreen.tsx`

Service activation & pricing:

- Lists all services from GET /detailers/me/services
- Toggle active/inactive per service
- Custom price override input (optional)
- Displays base price for reference
- Save changes (PATCH /detailers/me/services/{serviceId} for each)
- Saves only dirty services

---

## 4. NAVIGATION STRUCTURE (Complete)

### **Root Stack (RootStackParamList)**

```
Login
└─ Register (with optional initialRole param)
Main (Client Tab Navigator)
├─ Home
├─ Vehicles
└─ Profile
DetailerMain (Detailer Tab Navigator)
├─ DetailerHome
└─ DetailerProfile
[Shared Modal Screens - overlap both flows]
├─ AddVehicle
├─ VehicleDetail { vehicle: Vehicle }
├─ SelectVehicles
├─ Booking { selectedVehicles }
├─ Schedule { selections, vehicles, total }
├─ DetailerSelection { selections, vehicles, total, date }
├─ BookingSummary { selections, vehicles, total, detailerId, detailerName, scheduledTime, address, coords }
├─ EditProfile { user, focusAddress? }
├─ DetailerOnboarding
└─ DetailerServices
```

### **Navigation Flow for Clients**

1. Login → Main (Home tab)
2. Select Vehicles → Booking (services/addons) → Schedule (date) → DetailerSelection (detailer/time) → BookingSummary → Confirm
3. Home → Book → Same flow

### **Navigation Flow for Detailers**

1. Register as Detailer → DetailerOnboarding → DetailerServices → DetailerMain
2. DetailerMain → View/manage appointments, toggle accepting bookings

---

## 5. ALL SERVICES - API ENDPOINTS SUMMARY

| Service                  | Endpoint                     | Method | Auth | Purpose                     |
| ------------------------ | ---------------------------- | ------ | ---- | --------------------------- |
| auth.service             | /token                       | POST   | No   | Email/password login        |
| auth.service             | /users                       | POST   | No   | Register user               |
| auth.service             | /refresh                     | POST   | No   | Refresh access token        |
| auth.service             | /auth/google                 | POST   | Yes  | Google OAuth exchange       |
| auth.service             | /auth/apple                  | POST   | Yes  | Apple OAuth exchange        |
| auth.service             | /auth/password-reset         | POST   | Yes  | Request password reset      |
| user.service             | /me                          | GET    | Yes  | Get user profile            |
| user.service             | /update                      | PUT    | Yes  | Update user profile         |
| vehicle.service          | /vehicles                    | GET    | Yes  | Get all vehicles            |
| vehicle.service          | /vehicles                    | POST   | Yes  | Add vehicle                 |
| vehicle.service          | /vehicles/lookup/{vin}       | GET    | Yes  | Decode VIN                  |
| vehicle.service          | /vehicles/{id}               | DELETE | Yes  | Delete vehicle              |
| vehicle.service          | /vehicles/{id}               | PUT    | Yes  | Update vehicle              |
| appointment.service      | /appointments                | POST   | Yes  | Create appointment          |
| appointment.service      | /appointments/mine           | GET    | Yes  | Get user appointments       |
| appointment.service      | /appointments/{id}           | GET    | Yes  | Get appointment detail      |
| appointment.service      | /appointments/{id}/status    | PATCH  | Yes  | Update appointment status   |
| addon.service            | /addons                      | GET    | No   | Get add-ons catalog         |
| service.service          | /services                    | GET    | No   | Get services catalog        |
| detailer.service         | /detailers                   | GET    | No   | List detailers              |
| detailer.service         | /detailers/{id}/availability | GET    | No   | Get time slots              |
| detailer.service         | /matching                    | GET    | No   | Smart matching              |
| detailer-private.service | /detailers/me                | GET    | Yes  | Get own profile             |
| detailer-private.service | /detailers/me                | PUT    | Yes  | Upsert profile              |
| detailer-private.service | /detailers/me/status         | PATCH  | Yes  | Toggle accepting bookings   |
| detailer-private.service | /detailers/me/services       | GET    | Yes  | Get detailer services       |
| detailer-private.service | /detailers/me/services/{id}  | PATCH  | Yes  | Update service status/price |

---

## 6. ALL HOOKS

| Hook                 | File                             | Returns                                                          | Purpose                                          |
| -------------------- | -------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------ |
| `useLocation()`      | `/src/hooks/useLocation.ts`      | `{ city, region, zipcode, lat, lng, loading, permissionDenied }` | Get current location via GPS + reverse geocoding |
| `useWeather()`       | `/src/hooks/useWeather.ts`       | `{ temperature, condition, icon, isGoodForDetailing, loading }`  | Fetch weather from Open-Meteo API                |
| `useAppNavigation()` | `/src/hooks/useAppNavigation.ts` | `NativeStackNavigationProp<RootStackParamList>`                  | Typed navigation hook                            |

---

## 7. CONFIG & UTILITY SUMMARY

| File                          | Purpose               | Key Exports                                                    |
| ----------------------------- | --------------------- | -------------------------------------------------------------- |
| `/src/config/app.config.ts`   | Central config        | `APP_CONFIG` (apiBaseUrl, supportEmail, URLs, fallback coords) |
| `/src/config/oauth.ts`        | OAuth credentials     | `GOOGLE_CLIENT_IDS` (web, ios, android placeholders)           |
| `/src/utils/storage.ts`       | Secure token storage  | Save/get/clear tokens via expo-secure-store                    |
| `/src/utils/formatters.ts`    | Display formatters    | Status colors, color maps, initials, pricing, icons, countdown |
| `/src/utils/pricing.ts`       | Service pricing logic | `getServicePrice()` maps body_class → price tier               |
| `/src/utils/auth-redirect.ts` | Post-login routing    | `navigateAfterAuth()` routes by user role                      |
| `/src/theme/colors.ts`        | Theme constants       | `Colors` object (background, card, primary, text, secondary)   |

---

## 8. ENTRY POINT

### `/index.js`

```typescript
registerRootComponent(App);
```

### `/app.tsx`

```typescript
<SafeAreaProvider>
  <AppNavigator />
</SafeAreaProvider>
```

## AppNavigator is the root stack with Login as initial route, branches to Main (client) or DetailerMain (detailer) after auth.

## 9. KEY ARCHITECTURAL PATTERNS

1. **Auth Flow:** Login → Token stored in secure storage → Auto-refresh on 401 → Logout clears tokens
2. **Role-Based Navigation:** navigateAfterAuth() checks role enum and routes to appropriate tab navigator
3. **Multi-Vehicle Appointments:** Sprint 5 design with vehicles array + per-vehicle addons
4. **Shared Modals:** EditProfile, AddVehicle can be navigated from multiple places with params
5. **Interceptor Queue:** Pending requests queue during token refresh to avoid race conditions
6. **Type Safety:** RootStackParamList defines all routes and params; useAppNavigation provides typed access

---

## 10. TECH STACK SUMMARY

- **Framework:** React Native 0.81.5 with Expo 54
- **Navigation:** React Navigation 7 (stack + bottom tabs)
- **HTTP:** Axios with custom interceptors
- **Auth:** Email/password, Google OAuth, Apple Sign-In
- **Storage:** expo-secure-store for tokens, AsyncStorage available
- **Location:** expo-location with geocoding
- **Weather:** Open-Meteo free API
- **Calendar:** react-native-calendars
- **Icons:** @expo/vector-icons (Ionicons, MaterialCommunityIcons)
- **UI:** React Native Paper, Linear Gradient
- **Type Safety:** TypeScript 5.9
  This completes the comprehensive map of the RAYCARWASH app codebase.
  Agent
  Explore screens and business logic flow
  Perfect! Now I have comprehensive information about the screens. Let me compile the complete user flow and business logic analysis.

## Complete RayCarWash Application User Flow & Business Logic

### NAVIGATION STRUCTURE

**Root Navigator (AppNavigator.tsx):**

- **Login Screen** → Authentication entry point
- **Register Screen** → New user account creation (with role selection)
- **Main (Client Tab Navigator)** → Home, Vehicles, Profile tabs
- **DetailerMain (Detailer Tab Navigator)** → DetailerHome (Operations), DetailerProfile tabs
- **DetailerOnboarding** → Initial profile setup for detailers
- **DetailerServices** → Service catalog management
- **Booking Flow (Shared overlay screens)**:
  1. SelectVehicles → Booking → Schedule → DetailerSelection → BookingSummary

---

## CLIENT FLOW

### 1. **LoginScreen**

- **Purpose**: Authenticate existing users
- **Services Fetched**:
  - `loginWithBackend(email, password)`
  - `loginWithGoogle(accessToken)`
  - `loginWithApple(identityToken, fullName)`
  - `requestPasswordReset(email)`
- **User Actions**:
  - Email/password login with validation (email regex, password required)
  - Social login (Google, Apple on iOS only)
  - Password reset request
  - Navigate to Register
- **Navigation**: Redirects to `Main` (client) or `DetailerMain` (detailer) via `navigateAfterAuth()` based on user role
- **Key State**: Email, password, loading states, validation errors
- **UI Pattern**: LinearGradient dark background, custom styled inputs with validation, social divider

---

### 2. **RegisterScreen**

- **Purpose**: Create new user account with role selection (Client or Detailer)
- **Services Fetched**:
  - `registerUser(full_name, email, password, phone_number, role)`
  - `loginWithGoogle(accessToken)`
- **User Actions**:
  - Toggle between Client and Detailer role
  - Fill: Full Name, Email, Phone (optional), Password with strength indicator
  - Confirm password with match indicator
  - Accept Terms & Conditions
  - Google signup
- **Navigation**: Resets to LoginScreen after successful registration
- **Key State**:
  - Role selection (CLIENT/DETAILER enum)
  - Form fields (full_name, email, phone_number, password, confirm_password)
  - Password strength calculation (empty→weak→fair→good→strong)
  - Terms acceptance checkbox
- **UI Pattern**: Role buttons with icons, password strength bars (4-bar indicator), terms checkbox, gradient header

---

### 3. **HomeScreen** (Client Tab 1)

- **Purpose**: Dashboard showing upcoming appointments, vehicles, location-based info, weather
- **Services Fetched**:
  - `getUserProfile()`
  - `getMyVehicles()` - list of owned vehicles
  - `getMyAppointments(page, limit)` - pagination support
  - `useLocation()` hook - GPS coordinates
  - `useWeather(lat, lng)` hook - weather conditions
- **User Actions**:
  - View greeting personalized by time of day
  - See current location (city, region) with GPS detection
  - View weather card with detailing conditions indicator
  - See quick service shortcuts (Full Detail, Exterior, Interior, Headlights)
  - View active appointment with countdown timer
  - View upcoming appointments list with status badges
  - Navigate to Profile
  - Tap to start booking flow or view appointment details
- **Navigation**:
  - → Profile (avatar tap)
  - → Booking flow (quick service shortcuts)
- **Key State**:
  - User data (greeting, name, vehicle count)
  - Appointments (active, upcoming, completed washes count)
  - Weather data (temp, condition, suitability for detailing)
  - Member status based on completed washes (Bronze<3, Silver 3-7, Gold 8-14, Platinum 15+)
- **UI Pattern**:
  - Greeting with first name
  - Weather card with gradient (green if good, brown if bad)
  - Quick service buttons (4 columns)
  - Active job card with countdown
  - Appointment list with status color coding
  - Fleet carousel showing recent vehicles

---

### 4. **VehiclesScreen** (Client Tab 2 - "My Garage")

- **Purpose**: Manage user's vehicle collection
- **Services Fetched**:
  - `getMyVehicles()` - refreshed on screen focus
- **User Actions**:
  - View list of all registered vehicles as cards
  - Each card shows: Year/Make/Model, License Plate, Body Type badge, Color dot
  - Tap card → Navigate to VehicleDetailScreen
  - Tap "BOOK NOW" → Start booking with that vehicle
  - Tap "+" button → Add new vehicle
  - Empty state: "Your garage is empty" with call-to-action
- **Navigation**:
  - → AddVehicle (+ button or empty state CTA)
  - → VehicleDetail (card tap)
  - → Booking with selectedVehicles param
- **Key State**:
  - Vehicle list array
  - Loading state
  - useFocusEffect to refresh on tab focus
- **UI Pattern**:
  - Gradient overlay cards per vehicle color
  - MaterialCommunityIcons for car body types (estate, pickup, hatchback, sports, etc.)
  - Color-mapped dots from predefined color palette
  - Large "BOOK NOW" action button on each card

---

### 5. **AddVehicleScreen**

- **Purpose**: Register a new vehicle
- **Services Fetched**:
  - `decodeVehicleVin(vin)` - auto-populate make/model/year/body_class from VIN
  - `addVehicle(payload)` - save to backend
- **User Actions**:
  - Manual input: VIN (17 chars), Make, Model, License Plate, Year, Color, Body Type
  - Tap "Decode VIN" button to auto-fill details
  - Select from dropdowns: Year (last 40 years), Color (10 options), Body Type (7 options)
  - Validate: Make/Model/License Plate required
  - Save vehicle
- **Navigation**: ← Back after successful save
- **Key State**:
  - Form data: vin, make, model, year, body_class, color, license_plate, series, notes
  - Modal state (year/color/body selection)
  - Loading/decoding states
- **UI Pattern**:
  - Modal pickers for year/color/body type
  - VIN lookup with loading indicator
  - Uppercase conversion before submission

---

### 6. **VehicleDetailScreen**

- **Purpose**: View and edit vehicle details
- **Services Fetched**:
  - `updateVehicle(vehicleId, payload)`
  - `deleteVehicle(vehicleId)`
- **User Actions**:
  - Edit all vehicle fields (VIN, Make, Model, Year, Color, Body Type, License Plate, Notes)
  - Save changes
  - Delete vehicle (with confirmation alert)
- **Navigation**: ← Back after save/delete
- **Key State**:
  - Form state (populated from route params vehicle object)
  - Modal state for year/color/body selections
  - Loading states for save/delete
- **UI Pattern**:
  - Same modal picker pattern as AddVehicle
  - Delete button with destructive styling
  - Checkmark indicates current selection in modal

---

### 7. **ProfileScreen** (Client Tab 3)

- **Purpose**: View account info, stats, and manage preferences
- **Services Fetched**:
  - `getUserProfile()`
  - `getMyVehicles()`
  - `getMyAppointments(1, 100)` - get all for counting completed
- **User Actions**:
  - View avatar with initials
  - View profile card: Name, Email, Verified badge, Member status, Member since date
  - View stats: Completed Washes, Vehicles count, Member Status
  - Menu sections:
    - **ACCOUNT**: Personal Info (edit), My Vehicles (view), Payment Methods (coming soon)
    - **PREFERENCES**: Notifications (coming soon), Default Service Address (edit with focus flag), Change Password (coming soon)
    - **SUPPORT**: Help Center, Rate App, Privacy Policy
  - Sign Out (clears tokens, resets to Login)
  - Delete Account (email-based support)
- **Navigation**:
  - → EditProfile (Personal Info or Default Service Address menu items)
  - → Vehicles tab
  - → External: Email support
- **Key State**:
  - User data (full_name, email, phone_number, is_verified, created_at)
  - Stats: completed washes count, vehicle count
  - Member status derived from wash count
  - Loading state
- **UI Pattern**:
  - Avatar circle with initials and edit badge
  - Gradient background for profile card
  - MenuOption component for consistent menu items
  - Tag-based badges for status/verified/phone
  - Stats row with vertical dividers
  - ColoredMenuOption variants (icons with tinted backgrounds)

---

### 8. **EditProfileScreen**

- **Purpose**: Modify user profile information
- **Services Fetched**:
  - `updateUserProfile(full_name, phone_number, service_address)`
- **User Actions**:
  - Edit: Full Name, Phone Number, Service Address
  - Save changes
  - Optional auto-focus on Service Address field via route param
- **Navigation**: ← Back after save
- **Key State**:
  - Form data: full_name, phone_number, service_address
  - Loading state
  - focusAddress flag from route params
- **UI Pattern**:
  - Icon-prefixed input fields
  - Disabled email field (read-only)
  - TextInput ref for auto-focus capability

---

## CLIENT BOOKING FLOW (4 Steps)

### 9. **SelectVehiclesScreen** (Step 1 of 4)

- **Purpose**: Choose which vehicles to detail in this booking
- **Services Fetched**:
  - `getMyVehicles()`
- **User Actions**:
  - View all vehicles in list form
  - Checkbox/radio selection (can select multiple)
  - Tap "+" button to add new vehicle mid-booking
  - "NEXT" button (disabled if no vehicles selected)
- **Navigation**:
  - → BookingScreen with selectedVehicles array
  - → AddVehicle (modal overlay with + button)
- **Key State**:
  - selectedIds array (track selected vehicle IDs)
  - vehicles list
  - Loading state
- **UI Pattern**:
  - Radio button with checkmark and gradient highlight
  - Vehicle info: icon (make/model), license plate badge
  - Dynamic button enabled/disabled based on selection

---

### 10. **BookingScreen** (Step 2 of 4)

- **Purpose**: Select service(s) for each vehicle
- **Services Fetched**:
  - `getServices()` - main detailing services
  - `getAddons()` - optional add-ons/extras
- **User Actions**:
  - For each selected vehicle:
    - Select one base service (Full Detail, Exterior, Interior, etc.)
    - Select/deselect optional add-ons
  - View calculated total price (base + addons, vehicle-size-adjusted)
  - "NEXT" button (enabled when all vehicles have base service)
- **Navigation**:
  - → ScheduleScreen with selections (service choices per vehicle) + total price
- **Key State**:
  - selections: Record<vehicleId, {base: service, addons: addon[]}>
  - services and addons arrays
  - globalTotal (sum of all vehicle totals)
  - isReady (all vehicles have base service selected)
- **UI Pattern**:
  - Vehicle section headers with car icon
  - Service cards/pills (tap to select base)
  - Addon toggle rows with checkboxes
  - Real-time price calculation
  - Step indicator (2 of 4)

---

### 11. **ScheduleScreen** (Step 3 of 4)

- **Purpose**: Choose appointment date or use ASAP mode
- **Services Fetched**: None (UI only)
- **User Actions**:
  - Tap "ASAP Mode" → Skip to detailer selection without date constraint
  - Or: Tap calendar to select date (min date = today)
  - "FIND DETAILERS" button (enabled when date selected or ASAP)
- **Navigation**:
  - → DetailerSelectionScreen with selections, selectedVehicles, total, date (null if ASAP)
- **Key State**:
  - selectedDate (string ISO format or null for ASAP)
  - Passed params: selections, selectedVehicles, total
- **UI Pattern**:
  - ASAP card with flash icon and orange accent
  - react-native-calendars integration with custom theme (primary color highlight)
  - Divider pattern (OR PICK A DATE)
  - Selection preview with checkmark

---

### 12. **DetailerSelectionScreen** (Step 4a of 4)

- **Purpose**: Find and select detailer, choose time slot
- **Services Fetched**:
  - `getMatching(lat, lng, date, service_id, vehicle_sizes, addon_ids)` - finds available detailers
  - `useLocation()` hook - get current coordinates and address
- **User Actions**:
  - View list of matched detailers with:
    - Name, rating (1-5 stars), review count
    - Distance (miles)
    - Estimated price and duration
  - Tap detailer → Expand and see available time slots
  - Select time slot from dropdown
  - "CONFIRM" button (enabled when detailer + slot selected)
- **Navigation**:
  - → BookingSummaryScreen with detailer details, time slot, total (may differ from estimate)
- **Key State**:
  - matched: MatchedDetailer[] array
  - selectedDetailer: MatchedDetailer | null
  - selectedSlot: TimeSlotRead | null
  - locationLoading state
  - Derived: vehicleSize mapping, firstServiceId, addon_ids
- **UI Pattern**:
  - Detailer card with avatar, rating stars, distance
  - Expandable time slot dropdown (shows available slots only)
  - Fallback to app config coordinates if GPS unavailable
  - Step indicator visible

---

### 13. **BookingSummaryScreen** (Step 4b of 4)

- **Purpose**: Review and confirm final booking
- **Services Fetched**:
  - `createAppointment(detailer_id, scheduled_time, service_address, lat, lng, vehicles[])` - finalize
- **User Actions**:
  - Review appointment card: Date, Time, Detailer Name, Duration
  - Review service address and location
  - Review vehicle + service breakdown with prices
  - "CONFIRM BOOKING" button
  - After success: Alert with "Go Home" button
- **Navigation**:
  - After success → Reset to Main (home tab)
- **Key State**:
  - All route params from previous screens
  - Loading state during createAppointment
- **UI Pattern**:
  - Appointment ticket card with gradient
  - Service/addon breakdown table
  - Price summary with total
  - Confirmation alert after successful creation

---

## DETAILER FLOW

### 14. **DetailerOnboardingScreen**

- **Purpose**: Initial setup after detailer registration
- **Services Fetched**:
  - `upsertDetailerProfile(bio, years_of_experience, service_radius_miles, specialties)`
- **User Actions**:
  - Write professional bio (0-400 chars)
  - Enter years of experience (0-60)
  - Select service radius (5, 10, 15, 25 miles via pill buttons)
  - Select specialties (multiple choice from 8 options: Ceramic Coating, Interior Deep Clean, Paint Correction, Headlight Restoration, Engine Bay, Odor Elimination, Full Detail, Exterior Only)
  - Submit to complete onboarding
- **Navigation**:
  - After success → Redirects via `navigateAfterAuth()` to DetailerMain
- **Key State**:
  - bio string
  - years string (numeric input)
  - radius number
  - specialties array (selected keys)
  - Saving state
- **UI Pattern**:
  - Gradient header with logo icon
  - Textarea for bio with character count (400 max)
  - Pill buttons for radius selection (active state)
  - Specialty toggle grid with icons and labels

---

### 15. **DetailerHomeScreen** (Detailer Tab 1 - "Operations")

- **Purpose**: Dashboard for managing appointments and tracking earnings
- **Services Fetched**:
  - `getUserProfile()` - name
  - `getMyDetailerProfile()` - is_accepting_bookings, stats
  - `getMyAppointments(1, 50)` - all appointments
  - `patchAppointmentStatus(apptId, {status})` - update job status
  - `toggleAcceptingBookings(bool)` - availability toggle
- **User Actions**:
  - Toggle "Accepting Bookings" switch
  - View stats: Total Earnings, Total Jobs, Average Rating
  - See active job with live timer (elapsed time)
  - See next scheduled job
  - See today's jobs list
  - For each job: View client name, vehicle, address, time
    - Status badges with color coding
    - Action buttons: Confirm (pending→confirmed), Start (confirmed→in_progress), Complete (in_progress→completed), Cancel
    - Call client button (tel: link)
- **Navigation**:
  - → DetailerProfile (bottom tab)
  - → External: Phone call to client
- **Key State**:
  - userName, accepting, stats
  - appointments array with filtering (active, next, today)
  - elapsed timer (running while activeJob present)
  - Loading/refreshing states
  - Toggling status state
- **UI Pattern**:
  - Status-based color coding (yellow=pending, blue=confirmed, green=in_progress, gray=completed, red=cancelled)
  - Live timer (h:mm:ss format)
  - Expandable job cards
  - Pull-to-refresh gesture
  - Status transition alerts with confirmation

---

### 16. **DetailerProfileScreen** (Detailer Tab 2 - "Profile")

- **Purpose**: View professional profile, manage services, configure preferences
- **Services Fetched**:
  - `getUserProfile()` - name, email
  - `getMyDetailerProfile()` - full stats
- **User Actions**:
  - View profile card: Avatar with initials, Name, Email, Member since, Rating with review count, Member badge (based on jobs)
  - View performance stats: Earnings ($), Jobs (#), Rating (stars), Reviews (#), Years of Experience, Service Radius (miles)
  - Menu sections:
    - **GENERAL**: Bio & Experience (navigate to edit)
    - **SERVICES**: Manage Service Catalog (navigate to DetailerServicesScreen)
    - **PREFERENCES**: Accepting Bookings (toggle), Service Radius (view)
    - **ABOUT**: Member since, Specialties (if any)
  - Sign Out (clears tokens, resets to Login)
- **Navigation**:
  - → DetailerServicesScreen (Manage Service Catalog)
  - → External: Logout
- **Key State**:
  - User data (full_name, email)
  - Detailer profile (earnings, jobs, rating, reviews, years, radius, specialties, created_at)
  - Accepting bookings toggle
  - Loading/refreshing states
- **UI Pattern**:
  - Avatar circle with verification badge
  - Rating display with stars
  - Member badge with medal icon (color-coded by tier)
  - Stats grid with dividers
  - Pull-to-refresh on scroll

---

### 17. **DetailerServicesScreen**

- **Purpose**: Manage service pricing and availability
- **Services Fetched**:
  - `getMyDetailerServices()` - list of available services for this detailer
  - `updateDetailerService(serviceId, {is_active, custom_price_cents})` - save changes
- **User Actions**:
  - View all services from catalog
  - For each service:
    - Toggle on/off availability (switch)
    - Override price ($) - blank = use default
    - View default price (read-only)
  - "SAVE CHANGES" button (enabled when any field marked dirty)
  - Validation: Custom prices must be valid numeric values or blank
- **Navigation**: ← Back (no explicit nav needed)
- **Key State**:
  - services: ServiceDraft[] (with draftPrice string for editing, dirty flag)
  - isDirty boolean (any service has unsaved changes)
  - Loading/saving states
- **UI Pattern**:
  - Switch toggles for is_active (React Native Switch component)
  - Price input field with $ prefix and validation
  - Default price display (read-only comparison)
  - Dirty-only save strategy (only send changed services to backend)
  - Currency conversion: $string ↔ cents number

---

## KEY BUSINESS LOGIC PATTERNS

### Booking Flow Data Threading:

Each screen passes accumulated data forward:

1. **SelectVehicles** → selectedVehicles: Vehicle[]
2. **Booking** → selections + total (service choices per vehicle)
3. **Schedule** → date (null for ASAP)
4. **DetailerSelection** → detailerId, detailerName, scheduledTime, estimated_price
5. **BookingSummary** → Creates single multi-vehicle appointment with all addons

### Pricing Logic:

- **Vehicles have different sizes** → "small" (sedan/coupe), "medium" (SUV/hatchback), "large" (pickup), "xl" (van)
- **Services have base price** → Adjusted by vehicle size via `getServicePrice(vehicle, service)`
- **Addons have fixed price** → price_cents field (not vehicle-adjusted)
- **Total = (base × num_vehicles) + (addons sum)**

### Location & Matching:

- **GPS-based detailer matching** → Requires lat/lng + date + service_id + vehicle_sizes + addon_ids
- **Fallback fallback coords** → If GPS unavailable, use APP_CONFIG.fallbackCoords
- **Address resolution** → City, Region, Zipcode from GPS; displays as readable string

### Status Management:

- **Client**: pending → confirmed → in_progress → completed
- **Detailer**: pending → confirmed → in_progress → completed (or cancelled states)
- **Color coding**: Yellow, Blue, Green, Gray, Red respectively

### Member Status Tiers:

- **Bronze**: 0-2 washes
- **Silver**: 3-7 washes
- **Gold**: 8-14 washes
- **Platinum**: 15+ washes

### Detailer Specialties & Onboarding:

- Specialties are pre-defined keys (ceramic_coating, interior_deep_clean, etc.)
- Stored as array in detailer profile
- Selected during onboarding, may be updatable later

---

This completes the comprehensive mapping of all screens, data flows, and business logic for both the Cl

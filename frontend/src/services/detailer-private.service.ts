import { apiClient } from "./api";

/** Full detailer profile visible to the detailer themselves (authenticated). */
export interface DetailerOwnProfile {
  user_id: string;
  full_name: string;
  bio: string | null;
  years_of_experience: number | null;
  service_radius_miles: number;
  is_accepting_bookings: boolean;
  average_rating: number | null;
  total_reviews: number;
  total_earnings_cents: number;   // sum of completed appointment actual_prices
  total_services: number;         // count of completed appointments
  specialties: string[];
  created_at: string;
}

export interface DetailerServiceItem {
  service_id: string;
  name: string;
  description: string | null;
  base_price_cents: number;        // platform default (size-based min)
  custom_price_cents: number | null; // detailer override (null = use base)
  is_active: boolean;
}

export interface UpsertDetailerProfilePayload {
  bio?: string;
  years_of_experience?: number;
  service_radius_miles?: number;
  specialties?: string[];
  timezone?: string;
  working_hours?: Record<string, { start: string; end: string; enabled: boolean }>;
}

/**
 * GET /api/v1/detailers/me
 * Returns the authenticated detailer's own profile with earnings + stats.
 */
export const getMyDetailerProfile = async (): Promise<DetailerOwnProfile> => {
  const response = await apiClient.get("/detailers/me");
  return response.data;
};

/**
 * PUT /api/v1/detailers/me
 * Creates or updates the detailer profile (upsert).
 * Used both on onboarding and on profile edits.
 */
export const upsertDetailerProfile = async (
  payload: UpsertDetailerProfilePayload,
): Promise<DetailerOwnProfile> => {
  const response = await apiClient.put("/detailers/me", payload);
  return response.data;
};

/**
 * PATCH /api/v1/detailers/me/status
 * Toggles visibility in client-facing matching.
 */
export const toggleAcceptingBookings = async (
  accepting: boolean,
): Promise<void> => {
  await apiClient.patch("/detailers/me/status", {
    is_accepting_bookings: accepting,
  });
};

/**
 * GET /api/v1/detailers/me/services
 * Returns the service catalog with this detailer's active flags + custom prices.
 */
export const getMyDetailerServices = async (): Promise<DetailerServiceItem[]> => {
  const response = await apiClient.get("/detailers/me/services");
  return response.data;
};

/**
 * PATCH /api/v1/detailers/me/services/{serviceId}
 * Toggles a service on/off and optionally sets a custom price.
 */
export const updateDetailerService = async (
  serviceId: string,
  payload: { is_active: boolean; custom_price_cents?: number | null },
): Promise<void> => {
  await apiClient.patch(`/detailers/me/services/${serviceId}`, payload);
};

// ------------------------------------------------------------------ //
//  Identity Verification (Stripe Identity)                           //
// ------------------------------------------------------------------ //

export interface VerificationStartResponse {
  is_dev_bypass: boolean;
  client_secret?: string;
  session_id?: string;
  stripe_publishable_key?: string;
}

export interface VerificationSubmitPayload {
  legal_full_name: string;
  date_of_birth: string;        // ISO date "YYYY-MM-DD"
  address_line1: string;
  city: string;
  state: string;
  zip_code: string;
  background_check_consent: boolean;
  session_id?: string | null;   // null = dev bypass
}

export interface VerificationStatusResponse {
  verification_status: "not_submitted" | "pending" | "approved" | "rejected";
  legal_full_name: string | null;
  verification_submitted_at: string | null;
  verification_reviewed_at: string | null;
  rejection_reason: string | null;
}

/**
 * POST /api/v1/detailers/verification/start
 * Creates a Stripe Identity VerificationSession.
 * Returns is_dev_bypass=true in dev/debug mode — skip Stripe sheet.
 */
export const verificationStart = async (): Promise<VerificationStartResponse> => {
  const response = await apiClient.post("/detailers/verification/start");
  return response.data;
};

/**
 * POST /api/v1/detailers/verification/submit
 * Saves personal info + consent. Pass session_id=null for dev bypass.
 */
export const verificationSubmit = async (
  payload: VerificationSubmitPayload,
): Promise<{ verification_status: string; message: string }> => {
  const response = await apiClient.post("/detailers/verification/submit", payload);
  return response.data;
};

/**
 * GET /api/v1/detailers/verification/status
 */
export const getVerificationStatus = async (): Promise<VerificationStatusResponse> => {
  const response = await apiClient.get("/detailers/verification/status");
  return response.data;
};

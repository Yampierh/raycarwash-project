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

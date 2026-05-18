/**
 * frontend/src/services/provider-profile.service.ts
 *
 * Wraps /api/v1/users/me/provider-profile* and /provider-status
 * (Phase 5 chunk Y2).
 */
import { apiClient, unwrap } from "./api";

export interface ProviderProfile {
  user_id: string;
  business_name: string | null;
  display_name: string | null;
  tagline: string | null;
  bio: string | null;
  years_of_experience: number | null;
  is_accepting_bookings: boolean;
  service_radius_miles: number;
  average_rating: number | null;
  total_reviews: number;
  total_services_completed: number;
  earnings_lifetime_cents: number;
  verification_status: string;
  background_check_consent: boolean;
  social_links: Record<string, string> | null;
  cover_photo_s3_key: string | null;
  cover_url: string | null;
  working_hours: Record<string, unknown> | null;
  timezone: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProviderActivatePayload {
  business_name: string;
  display_name?: string | null;
  service_radius_miles?: number;
}

export type ProviderUpdatePayload = Partial<{
  business_name: string;
  display_name: string | null;
  tagline: string | null;
  bio: string | null;
  years_of_experience: number | null;
  service_radius_miles: number;
  social_links: Record<string, string> | null;
  working_hours: Record<string, unknown> | null;
}>;

export async function getProviderProfile(): Promise<ProviderProfile> {
  const res = await apiClient.get("/api/v1/users/me/provider-profile");
  return unwrap<ProviderProfile>(res);
}

export async function activateProvider(
  body: ProviderActivatePayload,
): Promise<ProviderProfile> {
  const res = await apiClient.post("/api/v1/users/me/provider-profile", body);
  return unwrap<ProviderProfile>(res);
}

export async function updateProvider(
  body: ProviderUpdatePayload,
): Promise<ProviderProfile> {
  const res = await apiClient.patch("/api/v1/users/me/provider-profile", body);
  return unwrap<ProviderProfile>(res);
}

export async function deactivateProvider(): Promise<ProviderProfile> {
  const res = await apiClient.post(
    "/api/v1/users/me/provider-profile/deactivate",
  );
  return unwrap<ProviderProfile>(res);
}

export async function setProviderStatus(
  isAccepting: boolean,
): Promise<ProviderProfile> {
  const res = await apiClient.patch("/api/v1/users/me/provider-status", {
    is_accepting_bookings: isAccepting,
  });
  return unwrap<ProviderProfile>(res);
}

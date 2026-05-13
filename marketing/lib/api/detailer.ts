import { apiClient } from "./client";

export type VerificationStartResponse = {
  is_dev_bypass: boolean;
  client_secret?: string;
  session_id?: string;
};

export type VerificationSubmitRequest = {
  legal_full_name: string;
  date_of_birth: string; // YYYY-MM-DD
  address: string;
  city: string;
  state: string;
  zip: string;
  background_check_consent: boolean;
  session_id?: string;
};

export type VerificationStatus = {
  verification_status: "not_submitted" | "pending" | "approved" | "rejected";
  legal_full_name?: string | null;
  submitted_at?: string | null;
  reviewed_at?: string | null;
  rejection_reason?: string | null;
};

export type DetailerService = {
  service_id: string;
  name: string;
  description?: string | null;
  base_price_cents: number;
  custom_price_cents: number | null;
  is_active: boolean;
};

export type DetailerMe = {
  user_id: string;
  full_name: string;
  bio?: string | null;
  years_of_experience?: number | null;
  service_radius_miles: number;
  is_accepting_bookings: boolean;
  average_rating?: number | null;
  total_reviews: number;
  total_earnings_cents: number;
  total_services: number;
  specialties: string[];
  created_at: string;
};

export type WorkingHoursDay = {
  start: string;
  end: string;
  enabled?: boolean;
};

export type DetailerProfileUpdate = {
  bio?: string | null;
  years_of_experience?: number | null;
  service_radius_miles?: number | null;
  is_accepting_bookings?: boolean | null;
  timezone?: string | null;
  working_hours?: Record<string, WorkingHoursDay> | null;
};

export async function startVerification() {
  const res = await apiClient.post<VerificationStartResponse>(
    "/detailers/verification/start"
  );
  return res.data;
}

export async function submitVerification(body: VerificationSubmitRequest) {
  const res = await apiClient.post(`/detailers/verification/submit`, body);
  return res.data;
}

export async function getVerificationStatus() {
  const res = await apiClient.get<VerificationStatus>(
    "/detailers/verification/status"
  );
  return res.data;
}

export async function getMyServices() {
  const res = await apiClient.get<DetailerService[]>("/detailers/me/services");
  return res.data;
}

export async function toggleService(
  serviceId: string,
  body: { is_active: boolean; custom_price_cents?: number | null }
) {
  const res = await apiClient.patch(
    `/detailers/me/services/${serviceId}`,
    body
  );
  return res.data;
}

export async function getMyDetailer() {
  const res = await apiClient.get<DetailerMe>("/detailers/me");
  return res.data;
}

export async function updateMyDetailer(body: DetailerProfileUpdate) {
  const res = await apiClient.put<DetailerMe>("/detailers/me", body);
  return res.data;
}

export async function setAcceptingBookings(is_accepting_bookings: boolean) {
  const res = await apiClient.patch<DetailerMe>("/detailers/me/status", {
    is_accepting_bookings,
  });
  return res.data;
}

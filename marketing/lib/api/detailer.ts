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

export type DetailerService = {
  service_id: string;
  name: string;
  base_price_cents: number;
  custom_price_cents: number | null;
  is_active: boolean;
};

export type DetailerMe = {
  id: string;
  bio?: string | null;
  years_of_experience?: number | null;
  service_radius_miles?: number | null;
  is_accepting_bookings?: boolean;
  verification_status?: "not_submitted" | "pending" | "approved" | "rejected";
  total_earnings_cents?: number;
  total_services?: number;
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

export async function updateMyDetailer(body: Partial<DetailerMe>) {
  const res = await apiClient.put<DetailerMe>("/detailers/me", body);
  return res.data;
}

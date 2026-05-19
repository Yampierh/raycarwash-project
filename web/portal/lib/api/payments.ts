import { apiClient } from "./client";

export type FareEstimateRequest = {
  service_id: string;
  vehicle_sizes: string[];
  client_lat: number;
  client_lng: number;
};

export type FareEstimateResponse = {
  fare_token: string;
  base_price_cents: number;
  surge_multiplier: number;
  estimated_price_cents: number;
  nearby_detailers_count: number;
  expires_at: string;
};

export type PaymentIntent = {
  payment_intent_id: string;
  client_secret: string;
  amount_cents: number;
  currency: string;
  status: string;
};

export async function estimateFare(body: FareEstimateRequest) {
  const res = await apiClient.post<FareEstimateResponse>(
    "/fares/estimate",
    body
  );
  return res.data;
}

export async function createPaymentIntent(appointment_id: string) {
  const res = await apiClient.post<PaymentIntent>("/payments/create-intent", {
    appointment_id,
  });
  return res.data;
}

import { apiClient } from "./api";

export interface PaymentIntentResponse {
  payment_intent_id: string;
  client_secret: string;
  amount_cents: number;
  currency: string;
  status: string;
}

export interface PaymentIntentRequest {
  appointment_id: string;
}

/**
 * POST /api/v1/payments/create-intent
 * Creates a Stripe PaymentIntent for a confirmed appointment.
 * Returns client_secret for React Native Stripe SDK.
 */
export const createPaymentIntent = async (
  appointmentId: string
): Promise<PaymentIntentResponse> => {
  const response = await apiClient.post<PaymentIntentResponse>("/payments/create-intent", {
    appointment_id: appointmentId,
  });
  return response.data;
};

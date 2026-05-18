/**
 * frontend/src/services/payment-methods.service.ts
 *
 * Wraps /api/v1/users/me/payment-methods (Phase 4 chunk U).
 *
 * createSetupIntent + deletePaymentMethod live behind step-up; the
 * apiClient interceptor surfaces StepUpRequiredError so the UI can
 * route to the re-auth modal before retrying.
 *
 * `Idempotency-Key` is forwarded to Stripe via the backend — pass the
 * same client-supplied UUID if the user double-taps "Add card" so the
 * second tap returns the cached SetupIntent rather than minting a
 * fresh one.
 */
import { apiClient, unwrap } from "./api";

export interface PaymentMethod {
  id: string;
  type: string;
  brand: string | null;
  last4: string | null;
  exp_month: number | null;
  exp_year: number | null;
  billing_zip: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface SetupIntentResponse {
  setup_intent_id: string;
  client_secret: string;
  publishable_key: string;
}

export async function listPaymentMethods(): Promise<PaymentMethod[]> {
  const res = await apiClient.get("/api/v1/users/me/payment-methods");
  return unwrap<PaymentMethod[]>(res);
}

export async function getPaymentMethod(id: string): Promise<PaymentMethod> {
  const res = await apiClient.get(`/api/v1/users/me/payment-methods/${id}`);
  return unwrap<PaymentMethod>(res);
}

export async function createSetupIntent(
  idempotencyKey: string,
): Promise<SetupIntentResponse> {
  const res = await apiClient.post(
    "/api/v1/users/me/payment-methods/setup-intent",
    {},
    { headers: { "Idempotency-Key": idempotencyKey } },
  );
  return unwrap<SetupIntentResponse>(res);
}

export async function setDefaultPaymentMethod(id: string): Promise<PaymentMethod> {
  const res = await apiClient.patch(
    `/api/v1/users/me/payment-methods/${id}/default`,
  );
  return unwrap<PaymentMethod>(res);
}

export async function deletePaymentMethod(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/users/me/payment-methods/${id}`);
}

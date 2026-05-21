import { apiClient, unwrap } from "./client";

export type PaymentMethod = {
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
};

export async function listPaymentMethods(): Promise<PaymentMethod[]> {
  const res = await apiClient.get("/users/me/payment-methods");
  return unwrap<PaymentMethod[]>(res);
}

export async function setDefaultPaymentMethod(id: string): Promise<PaymentMethod> {
  const res = await apiClient.patch(`/users/me/payment-methods/${id}/default`);
  return unwrap<PaymentMethod>(res);
}

export async function deletePaymentMethod(id: string): Promise<void> {
  await apiClient.delete(`/users/me/payment-methods/${id}`);
}

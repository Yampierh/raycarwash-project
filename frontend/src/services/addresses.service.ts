/**
 * frontend/src/services/addresses.service.ts
 *
 * Wraps /api/v1/users/me/addresses (Phase 4 chunk T).
 *
 * All endpoints return the envelope `{data, meta, links}`; we unwrap to
 * `data` here so the React Query hooks store the bare resource shapes.
 */
import { apiClient, unwrap } from "./api";

export interface Address {
  id: string;
  label: string | null;
  line1: string;
  line2: string | null;
  city: string;
  state: string;
  zip_code: string;
  country: string;
  notes: string | null;
  latitude: string | null;
  longitude: string | null;
  h3_index_r9: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface AddressCreatePayload {
  label?: string | null;
  line1: string;
  line2?: string | null;
  city: string;
  state: string;
  zip_code: string;
  country?: string;
  notes?: string | null;
  is_default?: boolean;
}

export type AddressUpdatePayload = Partial<AddressCreatePayload>;

export async function listAddresses(): Promise<Address[]> {
  const res = await apiClient.get("/api/v1/users/me/addresses");
  return unwrap<Address[]>(res);
}

export async function getAddress(id: string): Promise<Address> {
  const res = await apiClient.get(`/api/v1/users/me/addresses/${id}`);
  return unwrap<Address>(res);
}

export async function createAddress(body: AddressCreatePayload): Promise<Address> {
  const res = await apiClient.post("/api/v1/users/me/addresses", body);
  return unwrap<Address>(res);
}

export async function updateAddress(
  id: string,
  body: AddressUpdatePayload,
): Promise<Address> {
  const res = await apiClient.patch(`/api/v1/users/me/addresses/${id}`, body);
  return unwrap<Address>(res);
}

export async function setDefaultAddress(id: string): Promise<Address> {
  const res = await apiClient.patch(`/api/v1/users/me/addresses/${id}/default`);
  return unwrap<Address>(res);
}

export async function deleteAddress(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/users/me/addresses/${id}`);
}

import { apiClient, unwrap } from "./client";

export type Address = {
  id: string;
  label: string | null;
  line1: string;
  line2: string | null;
  city: string;
  state: string;
  zip_code: string;
  country: string;
  notes: string | null;
  latitude: number | null;
  longitude: number | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};

export type AddressCreate = {
  label?: string;
  line1: string;
  line2?: string;
  city: string;
  state: string;
  zip_code: string;
  country?: string;
  notes?: string;
  is_default?: boolean;
};

export async function listAddresses(): Promise<Address[]> {
  const res = await apiClient.get("/users/me/addresses");
  return unwrap<Address[]>(res);
}

export async function createAddress(body: AddressCreate): Promise<Address> {
  const res = await apiClient.post("/users/me/addresses", body);
  return unwrap<Address>(res);
}

export async function updateAddress(
  id: string,
  body: Partial<AddressCreate>
): Promise<Address> {
  const res = await apiClient.patch(`/users/me/addresses/${id}`, body);
  return unwrap<Address>(res);
}

export async function setDefaultAddress(id: string): Promise<Address> {
  const res = await apiClient.patch(`/users/me/addresses/${id}/default`);
  return unwrap<Address>(res);
}

export async function deleteAddress(id: string): Promise<void> {
  await apiClient.delete(`/users/me/addresses/${id}`);
}

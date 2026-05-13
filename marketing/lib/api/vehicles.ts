import { apiClient } from "./client";

export type Vehicle = {
  id: string;
  owner_id: string;
  make: string;
  model: string;
  year: number;
  vin: string | null;
  series: string | null;
  body_class: string | null;
  color: string;
  license_plate: string;
  suggested_size: string | null;
  created_at: string;
  updated_at: string;
};

export type VehicleCreate = {
  make: string;
  model: string;
  year: number;
  vin?: string | null;
  series?: string | null;
  body_class: string;
  color?: string | null;
  license_plate?: string | null;
  notes?: string | null;
};

export type VinLookup = {
  make?: string;
  model?: string;
  year?: number;
  body_class?: string;
  series?: string;
  [k: string]: unknown;
};

export async function listVehicles() {
  const res = await apiClient.get<Vehicle[]>("/vehicles");
  return res.data;
}

export async function createVehicle(body: VehicleCreate) {
  const res = await apiClient.post<Vehicle>("/vehicles", body);
  return res.data;
}

export async function updateVehicle(id: string, body: VehicleCreate) {
  const res = await apiClient.put<Vehicle>(`/vehicles/${id}`, body);
  return res.data;
}

export async function deleteVehicle(id: string) {
  await apiClient.delete(`/vehicles/${id}`);
}

export async function lookupVin(vin: string) {
  const res = await apiClient.get<VinLookup>(`/vehicles/lookup/${vin}`);
  return res.data;
}

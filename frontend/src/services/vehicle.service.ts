import { apiClient } from "./api";

/**
 * Standardized Vehicle Sizes to match Backend Enums
 */
export interface Vehicle {
  id: string;
  vin?: string | null;
  make: string;
  model: string;
  year: number;
  series?: string;
  license_plate: string;
  color: string;
  body_class?: string;
  notes?: string;
}

/**
 * Interface for the VIN decoding response
 * Matches the backend lookup logic in vehicle_router.py
 */
export interface VinDecodeResponse {
  make: string;
  model: string;
  year: number;
  series?: string;
  body_class: string;
}

/**
 * Fetch all vehicles owned by the current user
 * Endpoint: GET /api/v1/vehicles
 */
export const getMyVehicles = async (): Promise<Vehicle[]> => {
  const response = await apiClient.get<Vehicle[]>("/vehicles");
  return response.data;
};

/**
 * Add a new vehicle to the user's profile
 * Endpoint: POST /api/v1/vehicles
 */
export const addVehicle = async (
  vehicleData: Partial<Vehicle>,
): Promise<Vehicle> => {
  const response = await apiClient.post<Vehicle>("/vehicles", {
    ...vehicleData,
    year: vehicleData.year
      ? Number(vehicleData.year)
      : new Date().getFullYear(),
  });
  return response.data;
};

/**
 * Endpoint: GET /api/v1/vehicles/lookup/{vin}
 */
export const decodeVehicleVin = async (
  vin: string,
): Promise<VinDecodeResponse> => {
  const response = await apiClient.get<VinDecodeResponse>(
    `/vehicles/lookup/${vin.toUpperCase()}`,
  );
  return response.data;
};

export const deleteVehicle = async (id: string) => {
  return await apiClient.delete(`/vehicles/${id}`);
};

export const updateVehicle = async (id: string, data: any) => {
  // Nota que NO hay una diagonal al final de vehicles
  return await apiClient.put(`/vehicles/${id}`, data);
};

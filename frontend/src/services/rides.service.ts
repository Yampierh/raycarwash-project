import { apiClient } from "./api";

export interface RideRequest {
  appointment_id: string;
  status: string;
  estimated_price_cents: number;
}

export const requestRide = async (fare_token: string): Promise<RideRequest> => {
  const { data } = await apiClient.post<RideRequest>("/rides/request", { fare_token });
  return data;
};

export const acceptRide = async (appointment_id: string): Promise<void> => {
  await apiClient.put(`/rides/${appointment_id}/accept`);
};

export const declineRide = async (appointment_id: string): Promise<void> => {
  await apiClient.put(`/rides/${appointment_id}/decline`);
};

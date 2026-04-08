import { apiClient } from "./api";

export interface Service {
  id: string;
  name: string;
  description: string | null;
  category: string;
  price_small: number;    // cents
  price_medium: number;
  price_large: number;
  price_xl: number;
  duration_minutes: number;
}

/**
 * GET /api/v1/services
 * Public catalog of available services.
 */
export const getServices = async (): Promise<Service[]> => {
  const response = await apiClient.get("/services");
  return response.data;
};

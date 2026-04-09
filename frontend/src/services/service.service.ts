import { apiClient } from "./api";

export interface Service {
  id: string;
  name: string;
  description: string | null;
  category: string;
  base_price_cents: number;
  base_duration_minutes: number;
  price_small: number;
  price_medium: number;
  price_large: number;
  price_xl: number;
  duration_small_minutes: number;
  duration_medium_minutes: number;
  duration_large_minutes: number;
  duration_xl_minutes: number;
  is_active: boolean;
  created_at: string;
}

export type VehicleSize = "small" | "medium" | "large" | "xl";

export const getPriceForSize = (service: Service, size: VehicleSize): number => {
  switch (size) {
    case "small": return service.price_small;
    case "medium": return service.price_medium;
    case "large": return service.price_large;
    case "xl": return service.price_xl;
    default: return service.price_small;
  }
};

export const getDurationForSize = (service: Service, size: VehicleSize): number => {
  switch (size) {
    case "small": return service.duration_small_minutes;
    case "medium": return service.duration_medium_minutes;
    case "large": return service.duration_large_minutes;
    case "xl": return service.duration_xl_minutes;
    default: return service.duration_small_minutes;
  }
};

/**
 * GET /api/v1/services
 * Public catalog of available services.
 */
export const getServices = async (): Promise<Service[]> => {
  const response = await apiClient.get("/services");
  return response.data;
};

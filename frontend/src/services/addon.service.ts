import { apiClient } from "./api";

export interface Addon {
  id: string;
  name: string;
  price_cents: number; // flat-rate in cents
  description?: string;
}

/**
 * GET /api/v1/addons
 * Public catalog of add-on extras (no auth required).
 */
export const getAddons = async (): Promise<Addon[]> => {
  const response = await apiClient.get("/addons");
  return response.data;
};

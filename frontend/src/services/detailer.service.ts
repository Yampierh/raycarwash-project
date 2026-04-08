import { apiClient } from "./api";

export interface DetailerPublicRead {
  user_id: string;
  full_name: string;
  bio: string | null;
  years_of_experience: number | null;
  service_radius_miles: number;
  is_accepting_bookings: boolean;
  average_rating: number | null;
  total_reviews: number;
  distance_miles: number | null;
}

export interface TimeSlotRead {
  start_time: string; // ISO 8601 UTC
  end_time: string;   // start + 30 minutos
  is_available: boolean;
}

export interface DetailersQueryParams {
  lat?: number;
  lng?: number;
  radius_miles?: number;
  min_rating?: number;
  page?: number;
  page_size?: number;
}

export interface AvailabilityQueryParams {
  request_date: string;       // "YYYY-MM-DD"
  service_id?: string;
  vehicle_size?: string;
  override_duration_minutes?: number;
}

/** Shape returned by GET /api/v1/matching */
export interface MatchedDetailer extends DetailerPublicRead {
  estimated_price: number;    // cents — total for all vehicles + addons
  estimated_duration: number; // minutes
  available_slots: TimeSlotRead[];
}

export interface MatchingQueryParams {
  lat: number;
  lng: number;
  date: string;               // "YYYY-MM-DD"
  service_id: string;
  vehicle_sizes: string[];    // e.g. ["small", "medium"]
  addon_ids?: string[];
}

/**
 * GET /api/v1/detailers
 * Listado público de detailers. Sin auth requerido.
 */
export const getDetailers = async (
  params?: DetailersQueryParams,
): Promise<DetailerPublicRead[]> => {
  const response = await apiClient.get("/detailers", { params });
  // El endpoint retorna PaginatedResponse<DetailerPublicRead>
  const data = response.data;
  return data.items ?? data;
};

/**
 * GET /api/v1/detailers/{id}/availability
 * Available time slots for a detailer on a specific date.
 */
export const getDetailerAvailability = async (
  detailerId: string,
  params: AvailabilityQueryParams,
): Promise<TimeSlotRead[]> => {
  const response = await apiClient.get(
    `/detailers/${detailerId}/availability`,
    { params },
  );
  return response.data;
};

/**
 * GET /api/v1/matching
 * Smart matching — returns compatible detailers with price, duration & slots.
 */
export const getMatching = async (
  params: MatchingQueryParams,
): Promise<MatchedDetailer[]> => {
  const response = await apiClient.get("/matching", {
    params: {
      lat: params.lat,
      lng: params.lng,
      date: params.date,
      service_id: params.service_id,
      vehicle_sizes: params.vehicle_sizes.join(","),
      addon_ids: params.addon_ids?.join(",") ?? "",
    },
  });
  return response.data;
};

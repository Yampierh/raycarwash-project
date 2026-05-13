import { apiClient } from "./client";

export type TimeSlot = {
  start_time: string;
  end_time: string;
  is_available: boolean;
};

export type MatchingResult = {
  user_id: string;
  full_name: string;
  bio?: string | null;
  years_of_experience?: number | null;
  service_radius_miles: number;
  is_accepting_bookings: boolean;
  average_rating?: number | null;
  total_reviews: number;
  distance_miles?: number | null;
  estimated_price: number;
  estimated_duration: number;
  available_slots: TimeSlot[];
};

export type FindMatchesParams = {
  lat: number;
  lng: number;
  date: string; // YYYY-MM-DD
  service_id: string;
  vehicle_sizes: string; // comma separated
  addon_ids?: string;
  radius_miles?: number;
};

export async function findMatches(params: FindMatchesParams) {
  const res = await apiClient.get<MatchingResult[]>("/matching", { params });
  return res.data;
}

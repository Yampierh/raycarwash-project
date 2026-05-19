import { apiClient } from "./client";

export type Review = {
  id: string;
  appointment_id: string;
  reviewer_id: string;
  detailer_id: string;
  rating: number;
  comment?: string | null;
  created_at: string;
};

export async function createReview(body: {
  appointment_id: string;
  rating: number;
  comment?: string;
}) {
  const res = await apiClient.post<Review>("/reviews", body);
  return res.data;
}

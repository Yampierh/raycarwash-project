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

export type ReviewsPage = {
  items: Review[];
  total: number;
  page: number;
  per_page: number;
  average_rating: number | null;
};

export async function getDetailerReviews(
  detailerId: string,
  params?: { page?: number; per_page?: number }
): Promise<ReviewsPage> {
  const res = await apiClient.get<ReviewsPage>(`/reviews/detailer/${detailerId}`, {
    params,
  });
  return res.data;
}

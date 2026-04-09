import { apiClient } from "./api";

export interface ReviewCreate {
  appointment_id: string;
  rating: number;
  comment?: string;
}

export interface ReviewRead {
  id: string;
  appointment_id: string;
  reviewer_id: string;
  detailer_id: string;
  rating: number;
  comment: string | null;
  created_at: string;
}

export interface PaginatedReviews {
  items: ReviewRead[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/**
 * POST /api/v1/reviews
 * Submit a review for a completed appointment.
 * Only the client who had the appointment can review.
 */
export const createReview = async (
  appointmentId: string,
  rating: number,
  comment?: string
): Promise<ReviewRead> => {
  const response = await apiClient.post<ReviewRead>("/reviews", {
    appointment_id: appointmentId,
    rating,
    comment,
  });
  return response.data;
};

/**
 * GET /api/v1/reviews/detailer/{detailerId}
 * Get paginated reviews for a detailer.
 * Public endpoint (no auth required).
 */
export const getDetailerReviews = async (
  detailerId: string,
  page = 1,
  pageSize = 20
): Promise<PaginatedReviews> => {
  const response = await apiClient.get<PaginatedReviews>(`/reviews/detailer/${detailerId}`, {
    params: { page, page_size: pageSize },
  });
  return response.data;
};

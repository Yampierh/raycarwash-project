import { apiClient } from "./api";

/** Per-vehicle item in a multi-vehicle appointment */
export interface AppointmentVehicleItem {
  vehicle_id: string;
  service_id: string;
  addon_ids?: string[];
}

/** Sprint 5 multi-vehicle appointment payload */
export interface AppointmentCreatePayload {
  detailer_id: string;
  scheduled_time: string;      // ISO 8601 UTC
  service_address: string;
  service_latitude: number;
  service_longitude: number;
  vehicles: AppointmentVehicleItem[];
  client_notes?: string;
}

/** Legacy single-vehicle payload (backward compat) */
export interface AppointmentCreateLegacy {
  detailer_id: string;
  vehicle_id: string;
  service_id: string;
  scheduled_time: string;
  service_address: string;
  service_latitude: number;
  service_longitude: number;
  client_notes?: string;
}

export interface AppointmentStatusPatch {
  status: string;
  detailer_notes?: string;
  actual_price?: number;       // cents, required when status = "completed"
}

export interface PaginatedAppointments {
  items: any[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/**
 * POST /api/v1/appointments
 * Creates a multi-vehicle appointment (Sprint 5).
 */
export const createAppointment = async (
  payload: AppointmentCreatePayload,
): Promise<any> => {
  const response = await apiClient.post("/appointments", payload);
  return response.data;
};

/**
 * GET /api/v1/appointments/mine
 * Returns the authenticated user's appointments (paginated).
 */
export const getMyAppointments = async (
  page = 1,
  page_size = 20,
): Promise<PaginatedAppointments> => {
  const response = await apiClient.get("/appointments/mine", {
    params: { page, page_size },
  });
  return response.data;
};

/**
 * GET /api/v1/appointments/{id}
 */
export const getAppointmentById = async (id: string): Promise<any> => {
  const response = await apiClient.get(`/appointments/${id}`);
  return response.data;
};

/**
 * PATCH /api/v1/appointments/{id}/status
 * Client can cancel (cancelled_by_client). Detailer confirms, starts, completes.
 */
export const patchAppointmentStatus = async (
  id: string,
  payload: AppointmentStatusPatch,
): Promise<any> => {
  const response = await apiClient.patch(`/appointments/${id}/status`, payload);
  return response.data;
};

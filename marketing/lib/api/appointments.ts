import { apiClient } from "./client";

export type AppointmentStatus =
  | "pending"
  | "confirmed"
  | "arrived"
  | "in_progress"
  | "completed"
  | "cancelled_by_client"
  | "cancelled_by_detailer"
  | "no_show"
  | "searching"
  | "no_detailer_found";

export type AppointmentVehicleRead = {
  id: string;
  vehicle_id: string;
  vehicle_size: string;
  price_cents: number;
  duration_minutes: number;
  vehicle?: {
    make: string;
    model: string;
    body_class?: string | null;
    color: string;
  } | null;
};

export type Appointment = {
  id: string;
  status: AppointmentStatus;
  scheduled_time: string;
  estimated_end_time: string | null;
  service_address: string | null;
  client_notes: string | null;
  detailer_notes: string | null;
  estimated_price_cents: number;
  actual_price_cents: number | null;
  arrived_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  client_id: string;
  detailer_id: string;
  client?: { full_name: string; phone?: string | null } | null;
  detailer?: { full_name: string } | null;
  vehicles: AppointmentVehicleRead[];
  created_at: string;
  updated_at: string;
};

export type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  per_page: number;
};

export async function listMyAppointments(params?: {
  page?: number;
  per_page?: number;
  status?: AppointmentStatus;
}) {
  const res = await apiClient.get<Paginated<Appointment> | Appointment[]>(
    "/appointments/mine",
    { params }
  );
  // Backend returns either a list or a paginated envelope depending on version.
  return res.data;
}

export async function getAppointment(id: string) {
  const res = await apiClient.get<Appointment>(`/appointments/${id}`);
  return res.data;
}

export async function updateAppointmentStatus(
  id: string,
  status: AppointmentStatus,
  detailer_notes?: string
) {
  const res = await apiClient.patch<Appointment>(
    `/appointments/${id}/status`,
    { status, detailer_notes }
  );
  return res.data;
}

// --- Create ---

export type AppointmentVehicleCreate = {
  vehicle_id: string;
  service_id: string;
  addon_ids?: string[];
};

export type AppointmentCreate = {
  detailer_id: string;
  scheduled_time: string; // ISO 8601 with timezone, must be future and UTC
  service_address: string;
  service_latitude?: number | null;
  service_longitude?: number | null;
  client_notes?: string | null;
  vehicles: AppointmentVehicleCreate[];
};

export async function createAppointment(body: AppointmentCreate) {
  const res = await apiClient.post<Appointment>("/appointments", body);
  return res.data;
}

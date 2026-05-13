import useSWR from "swr";
import { listMyAppointments } from "@/lib/api/appointments";

export function useAppointments() {
  return useSWR("/appointments/mine", () => listMyAppointments());
}

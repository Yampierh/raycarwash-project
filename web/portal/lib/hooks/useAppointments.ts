import useSWR from "swr";
import { listMyAppointments } from "@/lib/api/appointments";
import { useAuthStore } from "@/lib/store/auth";

/**
 * Lists the authenticated user's appointments, disambiguating client- vs
 * detailer-side bookings for dual-role users via `?as=`.
 */
export function useAppointments() {
  const activeRole = useAuthStore((s) => s.activeRole);
  const as: "client" | "detailer" | undefined =
    activeRole === "client" || activeRole === "detailer" ? activeRole : undefined;

  return useSWR(["/appointments/mine", as], () =>
    listMyAppointments(as ? { as } : undefined)
  );
}

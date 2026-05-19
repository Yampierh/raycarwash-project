import clsx from "clsx";
import type { AppointmentStatus } from "@/lib/api/appointments";

const STYLES: Record<AppointmentStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  searching: "bg-amber-100 text-amber-800",
  confirmed: "bg-blue-100 text-blue-800",
  arrived: "bg-violet-100 text-violet-800",
  in_progress: "bg-violet-100 text-violet-800",
  completed: "bg-emerald-100 text-emerald-800",
  cancelled_by_client: "bg-zinc-100 text-zinc-700",
  cancelled_by_detailer: "bg-zinc-100 text-zinc-700",
  no_show: "bg-red-100 text-red-700",
  no_detailer_found: "bg-red-100 text-red-700",
};

export function AppointmentStatusBadge({
  status,
  label,
}: {
  status: AppointmentStatus;
  label: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        STYLES[status] ?? "bg-zinc-100 text-zinc-700"
      )}
    >
      {label}
    </span>
  );
}

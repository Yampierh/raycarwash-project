"use client";

import { useTranslations, useLocale } from "next-intl";
import useSWR from "swr";
import { Link } from "@/i18n/navigation";
import { listMyAppointments, type Appointment, type AppointmentStatus } from "@/lib/api/appointments";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { AppointmentStatusBadge } from "@/components/app/AppointmentStatusBadge";
import { Calendar, MapPin, User, ArrowRight, Loader2 } from "lucide-react";

const UPCOMING_STATUSES = new Set<AppointmentStatus>([
  "pending",
  "confirmed",
  "arrived",
  "in_progress",
]);

function groupByDay(
  appointments: Appointment[],
  locale: string
): { label: string; date: string; items: Appointment[] }[] {
  const map = new Map<string, Appointment[]>();
  for (const a of appointments) {
    const day = new Date(a.scheduled_time).toLocaleDateString(locale, {
      weekday: "long",
      month: "short",
      day: "numeric",
    });
    if (!map.has(day)) map.set(day, []);
    map.get(day)!.push(a);
  }
  return Array.from(map.entries()).map(([label, items]) => ({
    label,
    date: items[0].scheduled_time,
    items,
  }));
}

export default function DetailerSchedulePage() {
  const t = useTranslations("detailerSchedule");
  const locale = useLocale();
  const { data, error, isLoading } = useSWR(
    "/appointments/mine/detailer",
    () => listMyAppointments({ as: "detailer", per_page: 50 })
  );

  const timeFormatter = new Intl.DateTimeFormat(locale, {
    timeStyle: "short",
  });

  const all: Appointment[] = Array.isArray(data)
    ? data
    : (data as { items?: Appointment[] })?.items ?? [];

  const upcoming = all
    .filter((a) => UPCOMING_STATUSES.has(a.status))
    .sort(
      (a, b) =>
        new Date(a.scheduled_time).getTime() - new Date(b.scheduled_time).getTime()
    );

  const groups = groupByDay(upcoming, locale);

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <PageHeader title={t("title")} sub={t("sub")} />

      {isLoading && (
        <div className="flex justify-center py-16">
          <Loader2 className="size-6 animate-spin text-zinc-400" />
        </div>
      )}

      {error && !isLoading && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {t("loadError")}
        </div>
      )}

      {!isLoading && !error && groups.length === 0 && (
        <EmptyState
          icon={<Calendar className="size-5" />}
          title={t("emptyTitle")}
          body={t("emptyBody")}
        />
      )}

      {!isLoading && groups.length > 0 && (
        <div className="flex flex-col gap-8">
          {groups.map((group) => (
            <div key={group.label}>
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-zinc-500">
                {group.label}
              </h2>
              <ul className="flex flex-col gap-3">
                {group.items.map((job) => (
                  <li key={job.id}>
                    <Link
                      href={`/detailer/jobs/${job.id}`}
                      className="flex items-start justify-between gap-4 rounded-2xl border border-zinc-200 bg-white p-5 transition hover:border-zinc-300 hover:shadow-sm"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-sm font-semibold text-zinc-900">
                            {timeFormatter.format(new Date(job.scheduled_time))}
                          </span>
                          <AppointmentStatusBadge
                            status={job.status}
                            label={t(`status.${job.status}` as const, {
                              defaultMessage: job.status,
                            })}
                          />
                        </div>
                        <p className="mt-2 flex items-center gap-1.5 text-sm text-zinc-700">
                          <User className="size-3.5 shrink-0 text-zinc-400" />
                          {job.client?.full_name ?? t("unknownClient")}
                        </p>
                        {job.service_address && (
                          <p className="mt-1 flex items-center gap-1.5 truncate text-xs text-zinc-500">
                            <MapPin className="size-3.5 shrink-0" />
                            {job.service_address}
                          </p>
                        )}
                        {job.vehicles.length > 0 && (
                          <p className="mt-1 text-xs text-zinc-400">
                            {job.vehicles
                              .map((v) =>
                                v.vehicle
                                  ? `${v.vehicle.make} ${v.vehicle.model}`
                                  : t("vehicle")
                              )
                              .join(", ")}
                          </p>
                        )}
                      </div>
                      <div className="flex shrink-0 items-center gap-3">
                        <div className="text-right">
                          <p className="font-display text-lg font-bold text-zinc-900">
                            ${(job.estimated_price_cents / 100).toFixed(2)}
                          </p>
                          {job.vehicles.length > 0 && (
                            <p className="text-xs text-zinc-400">
                              {job.vehicles.reduce((s, v) => s + v.duration_minutes, 0)} min
                            </p>
                          )}
                        </div>
                        <ArrowRight className="size-4 text-zinc-400" />
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

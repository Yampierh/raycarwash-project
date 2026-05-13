"use client";

import { useTranslations, useLocale } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { useAppointments } from "@/lib/hooks/useAppointments";
import {
  type Appointment,
  type AppointmentStatus,
} from "@/lib/api/appointments";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { AppointmentStatusBadge } from "@/components/app/AppointmentStatusBadge";
import { Button } from "@/components/forms/Button";
import { Calendar, MapPin, Loader2, Car, Plus } from "lucide-react";

function flatten(data: unknown): Appointment[] {
  if (!data) return [];
  if (Array.isArray(data)) return data as Appointment[];
  const items = (data as { items?: Appointment[] }).items;
  return items ?? [];
}

export default function AppointmentsPage() {
  const t = useTranslations("clientAppointments");
  const locale = useLocale();
  const router = useRouter();
  const { data, error, isLoading } = useAppointments();

  const items = flatten(data);
  const dateFormatter = new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <PageHeader
        title={t("title")}
        sub={t("sub")}
        action={
          <Button onClick={() => router.push("/client/book")}>
            <Plus className="size-4" /> {t("book")}
          </Button>
        }
      />

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

      {!isLoading && !error && items.length === 0 && (
        <EmptyState
          icon={<Calendar className="size-5" />}
          title={t("emptyTitle")}
          body={t("emptyBody")}
          action={
            <Button onClick={() => router.push("/client/book")}>
              <Plus className="size-4" /> {t("book")}
            </Button>
          }
        />
      )}

      {items.length > 0 && (
        <ul className="flex flex-col gap-3">
          {items.map((a) => (
            <Link
              href={`/client/appointments/${a.id}`}
              key={a.id}
              className="flex flex-col gap-3 rounded-2xl border border-zinc-200 bg-white p-5 transition hover:border-zinc-300 hover:shadow-sm md:flex-row md:items-center md:justify-between"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <AppointmentStatusBadge
                    status={a.status as AppointmentStatus}
                    label={t(`status.${a.status}` as const, {
                      defaultMessage: a.status,
                    })}
                  />
                  <span className="text-xs text-zinc-500">
                    {dateFormatter.format(new Date(a.scheduled_time))}
                  </span>
                </div>
                <h3 className="mt-2 text-sm font-semibold text-zinc-900">
                  {a.detailer?.full_name ?? t("noDetailerAssigned")}
                </h3>
                {a.service_address && (
                  <p className="mt-1 flex items-center gap-1 truncate text-xs text-zinc-500">
                    <MapPin className="size-3.5" />
                    {a.service_address}
                  </p>
                )}
                {a.vehicles.length > 0 && (
                  <p className="mt-1 flex items-center gap-1 text-xs text-zinc-500">
                    <Car className="size-3.5" />
                    {a.vehicles
                      .map((v) =>
                        v.vehicle
                          ? `${v.vehicle.make} ${v.vehicle.model}`
                          : t("vehicle")
                      )
                      .join(", ")}
                  </p>
                )}
              </div>
              <div className="text-right">
                <div className="font-display text-xl font-bold text-zinc-900">
                  ${((a.actual_price_cents ?? a.estimated_price_cents) / 100).toFixed(2)}
                </div>
                <div className="text-[10px] uppercase tracking-wider text-zinc-500">
                  {a.actual_price_cents ? t("final") : t("estimate")}
                </div>
              </div>
            </Link>
          ))}
        </ul>
      )}
    </div>
  );
}

"use client";

import { useTranslations, useLocale } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useVehicles } from "@/lib/hooks/useVehicles";
import { useAppointments } from "@/lib/hooks/useAppointments";
import { useMe } from "@/lib/hooks/useMe";
import type { Appointment } from "@/lib/api/appointments";
import { PageHeader } from "@/components/app/PageHeader";
import { Button } from "@/components/forms/Button";
import { AppointmentStatusBadge } from "@/components/app/AppointmentStatusBadge";
import { Car, Calendar, Sparkles, ArrowRight, MapPin } from "lucide-react";

function flatten(data: unknown): Appointment[] {
  if (!data) return [];
  if (Array.isArray(data)) return data as Appointment[];
  const items = (data as { items?: Appointment[] }).items;
  return items ?? [];
}

const UPCOMING_STATUSES = new Set([
  "pending",
  "confirmed",
  "arrived",
  "in_progress",
  "searching",
]);
const DONE_STATUS = "completed";

export default function ClientHomePage() {
  const t = useTranslations("clientHome");
  const locale = useLocale();
  const { data: me } = useMe();
  const { data: vehicles } = useVehicles();
  const { data: appointmentData } = useAppointments();

  const appointments = flatten(appointmentData);
  const upcoming = appointments
    .filter((a) => UPCOMING_STATUSES.has(a.status))
    .sort(
      (a, b) =>
        new Date(a.scheduled_time).getTime() -
        new Date(b.scheduled_time).getTime()
    );
  const completedCount = appointments.filter((a) => a.status === DONE_STATUS)
    .length;
  const nextAppointment = upcoming[0];

  const dateFormatter = new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  const firstName = me?.full_name?.split(" ")[0] ?? null;

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <PageHeader
        title={firstName ? t("greeting", { name: firstName }) : t("title")}
        sub={t("sub")}
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat
          icon={<Calendar className="size-5" />}
          label={t("stats.upcoming")}
          value={String(upcoming.length)}
        />
        <Stat
          icon={<Car className="size-5" />}
          label={t("stats.vehicles")}
          value={vehicles ? String(vehicles.length) : "—"}
        />
        <Stat
          icon={<Sparkles className="size-5" />}
          label={t("stats.completed")}
          value={String(completedCount)}
        />
      </div>

      {nextAppointment ? (
        <div className="mt-8 rounded-2xl border border-zinc-200 bg-white p-6">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-zinc-900">
              {t("nextAppointment")}
            </h2>
            <AppointmentStatusBadge
              status={nextAppointment.status}
              label={t(`status.${nextAppointment.status}` as const, {
                defaultMessage: nextAppointment.status,
              })}
            />
          </div>
          <p className="mt-3 text-sm text-zinc-700">
            {dateFormatter.format(new Date(nextAppointment.scheduled_time))}
          </p>
          {nextAppointment.detailer?.full_name && (
            <p className="mt-1 text-sm text-zinc-600">
              {t("with")} <span className="font-medium">{nextAppointment.detailer.full_name}</span>
            </p>
          )}
          {nextAppointment.service_address && (
            <p className="mt-1 flex items-center gap-1 text-xs text-zinc-500">
              <MapPin className="size-3.5" />
              {nextAppointment.service_address}
            </p>
          )}
          <div className="mt-5 flex items-center gap-4">
            <Link
              href={`/client/appointments/${nextAppointment.id}`}
              className="inline-flex items-center gap-1 text-sm font-medium text-zinc-900 underline-offset-4 hover:underline"
            >
              {t("viewDetail")}
              <ArrowRight className="size-3.5" />
            </Link>
            <Link
              href="/client/appointments"
              className="text-sm text-zinc-500 hover:text-zinc-900"
            >
              {t("viewAll")}
            </Link>
          </div>
        </div>
      ) : (
        <div className="mt-8 rounded-2xl border border-zinc-200 bg-white p-8 text-center">
          <Sparkles className="mx-auto size-8 text-brand-600" />
          <h2 className="mt-3 text-lg font-semibold text-zinc-900">
            {t("placeholder.title")}
          </h2>
          <p className="mt-2 text-sm text-zinc-600">{t("placeholder.body")}</p>
          <Link
            href="/client/book"
            className="mt-6 inline-flex items-center justify-center gap-2 rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800"
          >
            {t("placeholder.cta")}
          </Link>
        </div>
      )}
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-6">
      <div className="flex items-center justify-between text-zinc-500">
        <span className="text-xs font-medium uppercase tracking-wider">
          {label}
        </span>
        {icon}
      </div>
      <div className="mt-3 font-display text-3xl font-bold text-zinc-900">
        {value}
      </div>
    </div>
  );
}

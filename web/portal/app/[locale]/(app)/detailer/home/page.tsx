"use client";

import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import useSWR from "swr";
import { Link } from "@/i18n/navigation";
import { useDetailerMe } from "@/lib/hooks/useDetailerMe";
import { setAcceptingBookings } from "@/lib/api/detailer";
import {
  listMyAppointments,
  type Appointment,
  type AppointmentStatus,
} from "@/lib/api/appointments";
import { getVerificationStatus } from "@/lib/api/detailer";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { AppointmentStatusBadge } from "@/components/app/AppointmentStatusBadge";
import {
  ListTodo,
  DollarSign,
  AlertCircle,
  Star,
  ArrowRight,
  MapPin,
  Loader2,
} from "lucide-react";
import clsx from "clsx";

function flatten(data: unknown): Appointment[] {
  if (!data) return [];
  if (Array.isArray(data)) return data as Appointment[];
  const items = (data as { items?: Appointment[] }).items;
  return items ?? [];
}

const ACTIVE_STATUSES = new Set<AppointmentStatus>([
  "pending",
  "confirmed",
  "arrived",
  "in_progress",
]);

export default function DetailerHomePage() {
  const t = useTranslations("detailerHome");
  const locale = useLocale();
  const { data: me, isLoading, mutate } = useDetailerMe();
  const { data: jobsRaw } = useSWR("/appointments/mine", () =>
    listMyAppointments({ as: "detailer" })
  );
  const { data: verification } = useSWR(
    "/detailers/verification/status",
    () => getVerificationStatus()
  );
  const [toggling, setToggling] = useState(false);

  const jobs = flatten(jobsRaw)
    .filter((j) => ACTIVE_STATUSES.has(j.status))
    .sort(
      (a, b) =>
        new Date(a.scheduled_time).getTime() -
        new Date(b.scheduled_time).getTime()
    );

  const dateFormatter = new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  async function handleToggleAccepting() {
    if (!me) return;
    setToggling(true);
    try {
      const updated = await setAcceptingBookings(!me.is_accepting_bookings);
      await mutate(updated, false);
    } catch {
      window.alert(t("loadError"));
    } finally {
      setToggling(false);
    }
  }

  const verificationStatus = verification?.verification_status;

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <PageHeader
        title={me?.full_name ? t("greeting", { name: me.full_name.split(" ")[0] }) : t("title")}
        sub={t("sub")}
        action={
          me ? (
            <button
              type="button"
              onClick={handleToggleAccepting}
              disabled={toggling}
              className={clsx(
                "inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium transition disabled:opacity-50",
                me.is_accepting_bookings
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                  : "border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50"
              )}
            >
              <span
                className={clsx(
                  "size-2 rounded-full",
                  me.is_accepting_bookings ? "bg-emerald-500" : "bg-zinc-400"
                )}
              />
              {me.is_accepting_bookings ? t("accepting") : t("paused")}
            </button>
          ) : null
        }
      />

      {verificationStatus === "pending" && (
        <Banner
          color="amber"
          title={t("verifyPending.title")}
          body={t("verifyPending.body")}
        />
      )}
      {verificationStatus === "rejected" && (
        <Banner
          color="red"
          title={t("verifyRejected.title")}
          body={
            verification?.rejection_reason ?? t("verifyRejected.body")
          }
        />
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat
          icon={<ListTodo className="size-5" />}
          label={t("stats.jobs")}
          value={isLoading ? "…" : String(me?.total_services ?? 0)}
        />
        <Stat
          icon={<DollarSign className="size-5" />}
          label={t("stats.earnings")}
          value={
            isLoading
              ? "…"
              : `$${((me?.total_earnings_cents ?? 0) / 100).toFixed(2)}`
          }
        />
        <Stat
          icon={<Star className="size-5" />}
          label={t("stats.rating")}
          value={
            isLoading
              ? "…"
              : me?.average_rating != null
                ? me.average_rating.toFixed(2)
                : t("noRating")
          }
        />
      </div>

      <section className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold text-zinc-900">
            {t("activeJobs")}
          </h2>
          {jobs.length > 0 && (
            <span className="text-xs text-zinc-500">
              {t("countJobs", { count: jobs.length })}
            </span>
          )}
        </div>

        {jobs.length === 0 ? (
          <EmptyState
            icon={<ListTodo className="size-5" />}
            title={t("emptyJobs.title")}
            body={t("emptyJobs.body")}
          />
        ) : (
          <ul className="flex flex-col gap-3">
            {jobs.map((j) => (
              <li key={j.id}>
                <Link
                  href={`/detailer/jobs/${j.id}`}
                  className="flex items-start justify-between gap-4 rounded-2xl border border-zinc-200 bg-white p-5 transition hover:border-zinc-300 hover:shadow-sm"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <AppointmentStatusBadge
                        status={j.status}
                        label={t(`status.${j.status}` as const, {
                          defaultMessage: j.status,
                        })}
                      />
                      <span className="text-xs text-zinc-500">
                        {dateFormatter.format(new Date(j.scheduled_time))}
                      </span>
                    </div>
                    <p className="mt-2 text-sm font-medium text-zinc-900">
                      {j.client?.full_name ?? t("client")}
                    </p>
                    {j.service_address && (
                      <p className="mt-1 flex items-center gap-1 truncate text-xs text-zinc-500">
                        <MapPin className="size-3.5" />
                        {j.service_address}
                      </p>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <div className="text-right">
                      <div className="font-display text-lg font-bold text-zinc-900">
                        ${(j.estimated_price_cents / 100).toFixed(2)}
                      </div>
                    </div>
                    <ArrowRight className="size-4 text-zinc-400" />
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Banner({
  color,
  title,
  body,
}: {
  color: "amber" | "red";
  title: string;
  body: string;
}) {
  const styles =
    color === "amber"
      ? "border-amber-200 bg-amber-50 text-amber-900"
      : "border-red-200 bg-red-50 text-red-900";
  return (
    <div className={clsx("mb-8 flex items-start gap-3 rounded-2xl border p-4", styles)}>
      <AlertCircle className="mt-0.5 size-5 shrink-0" />
      <div>
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="mt-1 text-xs">{body}</p>
      </div>
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

"use client";

import { useTranslations, useLocale } from "next-intl";
import useSWR from "swr";
import { useDetailerMe } from "@/lib/hooks/useDetailerMe";
import {
  listMyAppointments,
  type Appointment,
} from "@/lib/api/appointments";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { DollarSign, Calendar, Loader2 } from "lucide-react";

function flatten(data: unknown): Appointment[] {
  if (!data) return [];
  if (Array.isArray(data)) return data as Appointment[];
  const items = (data as { items?: Appointment[] }).items;
  return items ?? [];
}

export default function DetailerEarningsPage() {
  const t = useTranslations("detailerEarnings");
  const locale = useLocale();
  const { data: me } = useDetailerMe();
  const { data: jobsRaw, isLoading } = useSWR(
    "/appointments/mine?completed",
    () => listMyAppointments({ status: "completed", per_page: 50 })
  );

  const completed = flatten(jobsRaw).filter((a) => a.status === "completed");
  const totalCents = me?.total_earnings_cents ?? 0;

  const dateFormatter = new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
  });

  const lastDays = completed
    .slice()
    .sort(
      (a, b) =>
        new Date(b.completed_at ?? b.scheduled_time).getTime() -
        new Date(a.completed_at ?? a.scheduled_time).getTime()
    );

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <PageHeader title={t("title")} sub={t("sub")} />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatBig
          icon={<DollarSign className="size-5" />}
          label={t("stats.total")}
          value={`$${(totalCents / 100).toFixed(2)}`}
        />
        <StatBig
          icon={<Calendar className="size-5" />}
          label={t("stats.jobs")}
          value={String(completed.length)}
        />
        <StatBig
          icon={<DollarSign className="size-5" />}
          label={t("stats.average")}
          value={
            completed.length === 0
              ? "—"
              : `$${(totalCents / completed.length / 100).toFixed(2)}`
          }
        />
      </div>

      <section className="mt-10">
        <h2 className="mb-3 text-base font-semibold text-zinc-900">
          {t("history")}
        </h2>

        {isLoading && (
          <div className="flex justify-center py-12">
            <Loader2 className="size-6 animate-spin text-zinc-400" />
          </div>
        )}

        {!isLoading && completed.length === 0 && (
          <EmptyState
            icon={<DollarSign className="size-5" />}
            title={t("emptyTitle")}
            body={t("emptyBody")}
          />
        )}

        {completed.length > 0 && (
          <ul className="divide-y divide-zinc-100 overflow-hidden rounded-2xl border border-zinc-200 bg-white">
            {lastDays.map((j) => (
              <li
                key={j.id}
                className="flex items-center justify-between gap-4 px-5 py-4"
              >
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-zinc-900">
                    {j.client?.full_name ?? t("client")}
                  </div>
                  <div className="mt-1 text-xs text-zinc-500">
                    {dateFormatter.format(
                      new Date(j.completed_at ?? j.scheduled_time)
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-display text-base font-bold text-zinc-900">
                    $
                    {(
                      (j.actual_price_cents ?? j.estimated_price_cents) / 100
                    ).toFixed(2)}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function StatBig({
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

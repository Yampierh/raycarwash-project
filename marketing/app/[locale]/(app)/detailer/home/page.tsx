"use client";

import { useTranslations } from "next-intl";
import useSWR from "swr";
import { getMyDetailer, type DetailerMe } from "@/lib/api/detailer";
import { ListTodo, DollarSign, Star, AlertCircle } from "lucide-react";

export default function DetailerHomePage() {
  const t = useTranslations("detailerHome");
  const { data, error, isLoading } = useSWR<DetailerMe>(
    "/detailers/me",
    () => getMyDetailer()
  );

  const verificationStatus = data?.verification_status;

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold tracking-tight text-zinc-900">
          {t("title")}
        </h1>
        <p className="mt-2 text-sm text-zinc-600">{t("sub")}</p>
      </header>

      {verificationStatus === "pending" && (
        <div className="mb-8 flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <AlertCircle className="mt-0.5 size-5 shrink-0 text-amber-600" />
          <div>
            <h3 className="text-sm font-semibold text-amber-900">
              {t("verifyPending.title")}
            </h3>
            <p className="mt-1 text-xs text-amber-700">
              {t("verifyPending.body")}
            </p>
          </div>
        </div>
      )}

      {verificationStatus === "rejected" && (
        <div className="mb-8 flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4">
          <AlertCircle className="mt-0.5 size-5 shrink-0 text-red-600" />
          <div>
            <h3 className="text-sm font-semibold text-red-900">
              {t("verifyRejected.title")}
            </h3>
            <p className="mt-1 text-xs text-red-700">
              {t("verifyRejected.body")}
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat
          icon={<ListTodo className="size-5" />}
          label={t("stats.jobs")}
          value={isLoading ? "…" : String(data?.total_services ?? 0)}
        />
        <Stat
          icon={<DollarSign className="size-5" />}
          label={t("stats.earnings")}
          value={
            isLoading
              ? "…"
              : `$${((data?.total_earnings_cents ?? 0) / 100).toFixed(2)}`
          }
        />
        <Stat
          icon={<Star className="size-5" />}
          label={t("stats.accepting")}
          value={
            isLoading
              ? "…"
              : data?.is_accepting_bookings
                ? t("yes")
                : t("no")
          }
        />
      </div>

      <div className="mt-8 rounded-2xl border border-zinc-200 bg-white p-8 text-center">
        <ListTodo className="mx-auto size-8 text-brand-600" />
        <h2 className="mt-3 text-lg font-semibold text-zinc-900">
          {t("placeholder.title")}
        </h2>
        <p className="mt-2 text-sm text-zinc-600">{t("placeholder.body")}</p>
      </div>

      {error ? (
        <p className="mt-4 text-center text-xs text-red-600">{t("loadError")}</p>
      ) : null}
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

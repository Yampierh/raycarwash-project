"use client";

import { useTranslations } from "next-intl";
import { Car, Calendar, Sparkles } from "lucide-react";

export default function ClientHomePage() {
  const t = useTranslations("clientHome");

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold tracking-tight text-zinc-900">
          {t("title")}
        </h1>
        <p className="mt-2 text-sm text-zinc-600">{t("sub")}</p>
      </header>

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat icon={<Calendar className="size-5" />} label={t("stats.upcoming")} value="—" />
        <Stat icon={<Car className="size-5" />} label={t("stats.vehicles")} value="—" />
        <Stat icon={<Sparkles className="size-5" />} label={t("stats.completed")} value="—" />
      </div>

      <div className="mt-8 rounded-2xl border border-zinc-200 bg-white p-8 text-center">
        <Sparkles className="mx-auto size-8 text-brand-600" />
        <h2 className="mt-3 text-lg font-semibold text-zinc-900">
          {t("placeholder.title")}
        </h2>
        <p className="mt-2 text-sm text-zinc-600">
          {t("placeholder.body")}
        </p>
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

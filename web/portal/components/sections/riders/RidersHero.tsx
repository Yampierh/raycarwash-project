"use client";

import { useTranslations } from "next-intl";
import { PhoneMock } from "../PhoneMock";
import { Clock, ShieldCheck, Wallet, Apple, Play, Star } from "lucide-react";

const QUICK_ICONS = [Clock, ShieldCheck, Wallet];

export default function RidersHero() {
  const t = useTranslations("ridersPage.hero");
  const quickRows = t.raw("quickRows") as { t: string; b: string }[];

  const appStore = process.env.NEXT_PUBLIC_APPSTORE_URL ?? "#";
  const playStore = process.env.NEXT_PUBLIC_PLAYSTORE_URL ?? "#";

  return (
    <section
      id="top"
      className="relative overflow-hidden border-b border-ink-150 bg-gradient-to-b from-white to-ink-50"
    >
      <div className="hero-grid" aria-hidden />

      <div className="mx-auto grid max-w-6xl gap-12 px-6 py-20 md:grid-cols-[1.05fr_0.95fr] md:items-center md:py-28">
        <div>
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-ink-200 bg-white px-3 py-1 text-xs font-medium text-ink-600 shadow-sm">
            <span className="size-1.5 rounded-full bg-brand-500" />
            {t("kicker")}
          </span>
          <h1 className="mt-6 font-display text-5xl font-bold leading-[1.05] tracking-tight text-ink-900 md:text-6xl">
            {t("h1")}
            <br />
            <span className="bg-gradient-to-br from-brand-500 to-brand-700 bg-clip-text text-transparent">
              {t("h1Accent")}
            </span>
          </h1>
          <p className="mt-6 max-w-lg text-lg leading-relaxed text-ink-600">
            {t("sub")}
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a
              href={appStore}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-ink-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-ink-800"
            >
              <Apple className="size-4" />
              {t("ctaIos")}
            </a>
            <a
              href={playStore}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg border border-ink-200 bg-white px-5 py-3 text-sm font-semibold text-ink-900 shadow-sm transition hover:bg-ink-50"
            >
              <Play className="size-4" />
              {t("ctaAndroid")}
            </a>
          </div>
          <ul className="mt-10 space-y-3">
            {quickRows.map((row, i) => {
              const Icon = QUICK_ICONS[i];
              return (
                <li key={row.t} className="flex items-start gap-3">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700">
                    <Icon className="size-4" strokeWidth={2} />
                  </span>
                  <div>
                    <div className="text-sm font-semibold text-ink-900">
                      {row.t}
                    </div>
                    <div className="text-sm text-ink-500">{row.b}</div>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="relative">
          <div className="absolute -inset-8 -z-10 rounded-full bg-gradient-to-br from-brand-100 via-transparent to-transparent opacity-60 blur-3xl" />
          <div className="relative flex justify-center gap-4">
            <div className="hidden translate-y-6 scale-90 opacity-70 sm:block">
              <CalendarPhone />
            </div>
            <PhoneMock variant="client" step={1} />
          </div>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-2 text-xs text-ink-500">
            <Star className="size-3.5 fill-amber-400 text-amber-400" />
            <span className="font-semibold text-ink-900">{t("credit")}</span>
          </div>
        </div>
      </div>
    </section>
  );
}

function CalendarPhone() {
  return (
    <div className="relative aspect-[9/19] w-[180px] overflow-hidden rounded-[2rem] border-[8px] border-ink-900 bg-ink-900 shadow-phone">
      <div className="absolute left-1/2 top-1.5 z-20 h-4 w-20 -translate-x-1/2 rounded-b-xl bg-ink-900" />
      <div className="absolute inset-0 bg-gradient-to-br from-ink-50 via-white to-ink-50 p-3">
        <div className="mt-6 text-[9px] font-semibold uppercase tracking-wider text-ink-500">
          Step 1 of 3
        </div>
        <div className="mt-1 font-display text-base font-bold text-ink-900">
          When?
        </div>
        <div className="mt-3 rounded-lg bg-white p-2 shadow-sm">
          <div className="text-center text-[10px] font-semibold text-ink-700">
            June 2026
          </div>
          <div className="mt-1.5 grid grid-cols-7 gap-0.5">
            {Array.from({ length: 30 }).map((_, i) => {
              const d = i + 1;
              const sel = d === 14;
              const dis = d < 5 || d === 22;
              return (
                <div
                  key={i}
                  className={`flex aspect-square items-center justify-center rounded text-[8px] font-semibold ${
                    sel
                      ? "bg-brand-600 text-white"
                      : dis
                        ? "text-ink-300"
                        : "text-ink-700 hover:bg-ink-100"
                  }`}
                >
                  {d}
                </div>
              );
            })}
          </div>
        </div>
        <div className="mt-3 grid grid-cols-4 gap-1">
          {["9:00", "11:30", "2:00", "4:30"].map((s, i) => (
            <div
              key={s}
              className={`rounded py-1 text-center text-[9px] font-semibold ${
                i === 1
                  ? "bg-brand-600 text-white"
                  : i === 3
                    ? "bg-ink-200 text-ink-400 line-through"
                    : "bg-white text-ink-700 shadow-sm"
              }`}
            >
              {s}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

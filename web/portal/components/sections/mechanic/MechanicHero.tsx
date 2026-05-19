"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  ArrowRight,
  Check,
  Wrench,
  Truck,
  ShieldCheck,
  BatteryCharging,
  Activity,
  Clock,
} from "lucide-react";

export default function MechanicHero() {
  const t = useTranslations("mechanicPage.hero");
  const bullets = t.raw("bullets") as string[];
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setSubmitted(true);
  }

  return (
    <section className="relative overflow-hidden border-b border-ink-150 bg-gradient-to-b from-white to-ink-50">
      <div className="hero-grid" aria-hidden />
      <div className="mx-auto grid max-w-6xl gap-12 px-6 py-20 md:grid-cols-[1.1fr_0.9fr] md:items-center md:py-28">
        <div>
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700 shadow-sm">
            <span className="size-1.5 animate-pulse rounded-full bg-amber-500" />
            {t("badge")}
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

          {submitted ? (
            <div className="mt-8 inline-flex items-center gap-2 rounded-xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700">
              <Check className="size-4" /> {t("thanks")}
            </div>
          ) : (
            <form
              onSubmit={submit}
              className="mt-8 flex flex-wrap items-center gap-2"
            >
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t("emailPlaceholder")}
                className="min-w-0 flex-1 rounded-lg border border-ink-200 bg-white px-4 py-3 text-sm text-ink-900 outline-none transition placeholder:text-ink-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
              <button
                type="submit"
                className="inline-flex items-center gap-2 rounded-lg bg-ink-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-ink-800"
              >
                {t("submit")}
                <ArrowRight className="size-4" />
              </button>
            </form>
          )}
          <p className="mt-3 text-xs text-ink-500">{t("meta")}</p>

          <div className="mt-8 flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-700">
            {bullets.map((b) => (
              <span key={b} className="inline-flex items-center gap-1.5">
                <Check className="size-3 text-brand-600" strokeWidth={3} />
                {b}
              </span>
            ))}
          </div>
        </div>

        <div className="relative">
          <div className="absolute -inset-8 -z-10 rounded-full bg-gradient-to-br from-brand-100 via-transparent to-transparent opacity-60 blur-3xl" />
          <ToolboxArt />
        </div>
      </div>
    </section>
  );
}

function ToolboxArt() {
  const tiles = [
    { Ic: Truck, l: "Service van", big: true },
    { Ic: Wrench, l: "Tools" },
    { Ic: Clock, l: "~30 min" },
    { Ic: ShieldCheck, l: "Insured" },
    { Ic: Activity, l: "Diagnostics" },
    { Ic: BatteryCharging, l: "Battery" },
  ];
  return (
    <div className="grid grid-cols-3 gap-3 text-brand-700">
      {tiles.map((t, i) => (
        <div
          key={t.l}
          className={`${
            t.big ? "col-span-2 row-span-2" : ""
          } group flex flex-col items-center justify-center rounded-2xl border border-ink-150 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md`}
          style={{ animationDelay: `${i * 60}ms` }}
        >
          <t.Ic className={`text-brand-600 ${t.big ? "size-14" : "size-7"}`} />
          <div className="mt-3 text-center text-xs font-semibold text-ink-700">
            {t.l}
          </div>
        </div>
      ))}
    </div>
  );
}

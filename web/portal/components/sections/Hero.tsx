"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useAudienceStore } from "@/lib/store/audience";
import { PhoneMock } from "./PhoneMock";
import {
  ShieldCheck,
  Wallet,
  MapPin,
  Calendar,
  UserCheck,
  Apple,
  Play,
  ArrowRight,
} from "lucide-react";

const CLIENT_ICONS = [ShieldCheck, Wallet, MapPin];
const DETAILER_ICONS = [Calendar, Wallet, UserCheck];

export default function Hero() {
  const t = useTranslations("hero");
  const audience = useAudienceStore((s) => s.audience);
  const [step, setStep] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setStep((s) => (s + 1) % 4), 3200);
    return () => clearInterval(id);
  }, []);

  const isClient = audience === "client";
  const stepsRaw = t.raw(isClient ? "stepsClient" : "stepsDetailer") as string[];
  const bullets = t.raw(
    isClient ? "bulletsClient" : "bulletsDetailer",
  ) as string[];
  const icons = isClient ? CLIENT_ICONS : DETAILER_ICONS;

  const appStore = process.env.NEXT_PUBLIC_APPSTORE_URL ?? "#";
  const playStore = process.env.NEXT_PUBLIC_PLAYSTORE_URL ?? "#";

  return (
    <section
      id="top"
      className="relative overflow-hidden border-b border-ink-150 bg-gradient-to-b from-white to-ink-50"
    >
      <div className="hero-grid" aria-hidden />

      <div className="mx-auto grid max-w-6xl gap-12 px-6 py-20 md:grid-cols-2 md:items-center md:py-28">
        <div className="flex flex-col">
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-ink-200 bg-white px-3 py-1 text-xs font-medium text-ink-600 shadow-sm">
            <span className="size-1.5 rounded-full bg-brand-500" />
            {t("kicker")}
          </span>

          <h1 className="mt-6 font-display text-5xl font-bold leading-[1.05] tracking-tight text-ink-900 md:text-6xl">
            {isClient ? t("h1Client") : t("h1Detailer")}
            <br />
            <span className="bg-gradient-to-br from-brand-500 to-brand-700 bg-clip-text text-transparent">
              {isClient ? t("h1ClientAccent") : t("h1DetailerAccent")}
            </span>
          </h1>

          <p className="mt-6 max-w-lg text-lg leading-relaxed text-ink-600">
            {isClient ? t("subClient") : t("subDetailer")}
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            {isClient ? (
              <>
                <a
                  href={appStore}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-ink-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-ink-800"
                >
                  <Apple className="size-4" />
                  {t("downloadIos")}
                </a>
                <a
                  href={playStore}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-ink-200 bg-white px-5 py-3 text-sm font-semibold text-ink-900 shadow-sm transition hover:bg-ink-50"
                >
                  <Play className="size-4" />
                  {t("downloadAndroid")}
                </a>
              </>
            ) : (
              <>
                <a
                  href="/detailers#apply"
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700"
                >
                  {t("ctaDetailerApply")}
                  <ArrowRight className="size-4" />
                </a>
                <a
                  href="/detailers#earnings"
                  className="inline-flex items-center justify-center rounded-lg border border-ink-200 bg-white px-5 py-3 text-sm font-semibold text-ink-900 shadow-sm transition hover:bg-ink-50"
                >
                  {t("ctaDetailerEarnings")}
                </a>
              </>
            )}
          </div>

          <ul className="mt-10 flex flex-col gap-3 text-sm text-ink-700">
            {bullets.map((b, i) => {
              const Icon = icons[i % icons.length];
              return (
                <li key={b} className="flex items-center gap-3">
                  <span className="flex size-7 items-center justify-center rounded-full bg-brand-50 text-brand-600">
                    <Icon className="size-3.5" strokeWidth={2.5} />
                  </span>
                  {b}
                </li>
              );
            })}
          </ul>
        </div>

        <div className="relative">
          <div className="absolute -inset-8 -z-10 rounded-full bg-gradient-to-br from-brand-100 via-transparent to-transparent opacity-60 blur-3xl" />
          <PhoneMock variant={audience} step={step} size="lg" />

          <div className="mt-8 flex flex-wrap justify-center gap-2">
            {stepsRaw.map((label, i) => (
              <button
                key={i}
                onClick={() => setStep(i)}
                className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                  step === i
                    ? "border-ink-900 bg-ink-900 text-white"
                    : "border-ink-200 bg-white text-ink-600 hover:border-ink-300 hover:text-ink-900"
                }`}
                aria-label={label}
              >
                <span
                  className={`flex size-5 items-center justify-center rounded-full text-[10px] font-bold ${
                    step === i ? "bg-white/20" : "bg-ink-100 text-ink-700"
                  }`}
                >
                  {i + 1}
                </span>
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

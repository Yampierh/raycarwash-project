"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { PhoneMock } from "../PhoneMock";
import { ArrowRight } from "lucide-react";

type Step = {
  kicker: string;
  title: string;
  body: string;
  tags: string[];
};

export default function BookingJourney() {
  const t = useTranslations("ridersPage.journey");
  const steps = t.raw("steps") as Step[];
  const [step, setStep] = useState(0);

  return (
    <section
      id="how"
      className="border-b border-ink-150 bg-ink-50 py-20 md:py-28"
    >
      <div className="mx-auto max-w-6xl px-6">
        <div className="max-w-2xl">
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
            {t("kicker")}
          </span>
          <h2 className="mt-3 font-display text-4xl font-bold tracking-tight text-ink-900 md:text-5xl">
            {t("h2")}
          </h2>
          <p className="mt-4 text-lg text-ink-600">{t("sub")}</p>
        </div>

        <div className="mt-10 flex flex-wrap gap-2">
          {steps.map((s, i) => (
            <button
              key={i}
              onClick={() => setStep(i)}
              className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition ${
                step === i
                  ? "border-ink-900 bg-ink-900 text-white"
                  : "border-ink-200 bg-white text-ink-700 hover:border-ink-300"
              }`}
            >
              <span
                className={`font-mono text-xs ${
                  step === i ? "text-white/60" : "text-ink-400"
                }`}
              >
                {String(i + 1).padStart(2, "0")}
              </span>
              <span>{s.title}</span>
            </button>
          ))}
        </div>

        <div className="mt-10 grid gap-12 rounded-3xl border border-ink-150 bg-white p-6 shadow-sm md:grid-cols-[0.85fr_1.15fr] md:items-center md:p-12">
          <div className="flex justify-center">
            <PhoneMock variant="client" step={step} />
          </div>
          <div>
            <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
              {steps[step].kicker}
            </span>
            <h3 className="mt-2 font-display text-3xl font-bold text-ink-900 md:text-4xl">
              {steps[step].title}
            </h3>
            <p className="mt-4 text-lg leading-relaxed text-ink-600">
              {steps[step].body}
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              {steps[step].tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-ink-200 bg-ink-50 px-3 py-1 text-xs font-semibold text-ink-700"
                >
                  {tag}
                </span>
              ))}
            </div>
            <div className="mt-8 flex items-center gap-4">
              <div className="flex gap-1">
                {steps.map((_, i) => (
                  <div
                    key={i}
                    className={`h-1 w-8 rounded-full transition ${
                      i <= step ? "bg-ink-900" : "bg-ink-200"
                    }`}
                  />
                ))}
              </div>
              <button
                onClick={() => setStep((step + 1) % steps.length)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-ink-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-ink-800"
              >
                {step === steps.length - 1 ? t("restart") : t("next")}
                <ArrowRight className="size-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

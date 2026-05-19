"use client";

import { useTranslations } from "next-intl";
import { useAudienceStore } from "@/lib/store/audience";
import { Smartphone, Car, Droplets, Star } from "lucide-react";

const ICONS = [Smartphone, Car, Droplets, Star];

type Step = { title: string; body: string };

export default function HowItWorks() {
  const t = useTranslations("how");
  const audience = useAudienceStore((s) => s.audience);
  const isClient = audience === "client";
  const steps = t.raw(isClient ? "stepsClient" : "stepsDetailer") as Step[];

  return (
    <section id="how" className="border-b border-ink-150 bg-white py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-6">
        <div className="max-w-2xl">
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
            {t("kicker")}
          </span>
          <h2 className="mt-3 font-display text-4xl font-bold tracking-tight text-ink-900 md:text-5xl">
            {isClient ? t("h2Client") : t("h2Detailer")}
          </h2>
          <p className="mt-4 text-lg text-ink-600">
            {isClient ? t("subClient") : t("subDetailer")}
          </p>
        </div>

        <ol className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          {steps.map((step, i) => {
            const Icon = ICONS[i];
            return (
              <li
                key={step.title}
                className="relative flex flex-col rounded-2xl border border-ink-150 bg-white p-6 transition hover:border-brand-200 hover:shadow-md"
              >
                <div className="flex items-center justify-between">
                  <span className="flex size-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                    <Icon className="size-5" strokeWidth={1.75} />
                  </span>
                  <span className="font-mono text-xs font-semibold text-ink-400">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </div>
                <h3 className="mt-5 font-display text-lg font-semibold text-ink-900">
                  {step.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-500">
                  {step.body}
                </p>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

"use client";

import { useTranslations } from "next-intl";
import { ArrowRight, Star } from "lucide-react";

type TrustStripRow = { v: string; l: string };
type PreviewRow = { l: string; v: string };

export default function DetailersHero() {
  const t = useTranslations("detailersPage.hero");
  const trustStrip = t.raw("trustStrip") as TrustStripRow[];
  const previewRows = t.raw("previewRows") as PreviewRow[];
  const previewChips = t.raw("previewChips") as string[];

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
              href="#apply"
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700"
            >
              {t("ctaApply")}
              <ArrowRight className="size-4" />
            </a>
            <a
              href="#earnings"
              className="inline-flex items-center justify-center rounded-lg border border-ink-200 bg-white px-5 py-3 text-sm font-semibold text-ink-900 shadow-sm transition hover:bg-ink-50"
            >
              {t("ctaEarnings")}
            </a>
          </div>
          <dl className="mt-10 grid max-w-md grid-cols-3 gap-4 border-t border-ink-150 pt-6">
            {trustStrip.map((r) => (
              <div key={r.l}>
                <dt className="font-display text-xl font-bold text-ink-900">
                  {r.v}
                </dt>
                <dd className="mt-0.5 text-xs text-ink-500">{r.l}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="relative">
          <div className="absolute -inset-6 -z-10 rounded-3xl bg-gradient-to-br from-brand-100 via-transparent to-transparent opacity-70 blur-2xl" />

          <div className="relative rounded-3xl border border-ink-150 bg-white p-6 shadow-2xl">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-500">
              {t("previewTitle")}
            </div>
            <div className="mt-1 text-xs text-ink-400">{t("previewSub")}</div>

            <div className="mt-5 space-y-3">
              {previewRows.map((row) => (
                <div
                  key={row.l}
                  className="flex items-center justify-between border-b border-ink-100 pb-3 last:border-0 last:pb-0"
                >
                  <span className="text-sm text-ink-600">{row.l}</span>
                  <span className="font-display text-sm font-semibold text-ink-900">
                    {row.v}
                  </span>
                </div>
              ))}
            </div>

            <div className="mt-6 flex items-end gap-1">
              {[40, 65, 30, 80, 55, 90, 70].map((h, i) => (
                <div
                  key={i}
                  className="flex-1 rounded-t bg-gradient-to-t from-brand-400 to-brand-600"
                  style={{ height: `${h * 0.55}px` }}
                />
              ))}
            </div>
            <div className="mt-1 flex justify-between text-[10px] text-ink-400">
              {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => (
                <span key={i}>{d}</span>
              ))}
            </div>
          </div>

          <div className="mt-4 flex flex-wrap justify-center gap-2">
            {previewChips.map((chip, i) => (
              <span
                key={chip}
                className="inline-flex items-center gap-1.5 rounded-full border border-ink-200 bg-white px-3 py-1 text-xs font-semibold text-ink-700 shadow-sm"
              >
                {i === 0 && <Star className="size-3 fill-amber-400 text-amber-400" />}
                {chip}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

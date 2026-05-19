"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

const PLATFORM_FEE = 0.15;

export default function EarningsCalc() {
  const t = useTranslations("detailersPage.calc");
  const [jobs, setJobs] = useState(12);
  const [avg, setAvg] = useState(140);
  const [days, setDays] = useState(5);

  const weekly = jobs * avg;
  const monthly = Math.round(weekly * 4.33);
  const yearly = weekly * 52;
  const net = weekly * (1 - PLATFORM_FEE);
  const perDay = days > 0 ? weekly / days : 0;
  const fmt = (n: number) => "$" + Math.round(n).toLocaleString();

  return (
    <section
      id="earnings"
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

        <div className="mt-12 grid gap-6 md:grid-cols-2">
          <div className="rounded-3xl border border-ink-150 bg-white p-6 shadow-sm md:p-8">
            <Slider
              label={t("jobsLabel")}
              value={`${jobs}`}
              min={3}
              max={25}
              step={1}
              raw={jobs}
              onChange={setJobs}
              minLabel="3"
              maxLabel="25"
            />
            <Slider
              label={t("avgLabel")}
              value={`$${avg}`}
              min={49}
              max={299}
              step={1}
              raw={avg}
              onChange={setAvg}
              minLabel="$49"
              maxLabel="$299"
            />
            <Slider
              label={t("daysLabel")}
              value={t("daysWeek", { n: days })}
              min={1}
              max={7}
              step={1}
              raw={days}
              onChange={setDays}
              minLabel="1"
              maxLabel="7"
            />
            <p className="mt-2 rounded-xl bg-ink-50 p-3 text-xs leading-relaxed text-ink-600">
              <strong className="font-semibold text-ink-900">
                {t("feeLabel")}:
              </strong>{" "}
              {t("fineprint")}
            </p>
          </div>

          <div className="rounded-3xl bg-gradient-to-br from-ink-900 via-ink-900 to-brand-900 p-6 text-white shadow-2xl md:p-8">
            <div className="text-xs font-semibold uppercase tracking-wider text-brand-400">
              {t("bigLbl")}
            </div>
            <div className="mt-1 font-display text-5xl font-bold">
              {fmt(net)}
            </div>
            <div className="mt-1 text-xs text-ink-400">{t("bigSub")}</div>

            <div className="mt-6 grid grid-cols-2 gap-3">
              <Meta label={t("metaGross")} value={fmt(weekly)} />
              <Meta label={t("metaPerDay")} value={fmt(perDay)} />
              <Meta label={t("metaMonthly")} value={fmt(monthly)} />
              <Meta label={t("metaYearly")} value={fmt(yearly)} />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
      <div className="text-[10px] font-medium uppercase tracking-wide text-ink-400">
        {label}
      </div>
      <div className="mt-1 font-display text-lg font-bold text-white">
        {value}
      </div>
    </div>
  );
}

interface SliderProps {
  label: string;
  value: string;
  raw: number;
  min: number;
  max: number;
  step: number;
  minLabel: string;
  maxLabel: string;
  onChange: (n: number) => void;
}

function Slider({
  label,
  value,
  raw,
  min,
  max,
  step,
  minLabel,
  maxLabel,
  onChange,
}: SliderProps) {
  const pct = ((raw - min) / (max - min)) * 100;
  return (
    <div className="mb-6 last:mb-0">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-ink-700">{label}</span>
        <span className="rounded-md bg-ink-900 px-2 py-0.5 font-mono text-xs font-bold text-white">
          {value}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={raw}
        onChange={(e) => onChange(+e.target.value)}
        className="mt-3 w-full accent-brand-600"
        style={{
          background: `linear-gradient(to right, var(--brand) ${pct}%, #e4e4e7 ${pct}%)`,
          height: "4px",
          borderRadius: "9999px",
          WebkitAppearance: "none",
          appearance: "none",
        }}
      />
      <div className="mt-1.5 flex justify-between text-[11px] text-ink-400">
        <span>{minLabel}</span>
        <span>{maxLabel}</span>
      </div>
    </div>
  );
}

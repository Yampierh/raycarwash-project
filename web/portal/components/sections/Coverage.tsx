"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { MapPin } from "lucide-react";

interface Area {
  name: string;
  primary?: boolean;
  cx: number;
  cy: number;
  r: number;
}

const POSITIONS: Pick<Area, "cx" | "cy" | "r">[] = [
  { cx: 50, cy: 50, r: 12 },
  { cx: 30, cy: 58, r: 6 },
  { cx: 48, cy: 28, r: 5 },
  { cx: 68, cy: 30, r: 5 },
  { cx: 70, cy: 56, r: 6 },
  { cx: 40, cy: 70, r: 4 },
];

export default function Coverage() {
  const t = useTranslations("coverage");
  const rawAreas = t.raw("areas") as { name: string; primary?: boolean }[];
  const areas: Area[] = rawAreas.map((a, i) => ({
    ...a,
    ...POSITIONS[i],
  }));
  const [zip, setZip] = useState("");
  const [status, setStatus] = useState<"idle" | "checking" | "ok" | "soon">(
    "idle",
  );

  function check(e: React.FormEvent) {
    e.preventDefault();
    if (!zip.trim()) return;
    setStatus("checking");
    setTimeout(() => {
      const isCovered = ["46802", "46804", "46805", "46807", "46815"].includes(
        zip.trim(),
      );
      setStatus(isCovered ? "ok" : "soon");
    }, 600);
  }

  return (
    <section
      id="coverage"
      className="border-b border-ink-150 bg-white py-20 md:py-28"
    >
      <div className="mx-auto grid max-w-6xl gap-12 px-6 md:grid-cols-2 md:items-center">
        <div>
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
            {t("kicker")}
          </span>
          <h2 className="mt-3 font-display text-4xl font-bold tracking-tight text-ink-900 md:text-5xl">
            {t("h2")}
          </h2>
          <p className="mt-4 text-lg text-ink-600">{t("sub")}</p>

          <ul className="mt-8 grid gap-2 sm:grid-cols-2">
            {areas.map((a) => (
              <li
                key={a.name}
                className="flex items-center gap-2 text-sm text-ink-700"
              >
                <MapPin className="size-3.5 text-brand-600" />
                {a.name}
                {a.primary && (
                  <span className="rounded-full bg-brand-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-brand-700">
                    {t("hqLabel")}
                  </span>
                )}
              </li>
            ))}
          </ul>

          <form
            onSubmit={check}
            className="mt-8 flex flex-wrap items-center gap-2"
          >
            <input
              type="text"
              value={zip}
              onChange={(e) => {
                setZip(e.target.value);
                setStatus("idle");
              }}
              placeholder={t("zipPlaceholder")}
              maxLength={5}
              inputMode="numeric"
              pattern="[0-9]*"
              className="flex-1 rounded-lg border border-ink-200 bg-white px-4 py-2.5 text-sm text-ink-900 outline-none transition placeholder:text-ink-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
            <button
              type="submit"
              className="inline-flex items-center justify-center rounded-lg bg-ink-900 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-ink-800"
            >
              {t("zipSubmit")}
            </button>
          </form>
          {status === "ok" && (
            <p className="mt-3 text-sm font-medium text-emerald-600">
              ✓ We serve {zip}
            </p>
          )}
          {status === "soon" && (
            <p className="mt-3 text-sm font-medium text-amber-600">
              Not yet in {zip} — we&apos;ll notify you.
            </p>
          )}
        </div>

        <div className="relative">
          <div className="relative aspect-square overflow-hidden rounded-3xl border border-ink-150 bg-gradient-to-br from-ink-50 to-white p-4 shadow-sm">
            <svg
              viewBox="0 0 100 100"
              className="h-full w-full"
              preserveAspectRatio="xMidYMid meet"
            >
              <defs>
                <radialGradient id="hubGrad" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="var(--brand)" stopOpacity="0.35" />
                  <stop
                    offset="60%"
                    stopColor="var(--brand)"
                    stopOpacity="0.1"
                  />
                  <stop offset="100%" stopColor="var(--brand)" stopOpacity="0" />
                </radialGradient>
                <pattern
                  id="mapDots"
                  x="0"
                  y="0"
                  width="4"
                  height="4"
                  patternUnits="userSpaceOnUse"
                >
                  <circle cx="0.7" cy="0.7" r="0.4" fill="#cbd5e1" />
                </pattern>
              </defs>
              <rect width="100" height="100" fill="url(#mapDots)" />
              <path
                d="M0 60 Q20 50 35 55 T70 50 T100 55"
                stroke="#bfdbfe"
                strokeWidth="2"
                fill="none"
                opacity="0.7"
              />
              <circle cx="50" cy="50" r="35" fill="url(#hubGrad)" />
              <circle
                cx="50"
                cy="50"
                r="35"
                fill="none"
                stroke="var(--brand)"
                strokeWidth="0.4"
                strokeDasharray="1 1.2"
                opacity="0.55"
              />
              {areas.map((a) => (
                <g key={a.name}>
                  <circle
                    cx={a.cx}
                    cy={a.cy}
                    r={a.r / 3 + 2}
                    fill="white"
                    opacity="0.95"
                  />
                  <circle
                    cx={a.cx}
                    cy={a.cy}
                    r={a.r / 3}
                    fill={a.primary ? "var(--brand)" : "#09090b"}
                  />
                  {a.primary && (
                    <circle
                      cx={a.cx}
                      cy={a.cy}
                      r="4"
                      fill="none"
                      stroke="var(--brand)"
                      strokeWidth="0.5"
                    >
                      <animate
                        attributeName="r"
                        from="3"
                        to="9"
                        dur="2.4s"
                        repeatCount="indefinite"
                      />
                      <animate
                        attributeName="opacity"
                        from="0.7"
                        to="0"
                        dur="2.4s"
                        repeatCount="indefinite"
                      />
                    </circle>
                  )}
                  <text
                    x={a.cx}
                    y={a.cy - 4}
                    textAnchor="middle"
                    fontSize="2.6"
                    fontFamily="ui-monospace, monospace"
                    fill="#09090b"
                    fontWeight="600"
                  >
                    {a.name.toUpperCase()}
                  </text>
                </g>
              ))}
            </svg>
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-center gap-4 text-xs text-ink-500">
            <span className="flex items-center gap-1.5">
              <span className="size-2 rounded-full bg-brand-600" />
              {t("legendHq")}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="size-2 rounded-full bg-ink-900" />
              {t("legendArea")}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="size-2 rounded-full border border-brand-600" />
              {t("legendRadius")}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

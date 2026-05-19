import { useTranslations } from "next-intl";
import { MapPin } from "lucide-react";

type Tool = { title: string; body: string };

export default function Tools() {
  const t = useTranslations("detailersPage.tools");
  const items = t.raw("items") as Tool[];
  const variants: Array<"dispatcher" | "planner" | "capture"> = [
    "dispatcher",
    "planner",
    "capture",
  ];

  return (
    <section
      id="tools"
      className="relative overflow-hidden border-b border-ink-800 bg-ink-950 py-20 text-white md:py-28"
      style={{ background: "#09090b" }}
    >
      <div
        className="absolute inset-0 -z-10 opacity-30"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, #71717a 1px, transparent 0)",
          backgroundSize: "32px 32px",
        }}
      />

      <div className="mx-auto max-w-6xl px-6">
        <div className="max-w-2xl">
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-500">
            {t("kicker")}
          </span>
          <h2 className="mt-3 font-display text-4xl font-bold tracking-tight md:text-5xl">
            {t("h2")}
          </h2>
          <p className="mt-4 text-lg text-ink-300">{t("sub")}</p>
        </div>

        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {items.map((item, i) => (
            <div
              key={item.title}
              className="flex flex-col items-center rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur transition hover:border-brand-500/50"
            >
              <ToolPhone variant={variants[i]} />
              <div className="mt-6 text-center">
                <h3 className="font-display text-lg font-semibold text-white">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-400">
                  {item.body}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ToolPhone({
  variant,
}: {
  variant: "dispatcher" | "planner" | "capture";
}) {
  return (
    <div className="relative aspect-[9/18] w-[180px] overflow-hidden rounded-[2rem] border-[8px] border-ink-900 bg-ink-900 shadow-phone">
      <div className="absolute left-1/2 top-1.5 z-20 h-4 w-20 -translate-x-1/2 rounded-b-xl bg-ink-900" />
      <div className="absolute inset-0 bg-ink-50 p-2.5 pt-6">
        {variant === "dispatcher" && <DispatcherScreen />}
        {variant === "planner" && <PlannerScreen />}
        {variant === "capture" && <CaptureScreen />}
      </div>
    </div>
  );
}

function DispatcherScreen() {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-[10px] font-semibold">
        <span className="text-ink-600">3 jobs nearby</span>
        <span className="rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-[8px] font-bold text-emerald-700">
          Live
        </span>
      </div>
      <div className="rounded-lg border border-ink-200 bg-white p-2 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold text-ink-900">Full · Civic</span>
          <span className="text-[10px] font-bold text-brand-700">$149</span>
        </div>
        <div className="mt-0.5 flex items-center gap-1 text-[9px] text-ink-500">
          <MapPin className="size-2.5" />
          2.1 mi · 2:30 PM
        </div>
        <div className="mt-1 flex items-center gap-1 text-[9px] text-emerald-700">
          <span className="size-1.5 rounded-full bg-emerald-500" /> Great fit
        </div>
      </div>
      <div className="rounded-lg border border-ink-200 bg-white p-2 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold text-ink-900">
            Interior · Wrangler
          </span>
          <span className="text-[10px] font-bold text-brand-700">$129</span>
        </div>
        <div className="mt-0.5 flex items-center gap-1 text-[9px] text-ink-500">
          <MapPin className="size-2.5" />
          3.4 mi · Tomorrow
        </div>
        <div className="mt-1 flex items-center gap-1 text-[9px] text-brand-700">
          <span className="size-1.5 rounded-full bg-brand-500" /> Good fit
        </div>
      </div>
      <div className="rounded-lg border border-ink-200 bg-ink-100 p-2 opacity-50">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold text-ink-700">
            Exterior · Outside area
          </span>
          <span className="text-[10px] font-bold text-ink-700">$49</span>
        </div>
        <div className="mt-0.5 text-[9px] text-ink-500">
          12 mi · Auto-filtered
        </div>
      </div>
    </div>
  );
}

function PlannerScreen() {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-[10px] font-semibold">
        <span className="text-ink-600">Today · 4 stops</span>
        <span className="rounded-full bg-brand-500/10 px-1.5 py-0.5 text-[8px] font-bold text-brand-700">
          Optimized
        </span>
      </div>
      <div className="overflow-hidden rounded-lg bg-ink-900">
        <svg viewBox="0 0 200 140" preserveAspectRatio="none" className="block">
          <rect width="200" height="140" fill="#1a1a1f" />
          <path
            d="M20 110 Q60 80 90 100 T160 60 L180 30"
            stroke="#3b82f6"
            strokeWidth="2"
            fill="none"
            strokeDasharray="3 3"
          />
          {[
            { x: 20, y: 110, n: "1" },
            { x: 90, y: 100, n: "2" },
            { x: 140, y: 80, n: "3" },
            { x: 180, y: 30, n: "4" },
          ].map((p) => (
            <g key={p.n}>
              <circle cx={p.x} cy={p.y} r="5" fill="#3b82f6" />
              <text
                x={p.x}
                y={p.y + 3}
                textAnchor="middle"
                fontSize="6"
                fill="white"
                fontWeight="700"
              >
                {p.n}
              </text>
            </g>
          ))}
        </svg>
      </div>
      <div className="space-y-1 text-[10px]">
        {[
          { n: "1", l: "9:00 · M3 Exterior" },
          { n: "2", l: "11:30 · Civic Full" },
          { n: "3", l: "2:00 · F-150 Int." },
          { n: "4", l: "4:30 · Sienna Full" },
        ].map((r) => (
          <div
            key={r.n}
            className="flex items-center gap-1.5 rounded bg-white px-1.5 py-1 shadow-sm"
          >
            <span className="flex size-3.5 items-center justify-center rounded-full bg-brand-600 text-[8px] font-bold text-white">
              {r.n}
            </span>
            <span className="text-ink-700">{r.l}</span>
          </div>
        ))}
      </div>
      <div className="text-center text-[9px] text-emerald-700">
        Saved 22 min vs unsorted
      </div>
    </div>
  );
}

function CaptureScreen() {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-[10px] font-semibold">
        <span className="text-ink-600">Capture · 3 / 6</span>
        <span className="rounded-full bg-red-500/10 px-1.5 py-0.5 text-[8px] font-bold text-red-600">
          ● REC
        </span>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {[
          { l: "Before", on: true },
          { l: "After", on: true },
          { l: "Wheels", on: true },
          { l: "Interior", on: false },
          { l: "Engine", on: false, pending: true },
          { l: "Final", on: false, pending: true },
        ].map((c) => (
          <div
            key={c.l}
            className={`relative aspect-square overflow-hidden rounded-lg ${
              c.pending
                ? "border border-dashed border-ink-200 bg-white"
                : "bg-gradient-to-br from-ink-300 to-ink-500"
            } shadow-sm`}
          >
            <div className="absolute inset-1 flex flex-col justify-between p-1">
              {c.pending ? (
                <>
                  <span className="text-base font-bold text-ink-300">+</span>
                  <span className="text-[8px] font-semibold text-ink-500">
                    {c.l}
                  </span>
                </>
              ) : (
                <>
                  {c.on && (
                    <span className="ml-auto flex size-3 items-center justify-center rounded-full bg-emerald-500 text-[7px] font-bold text-white">
                      ✓
                    </span>
                  )}
                  <span className="text-[8px] font-semibold text-white">
                    {c.l}
                  </span>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="text-center text-[9px] text-ink-600">
        Auto-attached to receipt
      </div>
    </div>
  );
}

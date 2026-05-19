import { useTranslations } from "next-intl";
import {
  CalendarClock,
  Wallet,
  ShieldCheck,
  Wrench,
  ArrowRight,
} from "lucide-react";

const ICONS = [CalendarClock, Wallet, ShieldCheck, Wrench];

type Benefit = { title: string; body: string };
type EarnRow = { lbl: string; val: string };

export default function ForDetailers() {
  const t = useTranslations("detailers");
  const benefits = t.raw("benefits") as Benefit[];
  const earnRows = t.raw("earnRows") as EarnRow[];

  return (
    <section
      id="detailers"
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

      <div className="mx-auto grid max-w-6xl gap-12 px-6 md:grid-cols-2 md:items-start">
        <div>
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-500">
            {t("kicker")}
          </span>
          <h2 className="mt-3 font-display text-4xl font-bold tracking-tight md:text-5xl">
            {t("h2")}
          </h2>
          <p className="mt-4 text-lg text-ink-300">{t("sub")}</p>

          <div className="mt-8 rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-wider text-brand-400">
              {t("earnLabel")}
            </div>
            <ul className="mt-4 space-y-3">
              {earnRows.map((r) => (
                <li
                  key={r.lbl}
                  className="flex items-center justify-between border-b border-white/5 pb-3 last:border-0 last:pb-0"
                >
                  <span className="text-sm text-ink-300">{r.lbl}</span>
                  <span className="font-display text-base font-semibold text-white">
                    {r.val}
                  </span>
                </li>
              ))}
            </ul>
            <div className="mt-5 rounded-lg bg-gradient-to-r from-brand-600/20 to-transparent p-3">
              <span className="text-xs font-medium text-brand-400">
                {t("earnTag")}
              </span>
            </div>
          </div>

          <a
            href="/detailers"
            className="mt-8 inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 text-sm font-semibold text-ink-900 transition hover:bg-ink-100"
          >
            {t("cta")}
            <ArrowRight className="size-4" strokeWidth={2.5} />
          </a>
          <p className="mt-3 text-xs text-ink-400">{t("applyNote")}</p>
        </div>

        <ul className="grid gap-4 sm:grid-cols-2">
          {benefits.map((b, i) => {
            const Icon = ICONS[i];
            return (
              <li
                key={b.title}
                className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur transition hover:border-brand-500/50 hover:bg-white/[0.06]"
              >
                <span className="flex size-10 items-center justify-center rounded-lg bg-brand-600/20 text-brand-400">
                  <Icon className="size-5" strokeWidth={1.75} />
                </span>
                <h3 className="mt-4 text-base font-semibold text-white">
                  {b.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-400">
                  {b.body}
                </p>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

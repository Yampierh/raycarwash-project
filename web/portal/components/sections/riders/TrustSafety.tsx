import { useTranslations } from "next-intl";
import { ArrowRight } from "lucide-react";

type Pillar = { step: string; title: string; body: string; meta: string };
type Stat = { n: string; l: string };

export default function TrustSafety() {
  const t = useTranslations("ridersPage.safety");
  const pillars = t.raw("pillars") as Pillar[];
  const stats = t.raw("dispute.stats") as Stat[];

  return (
    <section
      id="safety"
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

        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {pillars.map((p) => (
            <div
              key={p.title}
              className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur transition hover:border-brand-500/50 hover:bg-white/[0.06]"
            >
              <div className="font-mono text-xs font-semibold text-brand-400">
                {p.step}
              </div>
              <h3 className="mt-3 font-display text-lg font-semibold text-white">
                {p.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-400">
                {p.body}
              </p>
              <div className="mt-4 border-t border-white/10 pt-3 text-xs font-medium text-brand-400">
                {p.meta}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 grid gap-8 rounded-3xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur md:grid-cols-[1.2fr_0.8fr] md:p-10">
          <div>
            <span className="text-sm font-semibold uppercase tracking-wider text-brand-500">
              {t("dispute.kicker")}
            </span>
            <h3 className="mt-2 font-display text-2xl font-bold md:text-3xl">
              {t("dispute.h3")}
            </h3>
            <p className="mt-3 text-ink-400">{t("dispute.body")}</p>
            <a
              href="#"
              className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-white hover:text-brand-400"
            >
              {t("dispute.policyCta")}
              <ArrowRight className="size-3.5" />
            </a>
          </div>
          <div className="grid grid-cols-3 gap-3 md:grid-cols-1">
            {stats.map((s) => (
              <div
                key={s.l}
                className="rounded-xl border border-white/10 bg-white/[0.04] p-4 text-center md:text-left"
              >
                <div className="font-display text-2xl font-bold text-white">
                  {s.n}
                </div>
                <div className="mt-1 text-xs text-ink-400">{s.l}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

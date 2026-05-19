import { useTranslations } from "next-intl";
import { ArrowRight, Check } from "lucide-react";

type Perk = { l: string; v: string };

export default function MechanicProviderCTA() {
  const t = useTranslations("mechanicPage.providerCta");
  const reqs = t.raw("reqs") as string[];
  const perks = t.raw("perks") as Perk[];

  return (
    <section
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
      <div className="mx-auto grid max-w-6xl gap-12 px-6 md:grid-cols-2">
        <div>
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-500">
            {t("kicker")}
          </span>
          <h2 className="mt-3 font-display text-4xl font-bold tracking-tight md:text-5xl">
            {t("h2")}
          </h2>
          <p className="mt-4 text-lg text-ink-300">{t("sub")}</p>
          <ul className="mt-8 space-y-3">
            {reqs.map((r) => (
              <li
                key={r}
                className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3"
              >
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-brand-500/20 text-brand-400">
                  <Check className="size-3.5" strokeWidth={3} />
                </span>
                <span className="text-sm font-medium text-ink-200">{r}</span>
              </li>
            ))}
          </ul>
          <a
            href="#waitlist"
            className="mt-8 inline-flex items-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-ink-900 transition hover:bg-ink-100"
          >
            {t("ctaApply")}
            <ArrowRight className="size-4" />
          </a>
        </div>

        <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-white/[0.04] to-transparent p-6 backdrop-blur md:p-8">
          <div className="text-xs font-semibold uppercase tracking-wider text-brand-400">
            {t("perksTag")}
          </div>
          <ul className="mt-5 space-y-4">
            {perks.map((p) => (
              <li
                key={p.l}
                className="flex items-center justify-between border-b border-white/10 pb-3 last:border-0 last:pb-0"
              >
                <span className="text-sm text-ink-300">{p.l}</span>
                <span className="font-display text-base font-semibold text-white">
                  {p.v}
                </span>
              </li>
            ))}
          </ul>
          <div className="mt-6 rounded-xl bg-brand-600/20 px-4 py-3 text-center">
            <span className="font-display text-sm font-semibold text-brand-300">
              {t("spotsLabel")}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

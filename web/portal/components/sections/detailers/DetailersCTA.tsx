import { useTranslations } from "next-intl";
import { ArrowRight, Check } from "lucide-react";

type PreviewStep = {
  label: string;
  state: "done" | "active" | "pending" | "";
};

export default function DetailersCTA() {
  const t = useTranslations("detailersPage.cta");
  const footnotes = t.raw("footnotes") as string[];
  const previewSteps = t.raw("previewSteps") as PreviewStep[];

  return (
    <section id="apply" className="bg-white py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-6">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-ink-900 via-ink-900 to-brand-900 p-8 text-white shadow-2xl md:p-14">
          <div
            className="absolute inset-0 -z-0 opacity-30"
            style={{
              backgroundImage:
                "radial-gradient(circle at 1px 1px, #71717a 1px, transparent 0)",
              backgroundSize: "32px 32px",
            }}
          />
          <div className="relative grid gap-10 md:grid-cols-[1.2fr_0.8fr] md:items-center">
            <div>
              <span className="text-sm font-semibold uppercase tracking-wider text-brand-400">
                {t("kicker")}
              </span>
              <h2 className="mt-3 font-display text-4xl font-bold tracking-tight md:text-5xl">
                {t("h2")}
              </h2>
              <p className="mt-4 max-w-lg text-lg text-ink-300">{t("sub")}</p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <a
                  href="/signup?role=detailer"
                  className="inline-flex items-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-ink-900 shadow-sm transition hover:bg-ink-100"
                >
                  {t("ctaApply")}
                  <ArrowRight className="size-4" />
                </a>
                <a
                  href="/"
                  className="inline-flex items-center gap-2 rounded-lg border border-white/20 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  {t("ctaBack")}
                </a>
              </div>
              <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-400">
                {footnotes.map((f) => (
                  <span key={f} className="inline-flex items-center gap-1.5">
                    <Check className="size-3 text-brand-400" strokeWidth={3} />
                    {f}
                  </span>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5 backdrop-blur">
              <div className="text-xs font-semibold uppercase tracking-wider text-ink-400">
                {t("previewTitle")}
              </div>
              <ol className="mt-4 space-y-2">
                {previewSteps.map((s, i) => (
                  <li
                    key={s.label}
                    className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 text-sm ${
                      s.state === "done"
                        ? "border-emerald-500/30 bg-emerald-500/5 text-white"
                        : s.state === "active"
                          ? "border-brand-500/40 bg-brand-500/10 text-white"
                          : "border-white/10 bg-white/[0.02] text-ink-400"
                    }`}
                  >
                    <span
                      className={`flex size-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                        s.state === "done"
                          ? "bg-emerald-500 text-white"
                          : s.state === "active"
                            ? "bg-brand-500 text-white"
                            : "bg-white/10 text-ink-400"
                      }`}
                    >
                      {s.state === "done" ? "✓" : i + 1}
                    </span>
                    <span className="font-medium">{s.label}</span>
                  </li>
                ))}
              </ol>
              <div className="mt-4 text-xs text-ink-400">{t("previewMeta")}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

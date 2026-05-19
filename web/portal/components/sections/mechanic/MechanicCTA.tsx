"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ArrowRight, Check } from "lucide-react";

type RolloutItem = {
  q: string;
  l: string;
  state: "active" | "done" | "";
};

export default function MechanicCTA() {
  const t = useTranslations("mechanicPage.cta");
  const footnotes = t.raw("footnotes") as string[];
  const rollout = t.raw("rollout") as RolloutItem[];
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setSubmitted(true);
  }

  return (
    <section id="waitlist" className="bg-white py-20 md:py-28">
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

              {submitted ? (
                <div className="mt-8 inline-flex items-center gap-2 rounded-xl bg-emerald-500/10 px-4 py-3 text-sm font-semibold text-emerald-300">
                  <Check className="size-4" /> {t("thanks")}
                </div>
              ) : (
                <form
                  onSubmit={submit}
                  className="mt-8 flex flex-wrap items-center gap-2"
                >
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={t("emailPlaceholder")}
                    className="min-w-0 flex-1 rounded-lg border border-white/15 bg-white/[0.06] px-4 py-3 text-sm text-white outline-none transition placeholder:text-ink-400 focus:border-brand-400 focus:ring-2 focus:ring-brand-400/30"
                  />
                  <button
                    type="submit"
                    className="inline-flex items-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-ink-900 shadow-sm transition hover:bg-ink-100"
                  >
                    {t("submit")}
                    <ArrowRight className="size-4" />
                  </button>
                </form>
              )}

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
                {t("rolloutTitle")}
              </div>
              <ol className="mt-4 space-y-2">
                {rollout.map((r) => (
                  <li
                    key={r.q}
                    className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 text-sm ${
                      r.state === "done"
                        ? "border-emerald-500/30 bg-emerald-500/5 text-white"
                        : r.state === "active"
                          ? "border-brand-500/40 bg-brand-500/10 text-white"
                          : "border-white/10 bg-white/[0.02] text-ink-400"
                    }`}
                  >
                    <span
                      className={`flex w-12 shrink-0 justify-center rounded-md py-1 font-mono text-[10px] font-bold ${
                        r.state === "done"
                          ? "bg-emerald-500/20 text-emerald-300"
                          : r.state === "active"
                            ? "bg-brand-500/20 text-brand-300"
                            : "bg-white/5 text-ink-500"
                      }`}
                    >
                      {r.q}
                    </span>
                    <span className="font-medium">{r.l}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

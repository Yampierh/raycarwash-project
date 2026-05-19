import { useTranslations } from "next-intl";
import { Check } from "lucide-react";

type Step = { t: string; b: string };

export default function Requirements() {
  const t = useTranslations("detailersPage.requirements");
  const reqs = t.raw("items") as string[];
  const steps = t.raw("steps") as Step[];

  return (
    <section id="requirements" className="bg-white py-20 md:py-28">
      <div className="mx-auto grid max-w-6xl gap-12 px-6 md:grid-cols-2">
        <div>
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
            {t("kicker")}
          </span>
          <h2 className="mt-3 font-display text-4xl font-bold tracking-tight text-ink-900 md:text-5xl">
            {t("h2")}
          </h2>
          <p className="mt-4 text-lg text-ink-600">{t("sub")}</p>
          <ul className="mt-8 space-y-3">
            {reqs.map((r) => (
              <li
                key={r}
                className="flex items-start gap-3 rounded-xl border border-ink-150 bg-ink-50/40 p-4"
              >
                <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-700">
                  <Check className="size-3.5" strokeWidth={3} />
                </span>
                <span className="text-sm font-medium text-ink-800">{r}</span>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
            {t("stepsKicker")}
          </span>
          <h3 className="mt-3 font-display text-3xl font-bold tracking-tight text-ink-900">
            {t("stepsH3")}
          </h3>
          <ol className="mt-8 space-y-4">
            {steps.map((s, i) => (
              <li
                key={s.t}
                className="flex items-start gap-4 rounded-2xl border border-ink-150 bg-white p-5 shadow-sm"
              >
                <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-ink-900 font-mono text-sm font-bold text-white">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div>
                  <div className="font-display text-base font-semibold text-ink-900">
                    {s.t}
                  </div>
                  <div className="mt-1 text-sm text-ink-600">{s.b}</div>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

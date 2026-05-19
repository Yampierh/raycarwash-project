import { useTranslations } from "next-intl";

type Step = { t: string; b: string };

export default function MechanicHow() {
  const t = useTranslations("mechanicPage.how");
  const steps = t.raw("steps") as Step[];

  return (
    <section id="how" className="bg-white py-20 md:py-28">
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

        <ol className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          {steps.map((s, i) => (
            <li
              key={s.t}
              className="relative flex flex-col rounded-2xl border border-ink-150 bg-ink-50/40 p-6 transition hover:border-brand-200 hover:bg-white hover:shadow-md"
            >
              <span className="flex size-10 items-center justify-center rounded-xl bg-brand-600 font-mono text-sm font-bold text-white shadow-sm">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="mt-5 font-display text-lg font-semibold text-ink-900">
                {s.t}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-600">{s.b}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

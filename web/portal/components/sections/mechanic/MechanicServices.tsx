import { useTranslations } from "next-intl";
import { Clock, ArrowRight } from "lucide-react";

type Item = { name: string; price: string; dur: string; body: string };

export default function MechanicServices() {
  const t = useTranslations("mechanicPage.services");
  const items = t.raw("items") as Item[];

  return (
    <section
      id="services"
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

        <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {items.map((s) => (
            <div
              key={s.name}
              className="flex flex-col rounded-2xl border border-ink-150 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex items-baseline justify-between">
                <span className="font-display text-base font-semibold text-ink-900">
                  {s.name}
                </span>
                <span className="font-display text-lg font-bold text-brand-700">
                  {s.price}
                </span>
              </div>
              <div className="mt-1 flex items-center gap-1 text-xs text-ink-500">
                <Clock className="size-3" /> {s.dur}
              </div>
              <p className="mt-3 flex-1 text-sm leading-relaxed text-ink-600">
                {s.body}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-3 text-sm text-ink-600">
          <span>{t("foot")}</span>
          <a
            href="#waitlist"
            className="inline-flex items-center gap-1.5 font-semibold text-ink-900 hover:text-brand-600"
          >
            {t("footCta")}
            <ArrowRight className="size-3.5" />
          </a>
        </div>
      </div>
    </section>
  );
}

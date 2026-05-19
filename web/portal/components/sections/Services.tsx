import { useTranslations } from "next-intl";
import { Check, Clock, ArrowRight } from "lucide-react";

type Service = {
  name: string;
  price: string;
  duration: string;
  features: string[];
};

export default function Services() {
  const t = useTranslations("services");
  const items = t.raw("items") as Service[];

  return (
    <section
      id="services"
      className="border-b border-ink-150 bg-ink-50 py-20 md:py-28"
    >
      <div className="mx-auto max-w-6xl px-6">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-2xl">
            <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
              {t("kicker")}
            </span>
            <h2 className="mt-3 font-display text-4xl font-bold tracking-tight text-ink-900 md:text-5xl">
              {t("h2")}
            </h2>
            <p className="mt-4 text-lg text-ink-600">{t("sub")}</p>
          </div>
          <a
            href="#book"
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-900 transition hover:text-brand-600"
          >
            See all add-ons
            <ArrowRight className="size-3.5" />
          </a>
        </div>

        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {items.map((s, i) => {
            const featured = i === 2;
            return (
              <div
                key={s.name}
                className={`relative flex flex-col rounded-2xl border bg-white p-7 transition ${
                  featured
                    ? "border-ink-900 shadow-xl ring-1 ring-ink-900"
                    : "border-ink-150 shadow-sm hover:border-ink-200 hover:shadow-md"
                }`}
              >
                {featured && (
                  <span className="absolute -top-3 left-7 rounded-full bg-ink-900 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-white">
                    Most popular
                  </span>
                )}
                <h3 className="font-display text-lg font-semibold text-ink-900">
                  {s.name}
                </h3>
                <div className="mt-4 flex items-baseline gap-2">
                  <span className="text-xs font-medium uppercase tracking-wider text-ink-500">
                    {t("fromLabel")}
                  </span>
                  <span className="font-display text-4xl font-bold text-ink-900">
                    {s.price}
                  </span>
                </div>
                <div className="mt-2 flex items-center gap-1.5 text-xs text-ink-500">
                  <Clock className="size-3.5" />
                  {s.duration}
                </div>
                <ul className="mt-6 flex-1 space-y-2.5 text-sm text-ink-700">
                  {s.features.map((f) => (
                    <li key={f} className="flex items-start gap-2">
                      <Check
                        className="mt-0.5 size-4 shrink-0 text-brand-600"
                        strokeWidth={2.5}
                      />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                <a
                  href="#book"
                  className={`mt-6 inline-flex items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold transition ${
                    featured
                      ? "bg-ink-900 text-white hover:bg-ink-800"
                      : "border border-ink-200 bg-white text-ink-900 hover:bg-ink-50"
                  }`}
                >
                  Book this
                </a>
              </div>
            );
          })}
        </div>

        <p className="mt-10 max-w-3xl text-xs leading-relaxed text-ink-500">
          {t("footnote")}
        </p>
      </div>
    </section>
  );
}

import { useTranslations } from "next-intl";
import { Check, Clock } from "lucide-react";

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
      className="border-b border-zinc-200 bg-zinc-50 py-24 md:py-32"
    >
      <div className="mx-auto max-w-6xl px-6">
        <div className="max-w-2xl">
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
            {t("kicker")}
          </span>
          <h2 className="mt-3 font-display text-4xl font-bold tracking-tight text-zinc-900 md:text-5xl">
            {t("h2")}
          </h2>
          <p className="mt-4 text-lg text-zinc-600">{t("sub")}</p>
        </div>

        <div className="mt-16 grid gap-6 md:grid-cols-3">
          {items.map((s, i) => {
            const featured = i === 2;
            return (
              <div
                key={s.name}
                className={
                  featured
                    ? "relative flex flex-col rounded-2xl border-2 border-zinc-900 bg-white p-8 shadow-lg"
                    : "flex flex-col rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm"
                }
              >
                {featured && (
                  <span className="absolute -top-3 left-8 rounded-full bg-zinc-900 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-white">
                    Most popular
                  </span>
                )}
                <h3 className="text-lg font-semibold text-zinc-900">{s.name}</h3>
                <div className="mt-4 flex items-baseline gap-2">
                  <span className="text-xs font-medium uppercase tracking-wider text-zinc-500">
                    {t("fromLabel")}
                  </span>
                  <span className="font-display text-4xl font-bold text-zinc-900">
                    {s.price}
                  </span>
                </div>
                <div className="mt-2 flex items-center gap-1.5 text-xs text-zinc-500">
                  <Clock className="size-3.5" />
                  {s.duration}
                </div>
                <ul className="mt-6 flex-1 space-y-3 text-sm text-zinc-700">
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
              </div>
            );
          })}
        </div>

        <p className="mt-10 max-w-3xl text-xs leading-relaxed text-zinc-500">
          {t("footnote")}
        </p>
      </div>
    </section>
  );
}

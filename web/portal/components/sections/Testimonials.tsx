import { useTranslations } from "next-intl";
import { Star } from "lucide-react";

type Testimonial = {
  quote: string;
  name: string;
  city: string;
  rating: number;
};

export default function Testimonials() {
  const t = useTranslations("testimonials");
  const items = t.raw("items") as Testimonial[];

  return (
    <section className="border-b border-ink-150 bg-white py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-6">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-2xl">
            <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
              {t("kicker")}
            </span>
            <h2 className="mt-3 font-display text-4xl font-bold tracking-tight text-ink-900 md:text-5xl">
              {t("h2")}
            </h2>
          </div>
          <div className="text-right">
            <div className="flex justify-end gap-0.5 text-amber-400">
              {Array.from({ length: 5 }).map((_, i) => (
                <Star key={i} className="size-4 fill-current" />
              ))}
            </div>
            <div className="mt-1 text-xs text-ink-500">{t("ratingSummary")}</div>
          </div>
        </div>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {items.map((item) => (
            <figure
              key={item.name}
              className="flex flex-col rounded-2xl border border-ink-150 bg-ink-50/40 p-6 transition hover:border-ink-200 hover:bg-white hover:shadow-md"
            >
              <div className="flex gap-0.5 text-amber-400">
                {Array.from({ length: item.rating }).map((_, i) => (
                  <Star key={i} className="size-3.5 fill-current" />
                ))}
              </div>
              <blockquote className="mt-4 flex-1 text-sm leading-relaxed text-ink-700">
                &ldquo;{item.quote}&rdquo;
              </blockquote>
              <figcaption className="mt-6 border-t border-ink-150 pt-4 text-xs">
                <div className="font-semibold text-ink-900">{item.name}</div>
                <div className="mt-0.5 text-ink-500">{item.city}</div>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}

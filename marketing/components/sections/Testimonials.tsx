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
    <section className="border-b border-zinc-200 bg-white py-24 md:py-32">
      <div className="mx-auto max-w-6xl px-6">
        <div className="max-w-2xl">
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
            {t("kicker")}
          </span>
          <h2 className="mt-3 font-display text-4xl font-bold tracking-tight text-zinc-900 md:text-5xl">
            {t("h2")}
          </h2>
        </div>

        <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {items.map((item) => (
            <figure
              key={item.name}
              className="flex flex-col rounded-2xl border border-zinc-200 bg-zinc-50/50 p-6"
            >
              <div className="flex gap-0.5 text-amber-400">
                {Array.from({ length: item.rating }).map((_, i) => (
                  <Star key={i} className="size-4 fill-current" />
                ))}
              </div>
              <blockquote className="mt-4 flex-1 text-sm leading-relaxed text-zinc-700">
                &ldquo;{item.quote}&rdquo;
              </blockquote>
              <figcaption className="mt-6 border-t border-zinc-200 pt-4 text-xs">
                <div className="font-semibold text-zinc-900">{item.name}</div>
                <div className="mt-0.5 text-zinc-500">{item.city}</div>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}

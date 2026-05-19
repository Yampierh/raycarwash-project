import { useTranslations } from "next-intl";
import { Star } from "lucide-react";

type Review = {
  quote: string;
  name: string;
  city: string;
  size: "sm" | "md" | "lg";
};

const SIZE_CLASS: Record<Review["size"], string> = {
  sm: "row-span-1",
  md: "row-span-1",
  lg: "row-span-2",
};

export default function ReviewsWall() {
  const t = useTranslations("ridersPage.reviewsWall");
  const items = t.raw("items") as Review[];

  return (
    <section id="reviews" className="bg-white py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
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
            <div className="mt-1 text-xs text-ink-500">{t("summary")}</div>
          </div>
        </div>

        <div className="mt-12 grid auto-rows-[180px] gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {items.map((r, i) => (
            <figure
              key={i}
              className={`flex flex-col rounded-2xl border border-ink-150 bg-ink-50/40 p-5 transition hover:border-ink-200 hover:bg-white hover:shadow-md ${SIZE_CLASS[r.size]}`}
            >
              <div className="flex gap-0.5 text-amber-400">
                {Array.from({ length: 5 }).map((_, j) => (
                  <Star key={j} className="size-3 fill-current" />
                ))}
              </div>
              <blockquote className="mt-3 flex-1 text-sm leading-relaxed text-ink-700">
                &ldquo;{r.quote}&rdquo;
              </blockquote>
              <figcaption className="mt-4 flex items-center gap-2.5 border-t border-ink-150 pt-3">
                <div className="size-8 rounded-full bg-gradient-to-br from-brand-200 to-brand-400" />
                <div>
                  <div className="text-xs font-semibold text-ink-900">
                    {r.name}
                  </div>
                  <div className="text-[11px] text-ink-500">{r.city}</div>
                </div>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}

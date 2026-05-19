import { useTranslations } from "next-intl";

type Item = { quote: string; name: string; meta: string };

export default function DetailersTestimonials() {
  const t = useTranslations("detailersPage.testimonials");
  const items = t.raw("items") as Item[];

  return (
    <section className="border-b border-ink-150 bg-ink-50 py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-6">
        <div className="max-w-2xl">
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
            {t("kicker")}
          </span>
          <h2 className="mt-3 font-display text-4xl font-bold tracking-tight text-ink-900 md:text-5xl">
            {t("h2")}
          </h2>
        </div>

        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {items.map((item) => (
            <figure
              key={item.name}
              className="flex flex-col rounded-2xl border border-ink-150 bg-white p-6 shadow-sm"
            >
              <div className="flex-1 font-display text-lg leading-relaxed text-ink-900">
                &ldquo;{item.quote}&rdquo;
              </div>
              <figcaption className="mt-6 flex items-center gap-3 border-t border-ink-150 pt-4">
                <div className="size-10 rounded-full bg-gradient-to-br from-brand-300 to-brand-600" />
                <div>
                  <div className="text-sm font-semibold text-ink-900">
                    {item.name}
                  </div>
                  <div className="mt-0.5 text-xs text-ink-500">{item.meta}</div>
                </div>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}

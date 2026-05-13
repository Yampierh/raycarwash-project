import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";

type Item = { q: string; a: string };

export default function FAQ() {
  const t = useTranslations("faq");
  const items = t.raw("items") as Item[];

  return (
    <section
      id="faq"
      className="border-b border-zinc-200 bg-zinc-50 py-24 md:py-32"
    >
      <div className="mx-auto max-w-3xl px-6">
        <div className="text-center">
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
            {t("kicker")}
          </span>
          <h2 className="mt-3 font-display text-4xl font-bold tracking-tight text-zinc-900 md:text-5xl">
            {t("h2")}
          </h2>
        </div>

        <div className="mt-16 divide-y divide-zinc-200 rounded-2xl border border-zinc-200 bg-white">
          {items.map((item) => (
            <details
              key={item.q}
              className="group px-6 py-5 [&[open]>summary>svg]:rotate-45"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-left text-base font-semibold text-zinc-900">
                {item.q}
                <Plus
                  className="size-5 shrink-0 text-zinc-400 transition-transform"
                  strokeWidth={2}
                />
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-zinc-600">
                {item.a}
              </p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

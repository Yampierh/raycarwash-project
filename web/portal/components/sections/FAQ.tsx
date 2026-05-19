import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";

type Item = { q: string; a: string };

interface FAQProps {
  namespace?: string;
  variant?: "default" | "boxed";
}

export default function FAQ({
  namespace = "faq",
  variant = "boxed",
}: FAQProps = {}) {
  const t = useTranslations(namespace);
  const items = t.raw("items") as Item[];

  return (
    <section
      id="faq"
      className={`border-b border-ink-150 ${
        variant === "boxed" ? "bg-ink-50" : "bg-white"
      } py-20 md:py-28`}
    >
      <div className="mx-auto max-w-3xl px-6">
        <div className="text-center">
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
            {t("kicker")}
          </span>
          <h2 className="mt-3 font-display text-4xl font-bold tracking-tight text-ink-900 md:text-5xl">
            {t("h2")}
          </h2>
        </div>

        <div className="mt-12 divide-y divide-ink-150 overflow-hidden rounded-2xl border border-ink-150 bg-white shadow-sm">
          {items.map((item) => (
            <details
              key={item.q}
              className="group px-6 py-5 [&[open]>summary>svg]:rotate-45 [&[open]]:bg-ink-50/60"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-left text-base font-semibold text-ink-900">
                {item.q}
                <Plus
                  className="size-5 shrink-0 text-ink-400 transition-transform"
                  strokeWidth={2}
                />
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-ink-600">
                {item.a}
              </p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

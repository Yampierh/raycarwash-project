import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { ShieldCheck, UserCheck, Star, ArrowRight } from "lucide-react";

const ICONS = [UserCheck, ShieldCheck, Star];
const HREFS = ["/trust/detailers", "/trust/insurance", "/contact"];

export default function TrustBadges() {
  const t = useTranslations("trust");
  const items = t.raw("items") as { title: string; body: string }[];

  return (
    <section className="border-b border-ink-150 bg-white py-16 md:py-20">
      <div className="mx-auto max-w-6xl px-6">
        <div className="grid gap-4 sm:grid-cols-3">
          {items.map((item, i) => {
            const Icon = ICONS[i];
            return (
              <Link
                key={item.title}
                href={HREFS[i]}
                className="group flex items-start gap-4 rounded-2xl border border-ink-150 bg-ink-50/40 p-5 transition hover:border-brand-100 hover:bg-brand-50/30"
              >
                <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-brand-100 text-brand-600 transition group-hover:bg-brand-600 group-hover:text-white">
                  <Icon className="size-5" strokeWidth={1.75} />
                </span>
                <div className="flex-1">
                  <h3 className="font-semibold text-ink-900 group-hover:text-brand-900">
                    {item.title}
                  </h3>
                  <p className="mt-1 text-sm leading-relaxed text-ink-500">
                    {item.body}
                  </p>
                </div>
                <ArrowRight className="size-4 shrink-0 text-ink-400 transition group-hover:translate-x-0.5 group-hover:text-brand-600" />
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}

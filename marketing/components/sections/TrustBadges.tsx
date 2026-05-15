import { Link } from "@/i18n/navigation";
import { ShieldCheck, UserCheck, Star } from "lucide-react";

const BADGES = [
  {
    icon: UserCheck,
    title: "Verified Detailers",
    description: "Every detailer passes identity & background checks",
    href: "/trust/detailers",
  },
  {
    icon: Shield,
    title: "Insured Service",
    description: "Your vehicle is protected during every job",
    href: "/trust/insurance",
  },
  {
    icon: Star,
    title: "Satisfaction Guarantee",
    description: "Not happy? We'll make it right",
    href: "/contact",
  },
];

function Shield(props: React.ComponentProps<typeof ShieldCheck>) {
  return <ShieldCheck {...props} />;
}

export default function TrustBadges() {
  return (
    <section className="border-b border-zinc-200 bg-white py-16 md:py-20">
      <div className="mx-auto max-w-6xl px-6">
        <div className="grid gap-8 sm:grid-cols-3">
          {BADGES.map((badge) => {
            const Icon = badge.icon;
            return (
              <Link
                key={badge.title}
                href={badge.href}
                className="group flex items-start gap-4 rounded-2xl border border-zinc-200 bg-zinc-50/50 p-6 transition hover:border-brand-200 hover:bg-brand-50/30"
              >
                <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-brand-100 text-brand-600 group-hover:bg-brand-600 group-hover:text-white">
                  <Icon className="size-6" strokeWidth={1.5} />
                </span>
                <div>
                  <h3 className="font-semibold text-zinc-900 group-hover:text-brand-900">
                    {badge.title}
                  </h3>
                  <p className="mt-1 text-sm leading-relaxed text-zinc-500 group-hover:text-zinc-600">
                    {badge.description}
                  </p>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
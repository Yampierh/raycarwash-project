import { useTranslations } from "next-intl";
import { CalendarClock, Wallet, ShieldCheck, Wrench, ArrowRight } from "lucide-react";

const ICONS = [CalendarClock, Wallet, ShieldCheck, Wrench];

type Benefit = { title: string; body: string };

export default function ForDetailers() {
  const t = useTranslations("detailers");
  const benefits = t.raw("benefits") as Benefit[];
  const appStore = process.env.NEXT_PUBLIC_APPSTORE_URL ?? "#";

  return (
    <section
      id="detailers"
      className="relative overflow-hidden border-b border-zinc-800 bg-zinc-950 py-24 text-white md:py-32"
    >
      <div
        className="absolute inset-0 -z-10 opacity-30"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, #71717a 1px, transparent 0)",
          backgroundSize: "32px 32px",
        }}
      />

      <div className="mx-auto grid max-w-6xl gap-16 px-6 md:grid-cols-2 md:items-start">
        <div>
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-500">
            {t("kicker")}
          </span>
          <h2 className="mt-3 font-display text-4xl font-bold tracking-tight md:text-5xl">
            {t("h2")}
          </h2>
          <p className="mt-4 text-lg text-zinc-400">{t("sub")}</p>

          <a
            href={appStore}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-8 inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 text-sm font-semibold text-zinc-900 transition hover:bg-zinc-100"
          >
            {t("cta")}
            <ArrowRight className="size-4" strokeWidth={2.5} />
          </a>
        </div>

        <ul className="grid gap-4 sm:grid-cols-2">
          {benefits.map((b, i) => {
            const Icon = ICONS[i];
            return (
              <li
                key={b.title}
                className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6 backdrop-blur"
              >
                <span className="flex size-10 items-center justify-center rounded-lg bg-brand-600/20 text-brand-500">
                  <Icon className="size-5" strokeWidth={2} />
                </span>
                <h3 className="mt-4 text-base font-semibold text-white">
                  {b.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-zinc-400">
                  {b.body}
                </p>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

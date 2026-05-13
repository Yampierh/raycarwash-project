import { useTranslations } from "next-intl";
import { Sparkles, MapPin, Clock } from "lucide-react";

const ICONS = [Sparkles, MapPin, Clock];

export default function Hero() {
  const t = useTranslations("hero");
  const bullets = t.raw("bullets") as string[];

  const appStore = process.env.NEXT_PUBLIC_APPSTORE_URL ?? "#";
  const playStore = process.env.NEXT_PUBLIC_PLAYSTORE_URL ?? "#";

  return (
    <section className="relative overflow-hidden border-b border-zinc-200 bg-gradient-to-b from-white to-zinc-50">
      <div className="absolute inset-0 -z-10 [mask-image:radial-gradient(ellipse_at_top,black_40%,transparent_70%)]">
        <div
          className="absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage:
              "radial-gradient(circle at 1px 1px, #18181b 1px, transparent 0)",
            backgroundSize: "32px 32px",
          }}
        />
      </div>

      <div className="mx-auto grid max-w-6xl gap-16 px-6 py-24 md:grid-cols-2 md:items-center md:py-32">
        <div className="flex flex-col">
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs font-medium text-zinc-600 shadow-sm">
            <span className="size-1.5 rounded-full bg-brand-500" />
            {t("kicker")}
          </span>

          <h1 className="mt-6 font-display text-5xl font-bold leading-[1.05] tracking-tight text-zinc-900 md:text-6xl">
            {t("h1")}
          </h1>

          <p className="mt-6 max-w-lg text-lg leading-relaxed text-zinc-600">
            {t("sub")}
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <a
              href={appStore}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center rounded-lg bg-zinc-900 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800"
            >
              {t("ctaPrimary")}
            </a>
            <a
              href="#detailers"
              className="inline-flex items-center justify-center rounded-lg border border-zinc-200 bg-white px-6 py-3 text-sm font-semibold text-zinc-900 shadow-sm transition hover:bg-zinc-50"
            >
              {t("ctaSecondary")}
            </a>
          </div>

          <ul className="mt-10 flex flex-col gap-3 text-sm text-zinc-700">
            {bullets.map((b, i) => {
              const Icon = ICONS[i % ICONS.length];
              return (
                <li key={b} className="flex items-center gap-3">
                  <span className="flex size-7 items-center justify-center rounded-full bg-brand-50 text-brand-600">
                    <Icon className="size-3.5" strokeWidth={2.5} />
                  </span>
                  {b}
                </li>
              );
            })}
          </ul>
        </div>

        <div className="relative">
          <div className="relative mx-auto aspect-[9/16] w-full max-w-sm overflow-hidden rounded-[2.5rem] border-[12px] border-zinc-900 bg-zinc-900 shadow-2xl">
            <div className="absolute inset-0 bg-gradient-to-br from-brand-500 via-brand-600 to-zinc-900">
              <div className="absolute left-1/2 top-3 h-6 w-32 -translate-x-1/2 rounded-b-2xl bg-zinc-900" />
              <div className="absolute inset-x-6 top-20 space-y-4">
                <div className="rounded-2xl bg-white/95 p-4 shadow-lg">
                  <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                    Next appointment
                  </div>
                  <div className="mt-2 text-base font-semibold text-zinc-900">
                    Full Detail · 2014 Honda Civic
                  </div>
                  <div className="mt-1 text-sm text-zinc-600">
                    Today, 2:30 PM · 25 min ETA
                  </div>
                  <div className="mt-4 flex items-center gap-2">
                    <div className="size-8 rounded-full bg-zinc-200" />
                    <div className="flex-1">
                      <div className="text-xs font-medium text-zinc-900">
                        Marcus T.
                      </div>
                      <div className="text-[10px] text-zinc-500">
                        ★ 4.9 · 312 jobs
                      </div>
                    </div>
                    <div className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                      En route
                    </div>
                  </div>
                </div>
                <div className="rounded-2xl bg-white/95 p-4 shadow-lg">
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                      Quote
                    </div>
                    <div className="text-base font-bold text-zinc-900">
                      $149
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-zinc-600">
                    Flat-rate · Includes interior + exterior + clay-bar
                  </div>
                </div>
                <div className="rounded-2xl bg-white/95 p-4 shadow-lg">
                  <div className="grid grid-cols-3 gap-2">
                    <div className="aspect-square rounded-lg bg-gradient-to-br from-zinc-200 to-zinc-300" />
                    <div className="aspect-square rounded-lg bg-gradient-to-br from-zinc-200 to-zinc-300" />
                    <div className="aspect-square rounded-lg bg-gradient-to-br from-zinc-200 to-zinc-300" />
                  </div>
                  <div className="mt-2 text-[10px] uppercase tracking-wide text-zinc-500">
                    Before / After
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

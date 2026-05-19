import { setRequestLocale, getTranslations } from "next-intl/server";
import { Sparkles, Shield, Clock } from "lucide-react";

const ICONS = [Sparkles, Shield, Clock];

export default async function AboutPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("about");

  const values = t.raw("values") as { title: string; body: string }[];

  return (
    <div className="overflow-hidden">
      <section className="border-b border-zinc-200 bg-white py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-3xl text-center">
            <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
              {t("kicker")}
            </span>
            <h1 className="mt-4 font-display text-4xl font-bold tracking-tight text-zinc-900 md:text-5xl">
              {t("h1")}
            </h1>
            <p className="mt-6 text-lg leading-relaxed text-zinc-600">
              {t("intro")}
            </p>
          </div>
        </div>
      </section>

      <section className="border-b border-zinc-200 bg-zinc-50 py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid gap-16 md:grid-cols-2">
            <div>
              <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
                {t("storyKicker")}
              </span>
              <h2 className="mt-3 font-display text-3xl font-bold tracking-tight text-zinc-900 md:text-4xl">
                {t("storyH2")}
              </h2>
              <div className="mt-6 space-y-4 text-base leading-relaxed text-zinc-600">
                {t.raw("storyBody") as string[]}
              </div>
            </div>
            <div className="relative">
              <div className="aspect-[4/3] overflow-hidden rounded-2xl bg-zinc-200">
                <div className="flex h-full items-center justify-center bg-zinc-100">
                  <Sparkles className="size-16 text-zinc-300" strokeWidth={1} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-zinc-200 bg-white py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-3xl text-center">
            <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
              {t("valuesKicker")}
            </span>
            <h2 className="mt-3 font-display text-3xl font-bold tracking-tight text-zinc-900 md:text-4xl">
              {t("valuesH2")}
            </h2>
          </div>
          <div className="mt-16 grid gap-8 sm:grid-cols-3">
            {values.map((v, i) => {
              const Icon = ICONS[i];
              return (
                <div
                  key={v.title}
                  className="rounded-2xl border border-zinc-200 bg-zinc-50/50 p-8 text-center"
                >
                  <span className="inline-flex size-12 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
                    <Icon className="size-6" strokeWidth={1.5} />
                  </span>
                  <h3 className="mt-6 text-lg font-semibold text-zinc-900">
                    {v.title}
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed text-zinc-600">
                    {v.body}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="bg-zinc-900 py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-display text-3xl font-bold tracking-tight text-white md:text-4xl">
              {t("ctaH2")}
            </h2>
            <p className="mt-4 text-lg text-zinc-400">{t("ctaSub")}</p>
            <div className="mt-8 flex flex-wrap justify-center gap-4">
              <a
                href="/signup"
                className="inline-flex items-center justify-center rounded-lg bg-white px-6 py-3 text-sm font-semibold text-zinc-900 transition hover:bg-zinc-100"
              >
                {t("ctaPrimary")}
              </a>
              <a
                href="/detailers"
                className="inline-flex items-center justify-center rounded-lg border border-zinc-700 px-6 py-3 text-sm font-semibold text-white transition hover:bg-zinc-800"
              >
                {t("ctaSecondary")}
              </a>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
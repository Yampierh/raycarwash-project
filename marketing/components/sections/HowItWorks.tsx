import { useTranslations } from "next-intl";
import { Smartphone, Car, Droplets, Star } from "lucide-react";

const ICONS = [Smartphone, Car, Droplets, Star];

type Step = { title: string; body: string };

export default function HowItWorks() {
  const t = useTranslations("how");
  const steps = t.raw("steps") as Step[];

  return (
    <section id="how" className="border-b border-zinc-200 bg-white py-24 md:py-32">
      <div className="mx-auto max-w-6xl px-6">
        <div className="max-w-2xl">
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
            {t("kicker")}
          </span>
          <h2 className="mt-3 font-display text-4xl font-bold tracking-tight text-zinc-900 md:text-5xl">
            {t("h2")}
          </h2>
          <p className="mt-4 text-lg text-zinc-600">{t("sub")}</p>
        </div>

        <ol className="mt-16 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((step, i) => {
            const Icon = ICONS[i];
            return (
              <li
                key={step.title}
                className="relative flex flex-col rounded-2xl border border-zinc-200 bg-zinc-50/50 p-6 transition hover:border-zinc-300 hover:bg-white hover:shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <span className="flex size-11 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm">
                    <Icon className="size-5" strokeWidth={2} />
                  </span>
                  <span className="font-display text-3xl font-bold text-zinc-200">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </div>
                <h3 className="mt-6 text-lg font-semibold text-zinc-900">
                  {step.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-zinc-600">
                  {step.body}
                </p>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

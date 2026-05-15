import { setRequestLocale, getTranslations } from "next-intl/server";
import {
  CalendarClock,
  Wallet,
  ShieldCheck,
  Wrench,
  ArrowRight,
  CheckCircle,
} from "lucide-react";

const BENEFIT_ICONS = [CalendarClock, Wallet, ShieldCheck, Wrench];
const REQUIREMENTS = [
  "Own vehicle with transport for equipment",
  "Pro-grade detailing tools and products",
  "Reliable transportation",
  "Smartphone with data plan",
  "Pass background check",
  "Valid ID",
];

export default async function DetailersPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("detailers");

  const benefits = t.raw("benefits") as { title: string; body: string }[];
  const appStore = process.env.NEXT_PUBLIC_APPSTORE_URL ?? "#";

  return (
    <div className="overflow-hidden">
      <section className="relative overflow-hidden border-b border-zinc-800 bg-zinc-950 py-24 text-white md:py-32">
        <div
          className="absolute inset-0 -z-10 opacity-30"
          style={{
            backgroundImage:
              "radial-gradient(circle at 1px 1px, #71717a 1px, transparent 0)",
            backgroundSize: "32px 32px",
          }}
        />

        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-3xl text-center">
            <span className="text-sm font-semibold uppercase tracking-wider text-brand-500">
              {t("kicker")}
            </span>
            <h1 className="mt-4 font-display text-4xl font-bold tracking-tight md:text-5xl lg:text-6xl">
              {t("h2")}
            </h1>
            <p className="mt-6 text-lg text-zinc-400">{t("sub")}</p>

            <div className="mt-10 flex flex-wrap justify-center gap-4">
              <a
                href="/signup?role=detailer"
                className="inline-flex items-center justify-center rounded-lg bg-white px-8 py-4 text-base font-semibold text-zinc-900 transition hover:bg-zinc-100"
              >
                Apply now
                <ArrowRight className="ml-2 size-5" strokeWidth={2} />
              </a>
              <a
                href="#benefits"
                className="inline-flex items-center justify-center rounded-lg border border-zinc-700 px-8 py-4 text-base font-semibold text-white transition hover:bg-zinc-800"
              >
                Learn more
              </a>
            </div>
          </div>
        </div>
      </section>

      <section id="benefits" className="border-b border-zinc-200 bg-white py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-3xl text-center">
            <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
              Why join RayCarWash
            </span>
            <h2 className="mt-4 font-display text-3xl font-bold tracking-tight text-zinc-900 md:text-4xl">
              Everything you need to run your business
            </h2>
          </div>

          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {benefits.map((b, i) => {
              const Icon = BENEFIT_ICONS[i];
              return (
                <div
                  key={b.title}
                  className="rounded-2xl border border-zinc-200 bg-zinc-50/50 p-8"
                >
                  <span className="flex size-12 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
                    <Icon className="size-6" strokeWidth={1.5} />
                  </span>
                  <h3 className="mt-6 text-lg font-semibold text-zinc-900">
                    {b.title}
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed text-zinc-600">
                    {b.body}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="border-b border-zinc-200 bg-zinc-50 py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid gap-16 lg:grid-cols-2 lg:items-center">
            <div>
              <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
                What you need
              </span>
              <h2 className="mt-4 font-display text-3xl font-bold tracking-tight text-zinc-900 md:text-4xl">
                Requirements to join
              </h2>
              <p className="mt-4 text-lg text-zinc-600">
                We maintain high standards to ensure quality service for every
                client. Here&apos;s what you&apos;ll need:
              </p>

              <ul className="mt-8 space-y-4">
                {REQUIREMENTS.map((req) => (
                  <li key={req} className="flex items-start gap-3">
                    <CheckCircle className="mt-0.5 size-5 shrink-0 text-brand-600" />
                    <span className="text-zinc-700">{req}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="relative">
              <div className="aspect-[4/3] overflow-hidden rounded-2xl border border-zinc-200 bg-white p-8">
                <div className="flex h-full flex-col items-center justify-center text-center">
                  <div className="mb-6 rounded-full bg-brand-100 p-4">
                    <ShieldCheck className="size-12 text-brand-600" />
                  </div>
                  <h3 className="text-xl font-bold text-zinc-900">
                    Verified & Insured
                  </h3>
                  <p className="mt-3 max-w-sm text-zinc-600">
                    Every detailer goes through identity verification and
                    background check before accepting jobs.
                  </p>
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
              How it works
            </span>
            <h2 className="mt-4 font-display text-3xl font-bold tracking-tight text-zinc-900 md:text-4xl">
              Start earning in 4 steps
            </h2>
          </div>

          <div className="mt-16 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                step: "01",
                title: "Apply",
                body: "Sign up and tell us about your experience and services.",
              },
              {
                step: "02",
                title: "Verify",
                body: "Complete identity verification and background check.",
              },
              {
                step: "03",
                title: "Setup",
                body: "Add your services, pricing, and service area to your profile.",
              },
              {
                step: "04",
                title: "Start earning",
                body: "Accept jobs, complete details, and get paid the same day.",
              },
            ].map((item) => (
              <div key={item.step} className="text-center">
                <span className="font-display text-5xl font-bold text-zinc-200">
                  {item.step}
                </span>
                <h3 className="mt-4 text-lg font-semibold text-zinc-900">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm text-zinc-600">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-zinc-900 py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-display text-3xl font-bold tracking-tight text-white md:text-4xl">
              Ready to start?
            </h2>
            <p className="mt-4 text-lg text-zinc-400">
              Join hundreds of detailers earning on their own schedule.
            </p>
            <div className="mt-10">
              <a
                href="/signup?role=detailer"
                className="inline-flex items-center justify-center rounded-lg bg-white px-8 py-4 text-base font-semibold text-zinc-900 transition hover:bg-zinc-100"
              >
                Apply now
                <ArrowRight className="ml-2 size-5" strokeWidth={2} />
              </a>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
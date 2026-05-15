import { setRequestLocale } from "next-intl/server";
import {
  ShieldCheck,
  UserCheck,
  FileText,
  Search,
  CheckCircle,
  Star,
  ArrowRight,
} from "lucide-react";

const STEPS = [
  {
    icon: UserCheck,
    title: "Identity Verification",
    description:
      "Every detailer must verify their identity through Stripe Identity. We confirm their name, address, and government-issued ID to ensure they're who they say they are.",
  },
  {
    icon: Search,
    title: "Background Check",
    description:
      "We run comprehensive background checks to screen for any criminal history or concerning records. This protects you and your property.",
  },
  {
    icon: FileText,
    title: "Portfolio Review",
    description:
      "Before activation, each detailer submits photos of their work. Our team reviews the quality to ensure it meets our professional standards.",
  },
  {
    icon: Star,
    title: "Ongoing Quality Control",
    description:
      "After going live, detailers are monitored through client ratings and reviews. Low-rated detailers are flagged and may be suspended pending review.",
  },
];

const STATS = [
  { value: "15%", label: "Approval rate" },
  { value: "4.9★", label: "Average rating" },
  { value: "98%", label: "Satisfaction" },
];

export default async function TrustDetailersPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <div className="overflow-hidden">
      <section className="border-b border-zinc-200 bg-white py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-3xl text-center">
            <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
              Trust & Safety
            </span>
            <h1 className="mt-4 font-display text-4xl font-bold tracking-tight text-zinc-900 md:text-5xl">
              How we vet our detailers
            </h1>
            <p className="mt-6 text-lg leading-relaxed text-zinc-600">
              Your safety is our top priority. Every detailer on our platform
              goes through a rigorous verification process before they can
              accept any jobs.
            </p>
          </div>
        </div>
      </section>

      <section className="border-b border-zinc-200 bg-zinc-50 py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid gap-12 lg:grid-cols-2 lg:gap-16">
            <div>
              <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
                Our process
              </span>
              <h2 className="mt-4 font-display text-3xl font-bold tracking-tight text-zinc-900 md:text-4xl">
                Four-step verification
              </h2>
              <p className="mt-4 text-lg text-zinc-600">
                We accept only the best. Our multi-layered vetting process
                ensures that every detailer meets our high standards for
                quality, reliability, and character.
              </p>
            </div>
            <div className="space-y-8">
              {STEPS.map((step, i) => {
                const Icon = step.icon;
                return (
                  <div key={step.title} className="flex gap-6">
                    <span className="flex size-12 shrink-0 items-center justify-center rounded-xl border border-zinc-200 bg-white text-brand-600">
                      <Icon className="size-6" strokeWidth={1.5} />
                    </span>
                    <div>
                      <div className="flex items-center gap-3">
                        <span className="flex size-6 items-center justify-center rounded-full bg-zinc-900 text-xs font-bold text-white">
                          {i + 1}
                        </span>
                        <h3 className="font-semibold text-zinc-900">
                          {step.title}
                        </h3>
                      </div>
                      <p className="mt-2 text-sm leading-relaxed text-zinc-600">
                        {step.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-zinc-200 bg-white py-20 md:py-24">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid gap-8 sm:grid-cols-3">
            {STATS.map((stat) => (
              <div
                key={stat.label}
                className="text-center"
              >
                <div className="font-display text-4xl font-bold text-zinc-900 md:text-5xl">
                  {stat.value}
                </div>
                <div className="mt-2 text-sm font-medium text-zinc-500">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-b border-zinc-200 bg-zinc-50 py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-3xl text-center">
            <h2 className="font-display text-3xl font-bold tracking-tight text-zinc-900 md:text-4xl">
              What happens if something goes wrong?
            </h2>
            <p className="mt-4 text-lg text-zinc-600">
              We have protocols in place for every situation. Our support team
              is available to help resolve any issues quickly and fairly.
            </p>
          </div>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[
              {
                title: "Dispute Resolution",
                description:
                  "Open a dispute in the app within 48 hours. Our team reviews the case and ensures fair resolution.",
              },
              {
                title: "Property Protection",
                description:
                  "Every job is covered by our protection policy. Your vehicle and property are insured during service.",
              },
              {
                title: "Satisfaction Guarantee",
                description:
                  "If the work doesn't meet documented standards, we'll arrange a redo or refund.",
              },
            ].map((item) => (
              <div
                key={item.title}
                className="rounded-2xl border border-zinc-200 bg-white p-6"
              >
                <CheckCircle className="size-8 text-brand-600" strokeWidth={1.5} />
                <h3 className="mt-4 text-lg font-semibold text-zinc-900">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm text-zinc-600">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-zinc-900 py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-display text-3xl font-bold tracking-tight text-white md:text-4xl">
              Ready to book?
            </h2>
            <p className="mt-4 text-lg text-zinc-400">
              Book with confidence knowing every detailer is verified and
              insured.
            </p>
            <div className="mt-10">
              <a
                href="/signup"
                className="inline-flex items-center justify-center rounded-lg bg-white px-8 py-4 text-base font-semibold text-zinc-900 transition hover:bg-zinc-100"
              >
                Get started
                <ArrowRight className="ml-2 size-5" strokeWidth={2} />
              </a>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
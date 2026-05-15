import { setRequestLocale } from "next-intl/server";
import {
  Shield,
  Car,
  FileCheck,
  AlertCircle,
  CheckCircle,
  ArrowRight,
} from "lucide-react";

const CLIENT_COVERAGE = [
  {
    title: "Vehicle Coverage",
    description:
      "Your vehicle is covered during the service period. Any damage caused by the detailer is protected up to the coverage limit.",
  },
  {
    title: "Property Damage Protection",
    description:
      "If the detailer accidentally damages your property (driveway, fencing, etc.) during service, you're protected.",
  },
  {
    title: " Liability Insurance",
    description:
      "Every detailer carries minimum liability coverage as part of our platform requirements.",
  },
];

const DETAILER_REQUIREMENTS = [
  {
    icon: Shield,
    title: "Liability Insurance",
    description:
      "Detailers must maintain minimum $1 million liability coverage to accept jobs on our platform.",
  },
  {
    icon: Car,
    title: "Auto Insurance",
    description:
      "Professional auto insurance is required for any vehicle used in business operations.",
  },
  {
    icon: FileCheck,
    title: "Equipment Insurance",
    description:
      "Detailers are responsible for insuring their own equipment and supplies.",
  },
];

export default async function TrustInsurancePage({
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
              Insurance & Coverage
            </h1>
            <p className="mt-6 text-lg leading-relaxed text-zinc-600">
              We protect both clients and detailers. Learn what's covered and
              how our insurance protection works.
            </p>
          </div>
        </div>
      </section>

      <section className="border-b border-zinc-200 bg-zinc-50 py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-3xl">
            <div className="flex items-center gap-4">
              <span className="flex size-14 items-center justify-center rounded-2xl bg-brand-100 text-brand-600">
                <Shield className="size-7" strokeWidth={1.5} />
              </span>
              <div className="text-left">
                <h2 className="font-display text-2xl font-bold tracking-tight text-zinc-900">
                  For Clients
                </h2>
                <p className="text-zinc-600">
                  Your protection starts the moment you book.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-12 grid gap-6 lg:grid-cols-3">
            {CLIENT_COVERAGE.map((item) => (
              <div
                key={item.title}
                className="rounded-2xl border border-zinc-200 bg-white p-8"
              >
                <CheckCircle className="size-8 text-emerald-600" strokeWidth={1.5} />
                <h3 className="mt-4 text-lg font-semibold text-zinc-900">
                  {item.title}
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-zinc-600">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-b border-zinc-200 bg-white py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-3xl">
            <div className="flex items-center gap-4">
              <span className="flex size-14 items-center justify-center rounded-2xl bg-zinc-100 text-zinc-600">
                <Car className="size-7" strokeWidth={1.5} />
              </span>
              <div className="text-left">
                <h2 className="font-display text-2xl font-bold tracking-tight text-zinc-900">
                  For Detailers
                </h2>
                <p className="text-zinc-600">
                  Insurance requirements to join our platform.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-12 grid gap-8 lg:grid-cols-3">
            {DETAILER_REQUIREMENTS.map((item) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.title}
                  className="rounded-2xl border border-zinc-200 bg-zinc-50/50 p-8"
                >
                  <span className="flex size-12 items-center justify-center rounded-xl bg-white border border-zinc-200 text-zinc-600">
                    <Icon className="size-6" strokeWidth={1.5} />
                  </span>
                  <h3 className="mt-6 text-lg font-semibold text-zinc-900">
                    {item.title}
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed text-zinc-600">
                    {item.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="border-b border-zinc-200 bg-amber-50 py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-3xl">
            <div className="flex items-start gap-4">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
                <AlertCircle className="size-5" strokeWidth={2} />
              </span>
              <div>
                <h2 className="font-display text-xl font-bold tracking-tight text-zinc-900">
                  What's NOT covered
                </h2>
                <ul className="mt-4 space-y-3 text-sm text-zinc-600">
                  <li className="flex items-start gap-2">
                    <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-zinc-400" />
                    Pre-existing damage or wear and tear
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-zinc-400" />
                    Damage from extreme neglect or hazardous conditions
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-zinc-400" />
                    Items left inside the vehicle during service
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-zinc-400" />
                    Consequential damages (loss of use, etc.)
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-zinc-200 bg-zinc-50 py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-3xl">
            <h2 className="font-display text-2xl font-bold tracking-tight text-zinc-900">
              How to file a claim
            </h2>
            <p className="mt-4 text-zinc-600">
              If something goes wrong, we're here to help resolve it quickly.
            </p>
            <div className="mt-8 space-y-4">
              {[
                "Contact us within 48 hours of the incident",
                "Provide photos of any damage if applicable",
                "Our team reviews and responds within 3 business days",
                "Resolution may include re-service, refund, or coverage payment",
              ].map((step, i) => (
                <div key={i} className="flex items-center gap-4">
                  <span className="flex size-8 items-center justify-center rounded-full bg-zinc-900 text-sm font-bold text-white">
                    {i + 1}
                  </span>
                  <span className="text-zinc-700">{step}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="bg-zinc-900 py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-display text-3xl font-bold tracking-tight text-white md:text-4xl">
              Have questions?
            </h2>
            <p className="mt-4 text-lg text-zinc-400">
              Our support team is here to help with any insurance-related
              questions.
            </p>
            <div className="mt-10">
              <a
                href="/contact"
                className="inline-flex items-center justify-center rounded-lg bg-white px-8 py-4 text-base font-semibold text-zinc-900 transition hover:bg-zinc-100"
              >
                Contact support
                <ArrowRight className="ml-2 size-5" strokeWidth={2} />
              </a>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
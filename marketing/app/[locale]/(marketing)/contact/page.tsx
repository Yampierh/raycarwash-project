"use client";

import { useState } from "react";
import { Mail, Phone, Clock, MapPin, Send } from "lucide-react";

export default function ContactPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    message: "",
  });
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const email = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "hello@raycarwash.com";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    await new Promise((r) => setTimeout(r, 1000));
    setSubmitted(true);
    setLoading(false);
  };

  const contactInfo = [
    {
      icon: Mail,
      label: "Email",
      value: email,
      href: `mailto:${email}`,
    },
    {
      icon: Phone,
      label: "Phone",
      value: "(260) XXX-XXXX",
      href: "tel:+12600000000",
    },
    {
      icon: MapPin,
      label: "Service Area",
      value: "Fort Wayne, IN",
    },
    {
      icon: Clock,
      label: "Hours",
      value: "Mon-Sun: 8am - 8pm",
    },
  ];

  return (
    <div className="overflow-hidden">
      <section className="border-b border-zinc-200 bg-white py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-3xl text-center">
            <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
              Contact
            </span>
            <h1 className="mt-4 font-display text-4xl font-bold tracking-tight text-zinc-900 md:text-5xl">
              Get in touch
            </h1>
            <p className="mt-6 text-lg leading-relaxed text-zinc-600">
              Have questions? We&apos;d love to hear from you. Send us a message
              and we&apos;ll respond as soon as possible.
            </p>
          </div>
        </div>
      </section>

      <section className="bg-zinc-50 py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid gap-16 lg:grid-cols-2">
            <div>
              <h2 className="font-display text-2xl font-bold tracking-tight text-zinc-900">
                Send us a message
              </h2>
              <p className="mt-2 text-zinc-600">
                Fill out the form below and we&apos;ll get back to you within 24
                hours.
              </p>

              {submitted ? (
                <div className="mt-8 rounded-xl border border-emerald-200 bg-emerald-50 p-6">
                  <p className="font-medium text-emerald-800">
                    Thanks for reaching out! We&apos;ll get back to you soon.
                  </p>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="mt-8 space-y-6">
                  <div>
                    <label
                      htmlFor="name"
                      className="block text-sm font-medium text-zinc-700"
                    >
                      Name
                    </label>
                    <input
                      type="text"
                      id="name"
                      required
                      value={formData.name}
                      onChange={(e) =>
                        setFormData({ ...formData, name: e.target.value })
                      }
                      className="mt-2 block w-full rounded-lg border border-zinc-300 px-4 py-3 text-zinc-900 placeholder-zinc-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      placeholder="Your name"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="email"
                      className="block text-sm font-medium text-zinc-700"
                    >
                      Email
                    </label>
                    <input
                      type="email"
                      id="email"
                      required
                      value={formData.email}
                      onChange={(e) =>
                        setFormData({ ...formData, email: e.target.value })
                      }
                      className="mt-2 block w-full rounded-lg border border-zinc-300 px-4 py-3 text-zinc-900 placeholder-zinc-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      placeholder="you@example.com"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="message"
                      className="block text-sm font-medium text-zinc-700"
                    >
                      Message
                    </label>
                    <textarea
                      id="message"
                      required
                      rows={5}
                      value={formData.message}
                      onChange={(e) =>
                        setFormData({ ...formData, message: e.target.value })
                      }
                      className="mt-2 block w-full rounded-lg border border-zinc-300 px-4 py-3 text-zinc-900 placeholder-zinc-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      placeholder="How can we help you?"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-zinc-900 px-6 py-3 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:opacity-50"
                  >
                    {loading ? (
                      "Sending..."
                    ) : (
                      <>
                        Send message
                        <Send className="size-4" />
                      </>
                    )}
                  </button>
                </form>
              )}
            </div>

            <div>
              <h2 className="font-display text-2xl font-bold tracking-tight text-zinc-900">
                Contact information
              </h2>
              <p className="mt-2 text-zinc-600">
                Prefer to reach out directly? Here&apos;s how you can contact
                us.
              </p>

              <div className="mt-8 space-y-6">
                {contactInfo.map((info) => {
                  const Icon = info.icon;
                  return (
                    <div key={info.label} className="flex gap-4">
                      <span className="flex size-12 shrink-0 items-center justify-center rounded-xl border border-zinc-200 bg-white text-zinc-500">
                        <Icon className="size-5" strokeWidth={1.5} />
                      </span>
                      <div>
                        <p className="text-sm font-medium text-zinc-900">
                          {info.label}
                        </p>
                        {info.href ? (
                          <a
                            href={info.href}
                            className="text-zinc-600 hover:text-zinc-900"
                          >
                            {info.value}
                          </a>
                        ) : (
                          <p className="text-zinc-600">{info.value}</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-12 rounded-2xl border border-zinc-200 bg-white p-6">
                <h3 className="font-semibold text-zinc-900">Service Area</h3>
                <p className="mt-2 text-sm text-zinc-600">
                  We currently serve Fort Wayne and surrounding areas including
                  Aboite, New Haven, Huntertown, and Leo-Cedarville.
                </p>
                <div className="mt-4 aspect-[16/9] overflow-hidden rounded-lg bg-zinc-100">
                  <div className="flex h-full items-center justify-center">
                    <MapPin className="size-8 text-zinc-300" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
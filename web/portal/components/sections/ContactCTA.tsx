"use client";

import { useTranslations } from "next-intl";
import { useAudienceStore } from "@/lib/store/audience";
import { Mail, Apple, Play, ArrowRight } from "lucide-react";

export default function ContactCTA() {
  const t = useTranslations("contact");
  const audience = useAudienceStore((s) => s.audience);
  const isClient = audience === "client";

  const appStore = process.env.NEXT_PUBLIC_APPSTORE_URL ?? "#";
  const playStore = process.env.NEXT_PUBLIC_PLAYSTORE_URL ?? "#";
  const email = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "hello@raycarwash.com";

  return (
    <section className="bg-white py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-6">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-ink-900 via-ink-900 to-brand-900 p-8 text-white shadow-2xl md:p-14">
          <div
            className="absolute inset-0 -z-0 opacity-30"
            style={{
              backgroundImage:
                "radial-gradient(circle at 1px 1px, #71717a 1px, transparent 0)",
              backgroundSize: "32px 32px",
            }}
          />
          <div className="relative grid gap-8 md:grid-cols-5 md:items-center md:gap-12">
            <div className="md:col-span-3">
              <span className="text-sm font-semibold uppercase tracking-wider text-brand-400">
                {t("kicker")}
              </span>
              <h2 className="mt-3 font-display text-4xl font-bold tracking-tight md:text-5xl">
                {isClient ? t("h2Client") : t("h2Detailer")}
              </h2>
              <p className="mt-4 max-w-lg text-lg text-ink-300">
                {isClient ? t("subClient") : t("subDetailer")}
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                {isClient ? (
                  <>
                    <a
                      href={appStore}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-ink-900 shadow-sm transition hover:bg-ink-100"
                    >
                      <Apple className="size-4" />
                      {t("appStore")}
                    </a>
                    <a
                      href={playStore}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 rounded-lg border border-white/20 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
                    >
                      <Play className="size-4" />
                      {t("playStore")}
                    </a>
                  </>
                ) : (
                  <a
                    href="/detailers"
                    className="inline-flex items-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-ink-900 shadow-sm transition hover:bg-ink-100"
                  >
                    {t("applyCta")}
                    <ArrowRight className="size-4" />
                  </a>
                )}
              </div>
              <p className="mt-6 inline-flex items-center gap-2 text-sm text-ink-400">
                <Mail className="size-4" />
                {t("email")}{" "}
                <a
                  href={`mailto:${email}`}
                  className="font-medium text-white underline-offset-4 hover:underline"
                >
                  {email}
                </a>
              </p>
            </div>

            <div className="md:col-span-2">
              <div className="grid grid-cols-2 gap-2">
                <div className="col-span-2 aspect-[4/3] overflow-hidden rounded-xl border border-white/10 bg-white/5">
                  <Stripes label={t("heroPhotoLabel")} dark />
                </div>
                <div className="aspect-square overflow-hidden rounded-xl border border-white/10 bg-white/5">
                  <Stripes label={t("beforeLabel")} />
                </div>
                <div className="aspect-square overflow-hidden rounded-xl border border-white/10 bg-white/[0.03]">
                  <Stripes label={t("afterLabel")} dark />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Stripes({ label, dark }: { label: string; dark?: boolean }) {
  return (
    <div className="relative h-full w-full">
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: dark
            ? "repeating-linear-gradient(45deg, rgba(255,255,255,0.05) 0px, rgba(255,255,255,0.05) 6px, transparent 6px, transparent 14px)"
            : "repeating-linear-gradient(45deg, rgba(255,255,255,0.12) 0px, rgba(255,255,255,0.12) 6px, transparent 6px, transparent 14px)",
        }}
      />
      <span className="absolute inset-0 flex items-center justify-center font-mono text-[10px] font-bold tracking-[0.2em] text-white/60">
        {label}
      </span>
    </div>
  );
}

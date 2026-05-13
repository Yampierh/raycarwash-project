import { useTranslations } from "next-intl";
import { Mail } from "lucide-react";

export default function ContactCTA() {
  const t = useTranslations("contact");

  const appStore = process.env.NEXT_PUBLIC_APPSTORE_URL ?? "#";
  const playStore = process.env.NEXT_PUBLIC_PLAYSTORE_URL ?? "#";
  const email = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "hello@raycarwash.com";

  return (
    <section className="border-b border-zinc-200 bg-white py-24 md:py-32">
      <div className="mx-auto max-w-4xl px-6 text-center">
        <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
          {t("kicker")}
        </span>
        <h2 className="mt-3 font-display text-4xl font-bold tracking-tight text-zinc-900 md:text-5xl">
          {t("h2")}
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-lg text-zinc-600">{t("sub")}</p>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
          <a
            href={appStore}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-lg bg-zinc-900 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800"
          >
            App Store
          </a>
          <a
            href={playStore}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-lg bg-zinc-900 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800"
          >
            Google Play
          </a>
        </div>

        <p className="mt-10 inline-flex items-center gap-2 text-sm text-zinc-500">
          <Mail className="size-4" />
          {t("email")}{" "}
          <a
            href={`mailto:${email}`}
            className="font-medium text-zinc-900 underline-offset-4 hover:underline"
          >
            {email}
          </a>
        </p>
      </div>
    </section>
  );
}

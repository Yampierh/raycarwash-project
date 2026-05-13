import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";

export default function Footer() {
  const t = useTranslations("footer");
  const year = new Date().getFullYear();
  const email = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "hello@raycarwash.com";

  return (
    <footer className="border-t border-zinc-200 bg-white">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <div className="grid gap-12 md:grid-cols-4">
          <div className="md:col-span-1">
            <Link href="/" className="flex items-center gap-2">
              <span className="flex size-8 items-center justify-center rounded-lg bg-zinc-900 text-sm font-bold text-white">
                R
              </span>
              <span className="font-display text-lg font-bold tracking-tight text-zinc-900">
                RayCarWash
              </span>
            </Link>
            <p className="mt-3 max-w-xs text-sm text-zinc-500">{t("tagline")}</p>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-900">
              {t("sections.product")}
            </h3>
            <ul className="mt-4 space-y-2 text-sm">
              <li>
                <a href="#how" className="text-zinc-600 hover:text-zinc-900">
                  {t("links.how")}
                </a>
              </li>
              <li>
                <a href="#services" className="text-zinc-600 hover:text-zinc-900">
                  {t("links.services")}
                </a>
              </li>
              <li>
                <a href="#faq" className="text-zinc-600 hover:text-zinc-900">
                  {t("links.faq")}
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-900">
              {t("sections.company")}
            </h3>
            <ul className="mt-4 space-y-2 text-sm">
              <li>
                <a
                  href="#detailers"
                  className="text-zinc-600 hover:text-zinc-900"
                >
                  {t("links.detailers")}
                </a>
              </li>
              <li>
                <Link
                  href="/login"
                  className="text-zinc-600 hover:text-zinc-900"
                >
                  {t("links.login")}
                </Link>
              </li>
              <li>
                <a
                  href={`mailto:${email}`}
                  className="text-zinc-600 hover:text-zinc-900"
                >
                  {t("links.contact")}
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-900">
              {t("sections.legal")}
            </h3>
            <ul className="mt-4 space-y-2 text-sm">
              <li>
                <Link
                  href="/legal/privacy"
                  className="text-zinc-600 hover:text-zinc-900"
                >
                  {t("links.privacy")}
                </Link>
              </li>
              <li>
                <Link
                  href="/legal/terms"
                  className="text-zinc-600 hover:text-zinc-900"
                >
                  {t("links.terms")}
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-12 border-t border-zinc-200 pt-6 text-xs text-zinc-500">
          {t("copyright", { year })}
        </div>
      </div>
    </footer>
  );
}

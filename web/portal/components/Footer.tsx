import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Apple, Play } from "lucide-react";

export default function Footer() {
  const t = useTranslations("footer");
  const year = new Date().getFullYear();
  const appStore = process.env.NEXT_PUBLIC_APPSTORE_URL ?? "#";
  const playStore = process.env.NEXT_PUBLIC_PLAYSTORE_URL ?? "#";

  return (
    <footer className="border-t border-ink-150 bg-white">
      <div className="mx-auto max-w-6xl px-6 py-14">
        <div className="grid gap-10 md:grid-cols-4">
          <div className="md:col-span-1">
            <Link href="/" className="flex items-center gap-2">
              <span className="flex size-8 items-center justify-center rounded-lg bg-ink-900 text-sm font-bold text-white">
                R
              </span>
              <span className="font-display text-lg font-bold tracking-tight text-ink-900">
                RayCarWash
              </span>
            </Link>
            <p className="mt-3 max-w-xs text-sm text-ink-500">{t("tagline")}</p>
            <div className="mt-5 flex flex-col gap-2">
              <a
                href={appStore}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex w-fit items-center gap-2.5 rounded-lg border border-ink-200 bg-white px-3 py-2 text-xs font-semibold text-ink-900 transition hover:bg-ink-50"
              >
                <Apple className="size-4" />
                <div className="text-left">
                  <div className="text-[9px] font-medium text-ink-500">
                    Download on
                  </div>
                  <div className="text-xs">App Store</div>
                </div>
              </a>
              <a
                href={playStore}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex w-fit items-center gap-2.5 rounded-lg border border-ink-200 bg-white px-3 py-2 text-xs font-semibold text-ink-900 transition hover:bg-ink-50"
              >
                <Play className="size-4" />
                <div className="text-left">
                  <div className="text-[9px] font-medium text-ink-500">
                    Get it on
                  </div>
                  <div className="text-xs">Google Play</div>
                </div>
              </a>
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-900">
              {t("sections.product")}
            </h3>
            <ul className="mt-4 space-y-2 text-sm">
              <li>
                <a href="/#how" className="text-ink-600 hover:text-ink-900">
                  {t("links.how")}
                </a>
              </li>
              <li>
                <a href="/#services" className="text-ink-600 hover:text-ink-900">
                  {t("links.services")}
                </a>
              </li>
              <li>
                <a href="/#coverage" className="text-ink-600 hover:text-ink-900">
                  Coverage
                </a>
              </li>
              <li>
                <a href="/#faq" className="text-ink-600 hover:text-ink-900">
                  {t("links.faq")}
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-900">
              {t("sections.company")}
            </h3>
            <ul className="mt-4 space-y-2 text-sm">
              <li>
                <Link href="/riders" className="text-ink-600 hover:text-ink-900">
                  For riders
                </Link>
              </li>
              <li>
                <Link
                  href="/detailers"
                  className="text-ink-600 hover:text-ink-900"
                >
                  {t("links.detailers")}
                </Link>
              </li>
              <li>
                <Link
                  href="/mechanic"
                  className="text-ink-600 hover:text-ink-900"
                >
                  Mechanic (soon)
                </Link>
              </li>
              <li>
                <Link href="/about" className="text-ink-600 hover:text-ink-900">
                  {t("links.about")}
                </Link>
              </li>
              <li>
                <Link
                  href="/contact"
                  className="text-ink-600 hover:text-ink-900"
                >
                  {t("links.contact")}
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-900">
              {t("sections.legal")}
            </h3>
            <ul className="mt-4 space-y-2 text-sm">
              <li>
                <Link
                  href="/legal/privacy"
                  className="text-ink-600 hover:text-ink-900"
                >
                  {t("links.privacy")}
                </Link>
              </li>
              <li>
                <Link
                  href="/legal/terms"
                  className="text-ink-600 hover:text-ink-900"
                >
                  {t("links.terms")}
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-between gap-3 border-t border-ink-150 pt-6 text-xs text-ink-500">
          <span>{t("copyright", { year })}</span>
          <span className="font-mono">EN · USD · Fort Wayne, IN</span>
        </div>
      </div>
    </footer>
  );
}

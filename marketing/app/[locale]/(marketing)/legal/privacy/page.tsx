import { setRequestLocale, getTranslations } from "next-intl/server";

const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL || "https://raycarwash.com";

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "PrivacyPolicy",
  name: "RayCarWash Privacy Policy",
  description:
    "Privacy Policy for RayCarWash mobile car wash and detailing platform.",
  url: `${BASE_URL}/legal/privacy`,
  publisher: {
    "@type": "Organization",
    name: "RayCarWash",
    url: BASE_URL,
  },
};

export default async function PrivacyPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("legal.privacy");

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <article className="mx-auto max-w-3xl px-6 py-24 md:py-32">
        <p className="text-sm text-zinc-500">
          {t("lastUpdated")}: 2026-05-13
        </p>
        <h1 className="mt-2 font-display text-4xl font-bold tracking-tight text-zinc-900">
          {t("title")}
        </h1>
        <div className="prose prose-zinc mt-8 text-zinc-700">
          <p>{t("intro")}</p>
        </div>
      </article>
    </>
  );
}

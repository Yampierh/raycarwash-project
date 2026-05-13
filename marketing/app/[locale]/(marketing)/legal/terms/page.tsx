import { setRequestLocale, getTranslations } from "next-intl/server";

export default async function TermsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("legal.terms");

  return (
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
  );
}

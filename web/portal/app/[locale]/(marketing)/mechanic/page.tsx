import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { hasLocale } from "next-intl";
import { routing } from "@/i18n/routing";
import MechanicHero from "@/components/sections/mechanic/MechanicHero";
import MechanicServices from "@/components/sections/mechanic/MechanicServices";
import MechanicHow from "@/components/sections/mechanic/MechanicHow";
import MechanicProviderCTA from "@/components/sections/mechanic/MechanicProviderCTA";
import FAQ from "@/components/sections/FAQ";
import MechanicCTA from "@/components/sections/mechanic/MechanicCTA";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) return {};
  const t = await getTranslations({
    locale,
    namespace: "mechanicPage.meta",
  });
  return {
    title: t("title"),
    description: t("description"),
  };
}

export default async function MechanicPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <>
      <MechanicHero />
      <MechanicServices />
      <MechanicHow />
      <MechanicProviderCTA />
      <FAQ namespace="mechanicPage.faq" />
      <MechanicCTA />
    </>
  );
}

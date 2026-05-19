import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { hasLocale } from "next-intl";
import { routing } from "@/i18n/routing";
import DetailersHero from "@/components/sections/detailers/DetailersHero";
import EarningsCalc from "@/components/sections/detailers/EarningsCalc";
import WeekInLife from "@/components/sections/detailers/WeekInLife";
import Tools from "@/components/sections/detailers/Tools";
import Requirements from "@/components/sections/detailers/Requirements";
import DetailersTestimonials from "@/components/sections/detailers/DetailersTestimonials";
import FAQ from "@/components/sections/FAQ";
import DetailersCTA from "@/components/sections/detailers/DetailersCTA";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) return {};
  const t = await getTranslations({
    locale,
    namespace: "detailersPage.meta",
  });
  return {
    title: t("title"),
    description: t("description"),
  };
}

export default async function DetailersPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <>
      <DetailersHero />
      <EarningsCalc />
      <WeekInLife />
      <Tools />
      <Requirements />
      <DetailersTestimonials />
      <FAQ namespace="detailersPage.faq" />
      <DetailersCTA />
    </>
  );
}

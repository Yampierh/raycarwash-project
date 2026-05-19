import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { hasLocale } from "next-intl";
import { routing } from "@/i18n/routing";
import RidersHero from "@/components/sections/riders/RidersHero";
import BookingJourney from "@/components/sections/riders/BookingJourney";
import ServicesCompare from "@/components/sections/riders/ServicesCompare";
import TrustSafety from "@/components/sections/riders/TrustSafety";
import ReviewsWall from "@/components/sections/riders/ReviewsWall";
import FAQ from "@/components/sections/FAQ";
import RidersCTA from "@/components/sections/riders/RidersCTA";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) return {};
  const t = await getTranslations({
    locale,
    namespace: "ridersPage.meta",
  });
  return {
    title: t("title"),
    description: t("description"),
  };
}

export default async function RidersPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <>
      <RidersHero />
      <BookingJourney />
      <ServicesCompare />
      <TrustSafety />
      <ReviewsWall />
      <FAQ namespace="ridersPage.faq" />
      <RidersCTA />
    </>
  );
}

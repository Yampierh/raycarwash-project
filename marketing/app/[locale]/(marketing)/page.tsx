import { setRequestLocale } from "next-intl/server";
import Hero from "@/components/sections/Hero";
import TrustBadges from "@/components/sections/TrustBadges";
import HowItWorks from "@/components/sections/HowItWorks";
import Services from "@/components/sections/Services";
import ForDetailers from "@/components/sections/ForDetailers";
import Testimonials from "@/components/sections/Testimonials";
import FAQ from "@/components/sections/FAQ";
import ContactCTA from "@/components/sections/ContactCTA";

const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL || "https://raycarwash.com";

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  name: "RayCarWash",
  description:
    "Mobile car wash and detailing services in Fort Wayne, Indiana. Book vetted detailers to come to your home or office.",
  url: BASE_URL,
  telephone: "+1-260-XXX-XXXX",
  email: "hello@raycarwash.com",
  address: {
    "@type": "PostalAddress",
    streetAddress: "Fort Wayne, IN",
    addressLocality: "Fort Wayne",
    addressRegion: "IN",
    postalCode: "46802",
    addressCountry: "US",
  },
  areaServed: {
    "@type": "GeoCircle",
    geoMidpoint: {
      "@type": "GeoCoordinates",
      latitude: 41.0793,
      longitude: -85.1394,
    },
    geoRadius: "20000",
  },
  priceRange: "$$",
  openingHours: "Mo-Su 08:00-20:00",
  image: `${BASE_URL}/og-image.png`,
  sameAs: [],
};

export default async function Home({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <Hero />
      <TrustBadges />
      <HowItWorks />
      <Services />
      <ForDetailers />
      <Testimonials />
      <FAQ />
      <ContactCTA />
    </>
  );
}

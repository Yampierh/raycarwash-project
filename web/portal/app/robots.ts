import { routing } from "@/i18n/routing";

const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL || "https://raycarwash.com";

export default function robots() {
  const locales = routing.locales;
  const sitemapUrl = `${BASE_URL}/sitemap.xml`;

  const rules = [
    {
      userAgent: "*",
      allow: "/",
      disallow: ["/api/", "/_next/", "/dashboard/", "/client/", "/detailer/"],
    },
  ];

  const sitemaps = locales.map((locale) => ({
    url: `${BASE_URL}/${locale}/sitemap.xml`,
    lastmod: new Date().toISOString().split("T")[0],
  }));

  return {
    rules,
    sitemaps,
    host: BASE_URL,
  };
}
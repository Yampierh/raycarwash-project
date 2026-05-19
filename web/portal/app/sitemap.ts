import { routing } from "@/i18n/routing";

const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL || "https://raycarwash.com";

export default async function sitemap() {
  const locales = routing.locales;
  const now = new Date().toISOString().split("T")[0];

  const staticPages = [
    "",
    "/about",
    "/contact",
    "/detailers",
    "/login",
    "/signup",
    "/legal/terms",
    "/legal/privacy",
  ];

  const sitemapEntries = [];

  for (const locale of locales) {
    for (const path of staticPages) {
      const url = path === "" ? `/${locale}` : `/${locale}${path}`;
      sitemapEntries.push({
        url: `${BASE_URL}${url}`,
        lastModified: now,
        alternates: {
          languages: {
            en: `${BASE_URL}/en${path}`,
            es: `${BASE_URL}/es${path}`,
          },
        },
      });
    }
  }

  return sitemapEntries;
}
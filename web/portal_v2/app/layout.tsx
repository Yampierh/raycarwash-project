import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "RayCarWash — Mobile Detailing in Fort Wayne, IN", template: "%s | RayCarWash" },
  description: "Book a vetted detailer to your driveway in minutes. Flat-rate pricing, live tracking, and before/after photos.",
  openGraph: { siteName: "RayCarWash", locale: "en_US", type: "website" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

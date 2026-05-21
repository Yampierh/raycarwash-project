import Link from "next/link";
import { Apple, Smartphone } from "lucide-react";

export default function Footer() {
  const cols = [
    { h: "Product", links: [{ l: "How it works", href: "/#how" }, { l: "Services", href: "/#services" }, { l: "Coverage", href: "/#coverage" }, { l: "Pricing", href: "/riders#services" }, { l: "FAQ", href: "/#faq" }] },
    { h: "Company", links: [{ l: "About", href: "/about" }, { l: "Become a detailer", href: "/detailers" }, { l: "Press", href: "/press" }, { l: "Careers", href: "/careers" }, { l: "Contact", href: "/contact" }] },
    { h: "Legal", links: [{ l: "Privacy Policy", href: "/legal/privacy" }, { l: "Terms of Service", href: "/legal/terms" }, { l: "Insurance", href: "/trust/insurance" }, { l: "Cookies", href: "/legal/cookies" }] },
  ];

  return (
    <footer className="footer">
      <div className="container">
        <div className="footer-grid">
          <div className="footer-brand">
            <Link href="/" className="brand">
              <span className="brand-mark">R</span>
              <span className="brand-name">RayCarWash</span>
            </Link>
            <p className="footer-tag">Mobile detailing, on demand.<br />Fort Wayne, IN.</p>
            <div className="footer-stores">
              <a href={process.env.NEXT_PUBLIC_APPSTORE_URL || "#"} className="store-btn">
                <Apple size={20} />
                <div><div className="sb-sm">Download on</div><div className="sb-lg">App Store</div></div>
              </a>
              <a href={process.env.NEXT_PUBLIC_PLAYSTORE_URL || "#"} className="store-btn">
                <Smartphone size={20} />
                <div><div className="sb-sm">Get it on</div><div className="sb-lg">Google Play</div></div>
              </a>
            </div>
          </div>
          {cols.map(c => (
            <div key={c.h} className="footer-col">
              <h4>{c.h}</h4>
              <ul>
                {c.links.map(l => (
                  <li key={l.l}><Link href={l.href}>{l.l}</Link></li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="footer-bottom">
          <div>© 2026 RayCarWash. All rights reserved.</div>
          <div className="footer-locale">EN · USD · Fort Wayne, IN</div>
        </div>
      </div>
    </footer>
  );
}

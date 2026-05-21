"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { Apple, Smartphone, ArrowRight } from "lucide-react";

interface NavbarProps {
  page?: "landing" | "riders" | "detailers" | "mechanic";
  audience?: "client" | "detailer";
  onAudienceChange?: (a: "client" | "detailer") => void;
}

export default function Navbar({ page = "landing", audience = "client", onAudienceChange }: NavbarProps) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 12);
    fn();
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, []);

  const landingLinks = [
    { href: "#how", label: "How it works" },
    { href: "#services", label: "Services" },
    { href: "#coverage", label: "Coverage" },
    { href: "#faq", label: "FAQ" },
  ];
  const detailersLinks = [
    { href: "#earnings", label: "Earnings" },
    { href: "#week", label: "A week" },
    { href: "#tools", label: "Tools" },
    { href: "#requirements", label: "Requirements" },
    { href: "#faq", label: "FAQ" },
  ];
  const mechanicLinks = [
    { href: "#services", label: "Services" },
    { href: "#how", label: "How it'll work" },
    { href: "#waitlist", label: "Waitlist" },
    { href: "#faq", label: "FAQ" },
  ];
  const ridersLinks = [
    { href: "#how", label: "How it works" },
    { href: "#services", label: "Services" },
    { href: "#safety", label: "Safety" },
    { href: "#reviews", label: "Reviews" },
    { href: "#faq", label: "FAQ" },
  ];

  const linkMap = {
    landing: landingLinks,
    riders: ridersLinks,
    detailers: detailersLinks,
    mechanic: mechanicLinks,
  };
  const links = linkMap[page];

  const pages = [
    { href: "/riders", label: "Riders" },
    { href: "/detailers", label: "Detailers" },
    { href: "/mechanic", label: "Mechanic", badge: "new" },
  ].filter(p => {
    if (page === "riders") return p.label !== "Riders";
    if (page === "detailers") return p.label !== "Detailers";
    if (page === "mechanic") return p.label !== "Mechanic";
    return true;
  });

  const brandSub = page === "riders" ? "/ riders" : page === "detailers" ? "/ detailers" : page === "mechanic" ? "/ mechanic" : null;

  return (
    <header className={`nav${scrolled ? " nav-scrolled" : ""}`}>
      <div className="nav-inner">
        <Link href="/" className="brand">
          <span className="brand-mark">R</span>
          <span className="brand-name">RayCarWash</span>
          {brandSub && <span className="brand-sub">{brandSub}</span>}
        </Link>

        <nav className="nav-links">
          {links.map(l => (
            <a key={l.href} href={l.href}>{l.label}</a>
          ))}
          <span className="nav-sep" />
          {pages.map(p => (
            <Link key={p.href} href={p.href} className="nav-page">
              {p.label}
              {"badge" in p && p.badge && <span className="nav-badge">{p.badge}</span>}
            </Link>
          ))}
        </nav>

        <div className="nav-right">
          {page === "landing" && onAudienceChange && (
            <div className="aud-toggle nav-aud">
              <button className={audience === "client" ? "on" : ""} onClick={() => onAudienceChange("client")}>Riders</button>
              <button className={audience === "detailer" ? "on" : ""} onClick={() => onAudienceChange("detailer")}>Detailers</button>
            </div>
          )}
          {page === "detailers" ? (
            <Link href="/signup" className="btn btn-accent btn-sm">Apply to detail</Link>
          ) : page === "mechanic" ? (
            <a href="#waitlist" className="btn btn-dark btn-sm">Join waitlist</a>
          ) : (
            <>
              <Link href="/login" className="link-quiet">Log in</Link>
              <Link href="/signup" className="btn btn-dark btn-sm">Get the app</Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

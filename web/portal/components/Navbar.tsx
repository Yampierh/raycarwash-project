"use client";

import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import LanguageSwitcher from "./LanguageSwitcher";
import { useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/lib/store/auth";
import { useAudienceStore } from "@/lib/store/audience";
import { ChevronDown, Menu, X } from "lucide-react";

export type NavbarVariant = "landing" | "riders" | "detailers" | "mechanic";

interface NavbarProps {
  variant?: NavbarVariant;
}

function detectVariant(pathname: string): NavbarVariant {
  if (pathname.startsWith("/riders")) return "riders";
  if (pathname.startsWith("/detailers")) return "detailers";
  if (pathname.startsWith("/mechanic")) return "mechanic";
  return "landing";
}

interface NavLink {
  href: string;
  label: string;
}

export default function Navbar({ variant: variantProp }: NavbarProps = {}) {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const variant = variantProp ?? detectVariant(pathname);
  const audience = useAudienceStore((s) => s.audience);
  const setAudience = useAudienceStore((s) => s.setAudience);
  const hydrated = useAuthStore((s) => s.hydrated);
  const isAuthed = useAuthStore((s) => s.isAuthenticated());
  const role = useAuthStore((s) => s.role);
  const clear = useAuthStore((s) => s.clear);

  const [menuOpen, setMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  function handleSignOut() {
    clear();
    setProfileOpen(false);
  }

  const subBrand = useTranslations(
    variant === "riders"
      ? "ridersPage"
      : variant === "detailers"
        ? "detailersPage"
        : variant === "mechanic"
          ? "mechanicPage"
          : "nav",
  );

  const subBrandLabel =
    variant === "landing" ? null : subBrand("navBrandSub");

  const primary: NavLink[] = (() => {
    if (variant === "riders") {
      const r = subBrand;
      return [
        { href: "#how", label: r("navLinks.how") },
        { href: "#services", label: r("navLinks.services") },
        { href: "#safety", label: r("navLinks.safety") },
        { href: "#reviews", label: r("navLinks.reviews") },
        { href: "#faq", label: r("navLinks.faq") },
      ];
    }
    if (variant === "detailers") {
      const r = subBrand;
      return [
        { href: "#earnings", label: r("navLinks.earnings") },
        { href: "#week", label: r("navLinks.week") },
        { href: "#tools", label: r("navLinks.tools") },
        { href: "#requirements", label: r("navLinks.requirements") },
        { href: "#faq", label: r("navLinks.faq") },
      ];
    }
    if (variant === "mechanic") {
      const r = subBrand;
      return [
        { href: "#services", label: r("navLinks.services") },
        { href: "#how", label: r("navLinks.how") },
        { href: "#waitlist", label: r("navLinks.waitlist") },
        { href: "#faq", label: r("navLinks.faq") },
      ];
    }
    return [
      { href: "/#how", label: t("how") },
      { href: "/#services", label: t("services") },
      { href: "/#coverage", label: t("coverage") },
      { href: "/#faq", label: t("faq") },
    ];
  })();

  const pages: { href: string; label: string; badge?: string }[] = (() => {
    const all: { key: NavbarVariant; href: string; label: string; badge?: string }[] = [
      { key: "riders", href: "/riders", label: t("pageRiders") },
      { key: "detailers", href: "/detailers", label: t("pageDetailers") },
      {
        key: "mechanic",
        href: "/mechanic",
        label: t("pageMechanic"),
        badge: t("newBadge"),
      },
    ];
    return all.filter((p) => p.key !== variant);
  })();

  const showAuthState = hydrated && isAuthed;

  const rightCta: { href: string; label: string; tone: "dark" | "accent" } =
    (() => {
      if (variant === "detailers")
        return { href: "#apply", label: subBrand("hero.ctaApply"), tone: "accent" };
      if (variant === "mechanic")
        return { href: "#waitlist", label: subBrand("ctaJoin"), tone: "dark" };
      return { href: "/signup", label: t("getApp"), tone: "dark" };
    })();

  return (
    <header
      className={`sticky top-0 z-40 transition-all ${
        scrolled
          ? "border-b border-ink-150 bg-white/85 backdrop-blur-md"
          : "border-b border-transparent bg-white/70 backdrop-blur"
      }`}
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3.5">
        <Link href={variant === "landing" ? "/" : "/"} className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-ink-900 text-sm font-bold text-white">
            R
          </span>
          <span className="font-display text-lg font-bold tracking-tight text-ink-900">
            RayCarWash
          </span>
          {subBrandLabel && (
            <span className="ml-1 hidden font-mono text-xs font-medium text-ink-400 md:inline">
              {subBrandLabel}
            </span>
          )}
        </Link>

        <nav className="hidden items-center gap-1 lg:flex">
          {primary.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="rounded-md px-3 py-1.5 text-sm font-medium text-ink-600 transition hover:bg-ink-50 hover:text-ink-900"
            >
              {l.label}
            </a>
          ))}
          <span className="mx-2 h-4 w-px bg-ink-200" />
          {pages.map((p) => (
            <Link
              key={p.href}
              href={p.href}
              className="inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium text-ink-600 transition hover:bg-ink-50 hover:text-ink-900"
            >
              {p.label}
              {p.badge && (
                <span className="rounded-full bg-brand-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-brand-700">
                  {p.badge}
                </span>
              )}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          {variant === "landing" && (
            <div className="inline-flex items-center rounded-full border border-ink-200 bg-white p-0.5 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setAudience("client")}
                className={`rounded-full px-3 py-1 transition ${
                  audience === "client"
                    ? "bg-ink-900 text-white"
                    : "text-ink-600 hover:text-ink-900"
                }`}
              >
                {t("audienceRiders")}
              </button>
              <button
                type="button"
                onClick={() => setAudience("detailer")}
                className={`rounded-full px-3 py-1 transition ${
                  audience === "detailer"
                    ? "bg-ink-900 text-white"
                    : "text-ink-600 hover:text-ink-900"
                }`}
              >
                {t("audienceDetailers")}
              </button>
            </div>
          )}
          <LanguageSwitcher />
          {showAuthState ? (
            <div ref={profileRef} className="relative">
              <button
                type="button"
                onClick={() => setProfileOpen((v) => !v)}
                className="inline-flex items-center gap-2 rounded-lg border border-ink-200 bg-white px-3 py-1.5 text-sm font-medium text-ink-700 transition hover:bg-ink-50"
                aria-expanded={profileOpen}
              >
                <span className="flex size-6 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">
                  {(role ?? "U").slice(0, 1).toUpperCase()}
                </span>
                <ChevronDown className="size-3.5 text-ink-400" />
              </button>
              {profileOpen && (
                <ul className="absolute right-0 top-full z-50 mt-2 w-48 overflow-hidden rounded-lg border border-ink-200 bg-white py-1 shadow-lg">
                  <li>
                    <Link
                      href="/dashboard"
                      onClick={() => setProfileOpen(false)}
                      className="block px-3 py-2 text-sm text-ink-700 hover:bg-ink-50"
                    >
                      {t("dashboard")}
                    </Link>
                  </li>
                  <li>
                    <button
                      type="button"
                      onClick={handleSignOut}
                      className="block w-full px-3 py-2 text-left text-sm text-ink-700 hover:bg-ink-50"
                    >
                      {t("logout")}
                    </button>
                  </li>
                </ul>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                href="/login"
                className="text-sm font-medium text-ink-700 hover:text-ink-900"
              >
                {t("login")}
              </Link>
              <a
                href={rightCta.href}
                className={`inline-flex items-center justify-center rounded-lg px-4 py-1.5 text-sm font-semibold shadow-sm transition ${
                  rightCta.tone === "accent"
                    ? "bg-brand-600 text-white hover:bg-brand-700"
                    : "bg-ink-900 text-white hover:bg-ink-800"
                }`}
              >
                {rightCta.label}
              </a>
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={() => setMenuOpen((v) => !v)}
          className="inline-flex size-9 items-center justify-center rounded-lg border border-ink-200 bg-white text-ink-700 md:hidden"
          aria-label="Menu"
        >
          {menuOpen ? <X className="size-4" /> : <Menu className="size-4" />}
        </button>
      </div>

      {menuOpen && (
        <div className="border-t border-ink-150 bg-white lg:hidden">
          <div className="mx-auto flex max-w-6xl flex-col gap-1 px-6 py-4">
            {primary.map((l) => (
              <a
                key={l.href}
                href={l.href}
                onClick={() => setMenuOpen(false)}
                className="rounded-lg px-3 py-2 text-sm font-medium text-ink-700 hover:bg-ink-50"
              >
                {l.label}
              </a>
            ))}
            <div className="mt-2 border-t border-ink-150 pt-2">
              {pages.map((p) => (
                <Link
                  key={p.href}
                  href={p.href}
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium text-ink-700 hover:bg-ink-50"
                >
                  {p.label}
                  {p.badge && (
                    <span className="rounded-full bg-brand-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-brand-700">
                      {p.badge}
                    </span>
                  )}
                </Link>
              ))}
            </div>
            <div className="mt-3 flex items-center justify-between border-t border-ink-150 pt-3">
              <LanguageSwitcher />
              {showAuthState ? (
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="rounded-lg border border-ink-200 px-4 py-1.5 text-sm font-medium text-ink-700"
                >
                  {t("logout")}
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <Link
                    href="/login"
                    onClick={() => setMenuOpen(false)}
                    className="text-sm font-medium text-ink-700"
                  >
                    {t("login")}
                  </Link>
                  <a
                    href={rightCta.href}
                    onClick={() => setMenuOpen(false)}
                    className={`rounded-lg px-4 py-1.5 text-sm font-semibold ${
                      rightCta.tone === "accent"
                        ? "bg-brand-600 text-white"
                        : "bg-ink-900 text-white"
                    }`}
                  >
                    {rightCta.label}
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

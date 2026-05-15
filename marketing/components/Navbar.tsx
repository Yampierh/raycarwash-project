"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import LanguageSwitcher from "./LanguageSwitcher";
import { useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/lib/store/auth";
import { ChevronDown, Menu, X } from "lucide-react";

export default function Navbar() {
  const t = useTranslations("nav");
  const hydrated = useAuthStore((s) => s.hydrated);
  const isAuthed = useAuthStore((s) => s.isAuthenticated());
  const role = useAuthStore((s) => s.role);
  const clear = useAuthStore((s) => s.clear);

  const [menuOpen, setMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
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

  function handleSignOut() {
    clear();
    setProfileOpen(false);
  }

  const navLinks = [
    { href: "/#how", label: t("how") },
    { href: "/#services", label: t("services") },
    { href: "/about", label: t("about") },
    { href: "/contact", label: t("contact") },
    { href: "/detailers", label: t("detailers") },
  ];

  const showAuthState = hydrated && isAuthed;

  return (
    <header className="sticky top-0 z-40 border-b border-zinc-200 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-6 py-4">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-zinc-900 text-sm font-bold text-white">
            R
          </span>
          <span className="font-display text-lg font-bold tracking-tight text-zinc-900">
            RayCarWash
          </span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {navLinks.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-sm font-medium text-zinc-600 transition hover:text-zinc-900"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <LanguageSwitcher />
          {showAuthState ? (
            <div ref={profileRef} className="relative">
              <button
                type="button"
                onClick={() => setProfileOpen((v) => !v)}
                className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-sm font-medium text-zinc-700 transition hover:bg-zinc-50"
                aria-expanded={profileOpen}
              >
                <span className="flex size-6 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">
                  {(role ?? "U").slice(0, 1).toUpperCase()}
                </span>
                <ChevronDown className="size-3.5 text-zinc-400" />
              </button>
              {profileOpen && (
                <ul className="absolute right-0 top-full z-50 mt-2 w-48 overflow-hidden rounded-lg border border-zinc-200 bg-white py-1 shadow-lg">
                  <li>
                    <Link
                      href="/dashboard"
                      onClick={() => setProfileOpen(false)}
                      className="block px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50"
                    >
                      {t("dashboard")}
                    </Link>
                  </li>
                  <li>
                    <button
                      type="button"
                      onClick={handleSignOut}
                      className="block w-full px-3 py-2 text-left text-sm text-zinc-700 hover:bg-zinc-50"
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
                className="text-sm font-medium text-zinc-700 hover:text-zinc-900"
              >
                {t("login")}
              </Link>
              <Link
                href="/signup"
                className="inline-flex items-center justify-center rounded-lg bg-zinc-900 px-4 py-1.5 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800"
              >
                {t("signup")}
              </Link>
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={() => setMenuOpen((v) => !v)}
          className="inline-flex size-9 items-center justify-center rounded-lg border border-zinc-200 bg-white text-zinc-700 md:hidden"
          aria-label="Menu"
        >
          {menuOpen ? <X className="size-4" /> : <Menu className="size-4" />}
        </button>
      </div>

      {menuOpen && (
        <div className="border-t border-zinc-200 bg-white md:hidden">
          <div className="mx-auto flex max-w-6xl flex-col gap-1 px-6 py-4">
            {navLinks.map((l) => (
              <a
                key={l.href}
                href={l.href}
                onClick={() => setMenuOpen(false)}
                className="rounded-lg px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
              >
                {l.label}
              </a>
            ))}
            <div className="mt-3 flex items-center justify-between border-t border-zinc-200 pt-3">
              <LanguageSwitcher />
              {showAuthState ? (
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="rounded-lg border border-zinc-200 px-4 py-1.5 text-sm font-medium text-zinc-700"
                >
                  {t("logout")}
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <Link
                    href="/login"
                    onClick={() => setMenuOpen(false)}
                    className="text-sm font-medium text-zinc-700"
                  >
                    {t("login")}
                  </Link>
                  <Link
                    href="/signup"
                    onClick={() => setMenuOpen(false)}
                    className="rounded-lg bg-zinc-900 px-4 py-1.5 text-sm font-semibold text-white"
                  >
                    {t("signup")}
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

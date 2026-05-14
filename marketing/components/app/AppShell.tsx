"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { useRouter, usePathname, Link } from "@/i18n/navigation";
import { useAuthStore } from "@/lib/store/auth";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import { Button } from "@/components/forms/Button";
import {
  Home,
  Car,
  Calendar,
  User,
  Wrench,
  ListTodo,
  DollarSign,
  LogOut,
  Menu,
} from "lucide-react";
import { useState } from "react";
import clsx from "clsx";

type NavLink = {
  href: "/client/home" | "/client/vehicles" | "/client/appointments" | "/client/profile" | "/detailer/home" | "/detailer/services" | "/detailer/profile" | "/detailer/earnings";
  label: string;
  icon: React.ComponentType<{ className?: string }>;
};

export default function AppShell({ children }: { children: React.ReactNode }) {
  const t = useTranslations("app");
  const router = useRouter();
  const pathname = usePathname();
  const hydrated = useAuthStore((s) => s.hydrated);
  const isAuthed = useAuthStore((s) => s.isAuthenticated());
  const activeRole = useAuthStore((s) => s.activeRole);
  const clear = useAuthStore((s) => s.clear);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (hydrated && !isAuthed) router.replace("/login");
  }, [hydrated, isAuthed, router]);

  if (!hydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50">
        <div className="size-8 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900" />
      </div>
    );
  }
  if (!isAuthed) return null;

  const isDetailer = activeRole === "detailer";

  const links: NavLink[] = isDetailer
    ? [
        { href: "/detailer/home", label: t("nav.jobs"), icon: ListTodo },
        { href: "/detailer/services", label: t("nav.services"), icon: Wrench },
        {
          href: "/detailer/earnings",
          label: t("nav.earnings"),
          icon: DollarSign,
        },
        { href: "/detailer/profile", label: t("nav.profile"), icon: User },
      ]
    : [
        { href: "/client/home", label: t("nav.home"), icon: Home },
        { href: "/client/vehicles", label: t("nav.vehicles"), icon: Car },
        {
          href: "/client/appointments",
          label: t("nav.appointments"),
          icon: Calendar,
        },
        { href: "/client/profile", label: t("nav.profile"), icon: User },
      ];

  function handleSignOut() {
    clear();
    router.replace("/");
  }

  return (
    <div className="flex min-h-screen bg-zinc-50">
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-40 w-64 border-r border-zinc-200 bg-white transition-transform md:static md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-16 items-center gap-2 border-b border-zinc-200 px-6">
          <Link href="/" className="flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-lg bg-zinc-900 text-sm font-bold text-white">
              R
            </span>
            <span className="font-display text-base font-bold tracking-tight text-zinc-900">
              RayCarWash
            </span>
          </Link>
        </div>

        <nav className="flex flex-col gap-1 p-4">
          {links.map((l) => {
            const active = pathname === l.href;
            const Icon = l.icon;
            return (
              <Link
                key={l.href}
                href={l.href}
                onClick={() => setMobileOpen(false)}
                className={clsx(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition",
                  active
                    ? "bg-zinc-900 text-white"
                    : "text-zinc-700 hover:bg-zinc-100"
                )}
              >
                <Icon className="size-4" />
                {l.label}
              </Link>
            );
          })}
        </nav>

        <div className="absolute inset-x-0 bottom-0 border-t border-zinc-200 p-4">
          <button
            type="button"
            onClick={handleSignOut}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-zinc-700 transition hover:bg-zinc-100"
          >
            <LogOut className="size-4" />
            {t("signOut")}
          </button>
        </div>
      </aside>

      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-zinc-900/40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-4 border-b border-zinc-200 bg-white px-6">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="inline-flex size-9 items-center justify-center rounded-lg border border-zinc-200 text-zinc-700 md:hidden"
            aria-label="Menu"
          >
            <Menu className="size-4" />
          </button>
          <div className="flex-1" />
          <LanguageSwitcher />
        </header>

        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}

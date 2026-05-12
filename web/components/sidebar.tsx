"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearTokens } from "@/lib/auth";

const NAV = [
  { href: "/dashboard", label: "Overview", icon: "⬡" },
  { href: "/dashboard/users", label: "Users", icon: "👥" },
  { href: "/dashboard/roles", label: "Roles", icon: "🔑" },
  { href: "/dashboard/permissions", label: "Permissions", icon: "🛡" },
  { href: "/dashboard/appointments", label: "Appointments", icon: "📅" },
  { href: "/dashboard/verifications", label: "Verifications", icon: "✓" },
  { href: "/dashboard/payments", label: "Payments", icon: "💳" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    clearTokens();
    router.push("/login");
  }

  return (
    <aside className="w-56 min-h-screen bg-zinc-900 border-r border-zinc-800 flex flex-col">
      <div className="px-5 py-6 border-b border-zinc-800">
        <p className="font-bold text-white text-sm">RayCarwash</p>
        <p className="text-zinc-500 text-xs mt-0.5">Admin Console</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ href, label, icon }) => {
          const active =
            href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-zinc-800 text-white"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-800/50"
              }`}
            >
              <span>{icon}</span>
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="px-3 py-4 border-t border-zinc-800">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:text-white hover:bg-zinc-800/50 transition-colors"
        >
          <span>→</span>
          Sign out
        </button>
      </div>
    </aside>
  );
}

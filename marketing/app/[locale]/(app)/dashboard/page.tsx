"use client";

import { useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useAuthStore } from "@/lib/store/auth";
import { resolveActiveRole } from "@/lib/auth-flow";

export default function DashboardRedirect() {
  const router = useRouter();
  const hydrated = useAuthStore((s) => s.hydrated);
  const roles = useAuthStore((s) => s.roles);
  const activeRole = useAuthStore((s) => s.activeRole);
  const roleIntent = useAuthStore((s) => s.roleIntent);
  const setSession = useAuthStore((s) => s.setSession);
  const clear = useAuthStore((s) => s.clear);

  useEffect(() => {
    if (!hydrated) return;

    if (roles.includes("admin")) {
      const adminUrl =
        process.env.NEXT_PUBLIC_ADMIN_URL ?? "http://localhost:3000";
      window.location.href = `${adminUrl}/dashboard`;
      return;
    }

    if (activeRole === "detailer") {
      router.replace("/detailer/home");
      return;
    }
    if (activeRole === "client") {
      router.replace("/client/home");
      return;
    }

    // No activeRole set yet. For single-role users we can auto-assign;
    // for multi-role users without an intent we don't know — bounce to login.
    if (roles.length === 1) {
      const next = resolveActiveRole(roles, roleIntent);
      if (next) {
        setSession({ active_role: next });
        return;
      }
    }

    clear();
    router.replace("/login");
  }, [
    hydrated,
    roles,
    activeRole,
    roleIntent,
    setSession,
    clear,
    router,
  ]);

  return (
    <div className="flex min-h-[calc(100vh-100px)] items-center justify-center">
      <div className="size-8 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900" />
    </div>
  );
}

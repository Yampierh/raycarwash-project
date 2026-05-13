"use client";

import { useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useAuthStore } from "@/lib/store/auth";
import { effectiveRoleOf } from "@/lib/auth";

export default function ClientLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const hydrated = useAuthStore((s) => s.hydrated);
  const roles = useAuthStore((s) => s.roles);
  const effective = effectiveRoleOf(roles);

  useEffect(() => {
    if (!hydrated || roles.length === 0) return;
    if (effective === "detailer") {
      router.replace("/detailer/home");
    } else if (effective === "admin") {
      const adminUrl =
        process.env.NEXT_PUBLIC_ADMIN_URL ?? "http://localhost:3000";
      window.location.href = `${adminUrl}/dashboard`;
    }
    // role === "client" or null (not yet authed): let AppShell handle.
  }, [hydrated, effective, roles.length, router]);

  if (!hydrated) return null;
  if (roles.length > 0 && effective !== "client") return null;
  return <>{children}</>;
}

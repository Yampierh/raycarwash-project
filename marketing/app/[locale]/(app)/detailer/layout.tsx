"use client";

import { useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useAuthStore } from "@/lib/store/auth";

export default function DetailerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const hydrated = useAuthStore((s) => s.hydrated);
  const roles = useAuthStore((s) => s.roles);
  const activeRole = useAuthStore((s) => s.activeRole);

  useEffect(() => {
    if (!hydrated || roles.length === 0) return;
    if (activeRole === "client") {
      router.replace("/client/home");
    } else if (activeRole === "admin") {
      const adminUrl =
        process.env.NEXT_PUBLIC_ADMIN_URL ?? "http://localhost:3000";
      window.location.href = `${adminUrl}/dashboard`;
    }
  }, [hydrated, activeRole, roles.length, router]);

  if (!hydrated) return null;
  if (roles.length > 0 && activeRole && activeRole !== "detailer") return null;
  return <>{children}</>;
}

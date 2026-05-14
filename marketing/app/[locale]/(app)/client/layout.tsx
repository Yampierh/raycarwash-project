"use client";

import { useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useAuthStore } from "@/lib/store/auth";

export default function ClientLayout({
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
    if (activeRole === "detailer") {
      router.replace("/detailer/home");
    } else if (activeRole === "admin") {
      const adminUrl =
        process.env.NEXT_PUBLIC_ADMIN_URL ?? "http://localhost:3000";
      window.location.href = `${adminUrl}/dashboard`;
    }
    // activeRole === "client" or null: render — null usually means
    // a single-role user where /dashboard will set activeRole on the fly.
  }, [hydrated, activeRole, roles.length, router]);

  if (!hydrated) return null;
  if (roles.length > 0 && activeRole && activeRole !== "client") return null;
  return <>{children}</>;
}

"use client";

import { useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useAuthStore } from "@/lib/store/auth";

export default function DashboardRedirect() {
  const router = useRouter();
  const hydrated = useAuthStore((s) => s.hydrated);
  const role = useAuthStore((s) => s.role);

  useEffect(() => {
    if (!hydrated) return;
    if (role === "detailer") {
      router.replace("/detailer/home");
    } else if (role === "admin") {
      const adminUrl =
        process.env.NEXT_PUBLIC_ADMIN_URL ?? "http://localhost:3000";
      window.location.href = `${adminUrl}/dashboard`;
    } else {
      router.replace("/client/home");
    }
  }, [hydrated, role, router]);

  return (
    <div className="flex min-h-[calc(100vh-100px)] items-center justify-center">
      <div className="size-8 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900" />
    </div>
  );
}

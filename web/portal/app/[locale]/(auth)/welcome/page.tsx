"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { useAuthStore } from "@/lib/store/auth";
import { Button } from "@/components/forms/Button";
import { CheckCircle2 } from "lucide-react";

export default function WelcomePage() {
  const t = useTranslations("welcome");
  const router = useRouter();
  const hydrated = useAuthStore((s) => s.hydrated);
  const isAuthed = useAuthStore((s) => s.isAuthenticated());
  const clear = useAuthStore((s) => s.clear);

  useEffect(() => {
    if (hydrated && !isAuthed) router.replace("/login");
  }, [hydrated, isAuthed, router]);

  if (!hydrated || !isAuthed) return null;

  const appStore = process.env.NEXT_PUBLIC_APPSTORE_URL ?? "#";
  const playStore = process.env.NEXT_PUBLIC_PLAYSTORE_URL ?? "#";

  return (
    <div className="flex min-h-[calc(100vh-200px)] items-center justify-center px-6 py-16">
      <div className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-10 text-center shadow-sm">
        <span className="mx-auto flex size-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
          <CheckCircle2 className="size-7" strokeWidth={2} />
        </span>
        <h1 className="mt-6 font-display text-3xl font-bold tracking-tight text-zinc-900">
          {t("title")}
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-zinc-600">{t("sub")}</p>

        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <a
            href={appStore}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800"
          >
            App Store
          </a>
          <a
            href={playStore}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800"
          >
            Google Play
          </a>
        </div>

        <Button
          variant="ghost"
          size="sm"
          className="mt-6 mx-auto"
          onClick={() => {
            clear();
            router.replace("/");
          }}
        >
          {t("signOut")}
        </Button>
      </div>
    </div>
  );
}

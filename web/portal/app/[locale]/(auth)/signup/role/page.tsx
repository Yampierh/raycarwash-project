"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { useAuthStore } from "@/lib/store/auth";
import {
  saveSignupRole,
  getSignupRole,
  type SignupRole,
} from "@/lib/auth-flow";
import { User, Wrench, ArrowRight } from "lucide-react";
import { Button } from "@/components/forms/Button";
import clsx from "clsx";

export default function SignupRolePage() {
  const t = useTranslations("signupRole");
  const router = useRouter();
  const hydrated = useAuthStore((s) => s.hydrated);
  const onboardingToken = useAuthStore((s) => s.onboardingToken);
  const accessToken = useAuthStore((s) => s.accessToken);

  const [selected, setSelected] = useState<SignupRole | null>(null);

  useEffect(() => {
    if (!hydrated) return;
    if (!onboardingToken && !accessToken) {
      router.replace("/signup");
      return;
    }
    // The signup toggle already captured the choice — skip this step.
    if (getSignupRole()) {
      router.replace("/onboarding");
    }
  }, [hydrated, onboardingToken, accessToken, router]);

  function handleContinue() {
    if (!selected) return;
    saveSignupRole(selected);
    router.push("/onboarding");
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center px-6 py-16">
      <div className="text-center">
        <h1 className="font-display text-3xl font-bold tracking-tight text-zinc-900">
          {t("title")}
        </h1>
        <p className="mt-2 text-sm text-zinc-600">{t("sub")}</p>
      </div>

      <div className="mt-10 grid w-full gap-4 sm:grid-cols-2">
        <RoleCard
          icon={<User className="size-6" />}
          title={t("client.title")}
          body={t("client.body")}
          selected={selected === "client"}
          onSelect={() => setSelected("client")}
        />
        <RoleCard
          icon={<Wrench className="size-6" />}
          title={t("detailer.title")}
          body={t("detailer.body")}
          selected={selected === "detailer"}
          onSelect={() => setSelected("detailer")}
        />
      </div>

      <Button
        size="lg"
        className="mt-10"
        disabled={!selected}
        onClick={handleContinue}
      >
        {t("continue")}
        <ArrowRight className="size-4" />
      </Button>
    </div>
  );
}

function RoleCard({
  icon,
  title,
  body,
  selected,
  onSelect,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={clsx(
        "flex flex-col rounded-2xl border-2 bg-white p-6 text-left transition",
        selected
          ? "border-brand-600 ring-4 ring-brand-500/15"
          : "border-zinc-200 hover:border-zinc-300"
      )}
    >
      <span
        className={clsx(
          "flex size-12 items-center justify-center rounded-xl",
          selected
            ? "bg-brand-600 text-white"
            : "bg-zinc-100 text-zinc-600"
        )}
      >
        {icon}
      </span>
      <h3 className="mt-4 text-lg font-semibold text-zinc-900">{title}</h3>
      <p className="mt-2 text-sm text-zinc-600">{body}</p>
    </button>
  );
}

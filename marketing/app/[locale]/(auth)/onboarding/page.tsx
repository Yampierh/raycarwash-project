"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { completeProfile } from "@/lib/api/auth-client";
import { useAuthStore } from "@/lib/store/auth";
import { getSignupRole, clearSignupRole } from "@/lib/auth-flow";
import { Input } from "@/components/forms/Input";
import { Button } from "@/components/forms/Button";
import { FormError } from "@/components/forms/FormError";

const schema = z.object({
  full_name: z.string().min(2, "At least 2 characters"),
  phone_number: z
    .string()
    .min(7, "Phone number too short")
    .regex(/^[+0-9 ()\-]+$/, "Invalid phone format"),
});
type FormValues = z.infer<typeof schema>;

export default function OnboardingPage() {
  const t = useTranslations("onboarding");
  const router = useRouter();
  const setSession = useAuthStore((s) => s.setSession);
  const hydrated = useAuthStore((s) => s.hydrated);
  const onboardingToken = useAuthStore((s) => s.onboardingToken);
  const accessToken = useAuthStore((s) => s.accessToken);
  const [error, setError] = useState<string | null>(null);
  const [role, setRole] = useState<"client" | "detailer" | null>(null);

  useEffect(() => {
    if (!hydrated) return;
    if (!onboardingToken && !accessToken) {
      router.replace("/signup");
      return;
    }
    setRole(getSignupRole());
  }, [hydrated, onboardingToken, accessToken, router]);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setError(null);
    try {
      const data = await completeProfile({
        full_name: values.full_name,
        phone_number: values.phone_number,
        service_type: role === "detailer" ? "detailer" : null,
      });
      setSession({
        access_token: data.access_token ?? null,
        refresh_token: data.refresh_token ?? null,
        onboarding_token: null,
        next_step: data.next_step ?? null,
      });
      clearSignupRole();
      if (role === "detailer") {
        router.push("/onboarding/detailer");
      } else {
        router.push("/dashboard");
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("error");
      setError(typeof msg === "string" ? msg : t("error"));
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-200px)] items-center justify-center px-6 py-16">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="font-display text-3xl font-bold tracking-tight text-zinc-900">
            {t("title")}
          </h1>
          <p className="mt-2 text-sm text-zinc-600">{t("sub")}</p>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm"
        >
          <Input
            label={t("fullName")}
            placeholder={t("fullNamePlaceholder")}
            autoComplete="name"
            error={errors.full_name?.message}
            {...register("full_name")}
          />
          <Input
            label={t("phone")}
            type="tel"
            placeholder={t("phonePlaceholder")}
            autoComplete="tel"
            error={errors.phone_number?.message}
            {...register("phone_number")}
          />

          {role && (
            <p className="rounded-lg bg-zinc-50 px-3 py-2 text-xs text-zinc-600">
              {t("signingUpAs", { role: role === "detailer" ? t("roleDetailer") : t("roleClient") })}
            </p>
          )}

          <FormError message={error} />
          <Button type="submit" loading={isSubmitting} className="w-full">
            {isSubmitting ? t("submitting") : t("submit")}
          </Button>
        </form>
      </div>
    </div>
  );
}

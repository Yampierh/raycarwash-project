"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter, Link } from "@/i18n/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { register as registerUser, googleLogin } from "@/lib/api/auth-client";
import { useAuthStore } from "@/lib/store/auth";
import {
  resolvePostAuthPath,
  resolveActiveRole,
  saveSignupRole,
} from "@/lib/auth-flow";
import { Input } from "@/components/forms/Input";
import { Button } from "@/components/forms/Button";
import { FormError } from "@/components/forms/FormError";
import GoogleButton from "@/components/auth/GoogleButton";
import RoleToggle from "@/components/auth/RoleToggle";

const schema = z.object({
  email: z.email("Invalid email address"),
  password: z
    .string()
    .min(8, "At least 8 characters")
    .regex(/[0-9]/, "Must contain a number"),
});
type FormValues = z.infer<typeof schema>;

export default function SignupPage() {
  const t = useTranslations("signup");
  const router = useRouter();
  const setSession = useAuthStore((s) => s.setSession);
  const roleIntent = useAuthStore((s) => s.roleIntent);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setError(null);
    try {
      const data = await registerUser(values.email, values.password);
      const intent = roleIntent ?? "client";
      // Persist the picked role for /onboarding to read as service_type.
      saveSignupRole(intent);
      setSession({
        access_token: data.access_token ?? null,
        refresh_token: data.refresh_token ?? null,
        onboarding_token: data.onboarding_token ?? null,
        roles: data.roles ?? [],
        next_step: data.next_step ?? null,
      });
      // Skip /signup/role because the toggle already captured the choice.
      router.push("/onboarding");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("error");
      setError(typeof msg === "string" ? msg : t("error"));
    }
  }

  async function handleGoogle(args: {
    code: string;
    code_verifier: string;
    redirect_uri: string;
  }) {
    setError(null);
    try {
      const data = await googleLogin(args);
      const roles = data.roles ?? [];
      const intent = roleIntent ?? "client";

      if (data.is_new_user) {
        saveSignupRole(intent);
        setSession({
          access_token: data.access_token ?? null,
          refresh_token: data.refresh_token ?? null,
          onboarding_token: data.onboarding_token ?? null,
          roles,
          next_step: data.next_step ?? null,
        });
        router.push("/onboarding");
        return;
      }

      // Existing user via Google — validate intent against roles.
      if (!roles.includes("admin") && roles.length > 0 && !roles.includes(intent)) {
        setError(t("error"));
        return;
      }
      const active = resolveActiveRole(roles, intent);
      setSession({
        access_token: data.access_token ?? null,
        refresh_token: data.refresh_token ?? null,
        onboarding_token: data.onboarding_token ?? null,
        roles,
        active_role: active,
        next_step: data.next_step ?? null,
      });
      const { path, externalAdmin } = resolvePostAuthPath(data);
      if (externalAdmin) {
        window.location.href = `${process.env.NEXT_PUBLIC_ADMIN_URL ?? ""}${path}`;
        return;
      }
      router.push(path);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("error");
      setError(typeof msg === "string" ? msg : t("error"));
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-200px)] items-center justify-center px-6 py-16">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="font-display text-3xl font-bold tracking-tight text-zinc-900">
            {t("title")}
          </h1>
          <p className="mt-2 text-sm text-zinc-600">{t("sub")}</p>
        </div>

        <div className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm">
          <RoleToggle labelKey="signUpAs" />

          <GoogleButton
            label={t("continueGoogle")}
            onSuccess={handleGoogle}
            onError={() => setError(t("error"))}
            disabled={isSubmitting}
          />

          {process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID && (
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-zinc-200" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-white px-2 text-zinc-400">
                  {t("orDivider")}
                </span>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              type="email"
              autoComplete="email"
              label={t("email")}
              placeholder={t("emailPlaceholder")}
              error={errors.email?.message}
              {...register("email")}
            />
            <Input
              type="password"
              autoComplete="new-password"
              label={t("password")}
              placeholder="••••••••"
              hint={t("passwordHint")}
              error={errors.password?.message}
              {...register("password")}
            />
            <FormError message={error} />
            <Button type="submit" loading={isSubmitting} className="w-full">
              {isSubmitting ? t("submitting") : t("submit")}
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-zinc-600">
          {t("haveAccount")}{" "}
          <Link
            href="/login"
            className="font-medium text-zinc-900 underline-offset-4 hover:underline"
          >
            {t("loginCta")}
          </Link>
        </p>
      </div>
    </div>
  );
}

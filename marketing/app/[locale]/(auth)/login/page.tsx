"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter, Link } from "@/i18n/navigation";
import { login, googleLogin } from "@/lib/api/auth-client";
import { useAuthStore } from "@/lib/store/auth";
import { resolvePostAuthPath } from "@/lib/auth-flow";
import { Input } from "@/components/forms/Input";
import { Button } from "@/components/forms/Button";
import { FormError } from "@/components/forms/FormError";
import GoogleButton from "@/components/auth/GoogleButton";

export default function LoginPage() {
  const t = useTranslations("login");
  const router = useRouter();
  const setSession = useAuthStore((s) => s.setSession);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSession(data: Awaited<ReturnType<typeof login>>) {
    setSession({
      access_token: data.access_token ?? null,
      refresh_token: data.refresh_token ?? null,
      onboarding_token: data.onboarding_token ?? null,
      roles: data.roles ?? [],
      next_step: data.next_step ?? null,
    });

    const { path, externalAdmin } = resolvePostAuthPath(data);
    if (externalAdmin) {
      const adminUrl =
        process.env.NEXT_PUBLIC_ADMIN_URL ?? "http://localhost:3000";
      window.location.href = `${adminUrl}${path}`;
      return;
    }
    router.push(path);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await login(email, password);
      if (!data.access_token && !data.onboarding_token) {
        setError(t("error"));
        return;
      }
      await handleSession(data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("error");
      setError(typeof msg === "string" ? msg : t("error"));
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogle(args: {
    code: string;
    code_verifier: string;
    redirect_uri: string;
  }) {
    setError(null);
    setLoading(true);
    try {
      const data = await googleLogin(args);
      await handleSession(data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("error");
      setError(typeof msg === "string" ? msg : t("error"));
    } finally {
      setLoading(false);
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
          <GoogleButton
            label={t("continueGoogle")}
            onSuccess={handleGoogle}
            onError={() => setError(t("error"))}
            disabled={loading}
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

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              type="email"
              name="email"
              label={t("email")}
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={t("emailPlaceholder")}
            />
            <Input
              type="password"
              name="password"
              label={t("password")}
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
            <FormError message={error} />
            <Button type="submit" loading={loading} className="w-full">
              {loading ? t("submitting") : t("submit")}
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-zinc-600">
          {t("noAccount")}{" "}
          <Link
            href="/signup"
            className="font-medium text-zinc-900 underline-offset-4 hover:underline"
          >
            {t("signupCta")}
          </Link>
        </p>
      </div>
    </div>
  );
}

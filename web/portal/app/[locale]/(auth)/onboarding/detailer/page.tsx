"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { useAuthStore } from "@/lib/store/auth";
import {
  getMyServices,
  startVerification,
  submitVerification,
  toggleService,
  type DetailerService,
} from "@/lib/api/detailer";
import { Input } from "@/components/forms/Input";
import { Checkbox } from "@/components/forms/Checkbox";
import { Button } from "@/components/forms/Button";
import { FormError } from "@/components/forms/FormError";
import {
  ShieldCheck,
  CheckCircle2,
  User,
  FileCheck,
  Wrench,
  Loader2,
} from "lucide-react";
import clsx from "clsx";

type PersonalInfo = {
  legal_full_name: string;
  date_of_birth: string;
  address: string;
  city: string;
  state: string;
  zip: string;
};

const EMPTY: PersonalInfo = {
  legal_full_name: "",
  date_of_birth: "",
  address: "",
  city: "",
  state: "",
  zip: "",
};

export default function DetailerOnboardingPage() {
  const t = useTranslations("detailerOnboarding");
  const router = useRouter();
  const hydrated = useAuthStore((s) => s.hydrated);
  const accessToken = useAuthStore((s) => s.accessToken);

  const [step, setStep] = useState(0);
  const [personal, setPersonal] = useState<PersonalInfo>(EMPTY);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isDevBypass, setIsDevBypass] = useState<boolean | null>(null);
  const [consentBackground, setConsentBackground] = useState(false);
  const [consentTos, setConsentTos] = useState(false);
  const [services, setServices] = useState<DetailerService[]>([]);
  const [loadingServices, setLoadingServices] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (hydrated && !accessToken) router.replace("/login");
  }, [hydrated, accessToken, router]);

  function setField<K extends keyof PersonalInfo>(
    key: K,
    value: PersonalInfo[K]
  ) {
    setPersonal((p) => ({ ...p, [key]: value }));
  }

  function validatePersonal(): string | null {
    for (const k of Object.keys(EMPTY) as (keyof PersonalInfo)[]) {
      if (!personal[k]?.trim()) return t("validation.required");
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(personal.date_of_birth))
      return t("validation.dob");
    if (!/^\d{5}(-\d{4})?$/.test(personal.zip))
      return t("validation.zip");
    return null;
  }

  async function handleStartVerification() {
    setError(null);
    setSubmitting(true);
    try {
      const res = await startVerification();
      setIsDevBypass(res.is_dev_bypass);
      setSessionId(res.session_id ?? null);
      setStep(2);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("error");
      setError(typeof msg === "string" ? msg : t("error"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLoadServices() {
    setLoadingServices(true);
    try {
      const list = await getMyServices();
      setServices(list);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("error");
      setError(typeof msg === "string" ? msg : t("error"));
    } finally {
      setLoadingServices(false);
    }
  }

  async function handleToggleService(serviceId: string, next: boolean) {
    setServices((prev) =>
      prev.map((s) =>
        s.service_id === serviceId ? { ...s, is_active: next } : s
      )
    );
    try {
      await toggleService(serviceId, { is_active: next });
    } catch {
      setServices((prev) =>
        prev.map((s) =>
          s.service_id === serviceId ? { ...s, is_active: !next } : s
        )
      );
    }
  }

  async function handleFinalSubmit() {
    setError(null);
    if (!consentBackground || !consentTos) {
      setError(t("validation.consent"));
      return;
    }
    if (!services.some((s) => s.is_active)) {
      setError(t("validation.atLeastOneService"));
      return;
    }
    setSubmitting(true);
    try {
      await submitVerification({
        ...personal,
        background_check_consent: consentBackground,
        session_id: sessionId ?? undefined,
      });
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("error");
      setError(typeof msg === "string" ? msg : t("error"));
    } finally {
      setSubmitting(false);
    }
  }

  const stepDefs = [
    { icon: User, label: t("steps.personal") },
    { icon: ShieldCheck, label: t("steps.kyc") },
    { icon: FileCheck, label: t("steps.consent") },
    { icon: Wrench, label: t("steps.services") },
  ];

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-10 text-center">
        <h1 className="font-display text-3xl font-bold tracking-tight text-zinc-900">
          {t("title")}
        </h1>
        <p className="mt-2 text-sm text-zinc-600">{t("sub")}</p>
      </header>

      <ol className="mb-10 flex items-center justify-between gap-2">
        {stepDefs.map((s, i) => {
          const Icon = s.icon;
          const done = i < step;
          const current = i === step;
          return (
            <li key={i} className="flex flex-1 items-center gap-3">
              <span
                className={clsx(
                  "flex size-9 shrink-0 items-center justify-center rounded-full border-2 text-xs font-semibold transition",
                  done && "border-emerald-600 bg-emerald-600 text-white",
                  current && "border-brand-600 bg-brand-600 text-white",
                  !done && !current && "border-zinc-200 bg-white text-zinc-400"
                )}
              >
                {done ? <CheckCircle2 className="size-4" /> : <Icon className="size-4" />}
              </span>
              <span
                className={clsx(
                  "hidden text-xs font-medium sm:inline",
                  done && "text-emerald-700",
                  current && "text-zinc-900",
                  !done && !current && "text-zinc-400"
                )}
              >
                {s.label}
              </span>
              {i < stepDefs.length - 1 && (
                <span
                  className={clsx(
                    "h-px flex-1",
                    done ? "bg-emerald-600" : "bg-zinc-200"
                  )}
                />
              )}
            </li>
          );
        })}
      </ol>

      <div className="rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm">
        {step === 0 && (
          <div className="space-y-5">
            <h2 className="text-xl font-semibold text-zinc-900">
              {t("personal.title")}
            </h2>
            <p className="text-sm text-zinc-600">{t("personal.sub")}</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label={t("personal.legalName")}
                value={personal.legal_full_name}
                onChange={(e) => setField("legal_full_name", e.target.value)}
              />
              <Input
                label={t("personal.dob")}
                type="date"
                value={personal.date_of_birth}
                onChange={(e) => setField("date_of_birth", e.target.value)}
              />
              <Input
                label={t("personal.address")}
                value={personal.address}
                onChange={(e) => setField("address", e.target.value)}
                className="sm:col-span-2"
              />
              <Input
                label={t("personal.city")}
                value={personal.city}
                onChange={(e) => setField("city", e.target.value)}
              />
              <Input
                label={t("personal.state")}
                value={personal.state}
                onChange={(e) => setField("state", e.target.value.toUpperCase())}
                maxLength={2}
                placeholder="IN"
              />
              <Input
                label={t("personal.zip")}
                value={personal.zip}
                onChange={(e) => setField("zip", e.target.value)}
                placeholder="46802"
              />
            </div>
            <FormError message={error} />
            <div className="flex justify-end">
              <Button
                onClick={() => {
                  const err = validatePersonal();
                  if (err) return setError(err);
                  setError(null);
                  setStep(1);
                }}
              >
                {t("next")}
              </Button>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-5">
            <h2 className="text-xl font-semibold text-zinc-900">
              {t("kyc.title")}
            </h2>
            <p className="text-sm text-zinc-600">{t("kyc.sub")}</p>
            <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-6">
              <ShieldCheck className="size-8 text-brand-600" />
              <p className="mt-3 text-sm text-zinc-700">{t("kyc.body")}</p>
            </div>
            <FormError message={error} />
            <div className="flex justify-between">
              <Button variant="ghost" onClick={() => setStep(0)}>
                {t("back")}
              </Button>
              <Button onClick={handleStartVerification} loading={submitting}>
                {t("kyc.start")}
              </Button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5">
            <h2 className="text-xl font-semibold text-zinc-900">
              {t("consent.title")}
            </h2>
            {isDevBypass && (
              <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                {t("kyc.devBypassNotice")}
              </p>
            )}
            <Checkbox
              checked={consentBackground}
              onChange={(e) => setConsentBackground(e.target.checked)}
              label={t("consent.background")}
            />
            <Checkbox
              checked={consentTos}
              onChange={(e) => setConsentTos(e.target.checked)}
              label={t("consent.tos")}
            />
            <FormError message={error} />
            <div className="flex justify-between">
              <Button variant="ghost" onClick={() => setStep(1)}>
                {t("back")}
              </Button>
              <Button
                onClick={() => {
                  if (!consentBackground || !consentTos) {
                    setError(t("validation.consent"));
                    return;
                  }
                  setError(null);
                  setStep(3);
                  if (services.length === 0) handleLoadServices();
                }}
              >
                {t("next")}
              </Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5">
            <h2 className="text-xl font-semibold text-zinc-900">
              {t("services.title")}
            </h2>
            <p className="text-sm text-zinc-600">{t("services.sub")}</p>

            {loadingServices ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="size-6 animate-spin text-zinc-400" />
              </div>
            ) : services.length === 0 ? (
              <p className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-3 text-sm text-zinc-500">
                {t("services.empty")}
              </p>
            ) : (
              <ul className="divide-y divide-zinc-200 overflow-hidden rounded-lg border border-zinc-200">
                {services.map((s) => (
                  <li
                    key={s.service_id}
                    className="flex items-center justify-between gap-4 bg-white px-4 py-3"
                  >
                    <div>
                      <div className="text-sm font-medium text-zinc-900">
                        {s.name}
                      </div>
                      <div className="text-xs text-zinc-500">
                        ${(s.base_price_cents / 100).toFixed(2)}
                      </div>
                    </div>
                    <label className="relative inline-flex cursor-pointer items-center">
                      <input
                        type="checkbox"
                        className="peer sr-only"
                        checked={s.is_active}
                        onChange={(e) =>
                          handleToggleService(s.service_id, e.target.checked)
                        }
                      />
                      <span className="h-6 w-11 rounded-full bg-zinc-200 transition peer-checked:bg-brand-600 peer-focus:ring-2 peer-focus:ring-brand-500/30" />
                      <span className="absolute left-0.5 top-0.5 size-5 rounded-full bg-white shadow transition peer-checked:translate-x-5" />
                    </label>
                  </li>
                ))}
              </ul>
            )}

            <FormError message={error} />
            <div className="flex justify-between">
              <Button variant="ghost" onClick={() => setStep(2)}>
                {t("back")}
              </Button>
              <Button onClick={handleFinalSubmit} loading={submitting}>
                {t("services.finish")}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

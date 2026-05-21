"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import { getVerificationStatus, startVerification } from "@/lib/api/detailer";
import { PageHeader } from "@/components/app/PageHeader";
import { Button } from "@/components/forms/Button";
import {
  ShieldCheck,
  ShieldAlert,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  ExternalLink,
} from "lucide-react";
import clsx from "clsx";

type StatusConfig = {
  icon: React.ReactNode;
  color: string;
  bg: string;
  border: string;
  titleKey: string;
  bodyKey: string;
};

const STATUS_CONFIG: Record<string, StatusConfig> = {
  not_submitted: {
    icon: <ShieldAlert className="size-6" />,
    color: "text-zinc-600",
    bg: "bg-zinc-50",
    border: "border-zinc-200",
    titleKey: "status.not_submitted.title",
    bodyKey: "status.not_submitted.body",
  },
  pending: {
    icon: <Clock className="size-6" />,
    color: "text-amber-600",
    bg: "bg-amber-50",
    border: "border-amber-200",
    titleKey: "status.pending.title",
    bodyKey: "status.pending.body",
  },
  approved: {
    icon: <ShieldCheck className="size-6" />,
    color: "text-emerald-600",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
    titleKey: "status.approved.title",
    bodyKey: "status.approved.body",
  },
  rejected: {
    icon: <AlertTriangle className="size-6" />,
    color: "text-red-600",
    bg: "bg-red-50",
    border: "border-red-200",
    titleKey: "status.rejected.title",
    bodyKey: "status.rejected.body",
  },
};

export default function DetailerVerificationPage() {
  const t = useTranslations("detailerVerification");
  const { data, isLoading, error, mutate } = useSWR(
    "/detailers/verification/status",
    getVerificationStatus
  );
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [stripeUrl, setStripeUrl] = useState<string | null>(null);

  async function handleStart() {
    setStarting(true);
    setStartError(null);
    try {
      const result = await startVerification();
      if (result.is_dev_bypass) {
        await mutate();
        return;
      }
      if (result.client_secret) {
        setStripeUrl(
          `https://verify.stripe.com/start#${result.client_secret}`
        );
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("startError");
      setStartError(typeof msg === "string" ? msg : t("startError"));
    } finally {
      setStarting(false);
    }
  }

  const status = data?.verification_status ?? "not_submitted";
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.not_submitted;

  const canStart = status === "not_submitted" || status === "rejected";

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <PageHeader title={t("title")} sub={t("sub")} />

      {isLoading && (
        <div className="flex justify-center py-16">
          <Loader2 className="size-6 animate-spin text-zinc-400" />
        </div>
      )}

      {error && !isLoading && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {t("loadError")}
        </div>
      )}

      {!isLoading && data && (
        <div className="space-y-6">
          <div
            className={clsx(
              "rounded-2xl border p-6",
              cfg.bg,
              cfg.border
            )}
          >
            <div className={clsx("mb-3 flex items-center gap-3", cfg.color)}>
              {cfg.icon}
              <h2 className="text-base font-semibold">{t(cfg.titleKey)}</h2>
            </div>
            <p className="text-sm text-zinc-700">{t(cfg.bodyKey)}</p>

            {status === "rejected" && data.rejection_reason && (
              <div className="mt-4 rounded-xl border border-red-200 bg-white px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-red-600">
                  {t("rejectionReason")}
                </p>
                <p className="mt-1 text-sm text-zinc-700">
                  {data.rejection_reason}
                </p>
              </div>
            )}

            {status === "approved" && (
              <div className="mt-4 flex items-center gap-2 text-sm text-emerald-700">
                <CheckCircle2 className="size-4" />
                {t("approvedNote")}
              </div>
            )}
          </div>

          {stripeUrl && (
            <div className="rounded-2xl border border-zinc-200 bg-white p-6">
              <p className="mb-4 text-sm text-zinc-600">{t("stripeReady")}</p>
              <a
                href={stripeUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800"
              >
                {t("openStripe")}
                <ExternalLink className="size-4" />
              </a>
            </div>
          )}

          {startError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {startError}
            </div>
          )}

          {canStart && !stripeUrl && (
            <div className="rounded-2xl border border-zinc-200 bg-white p-6">
              <h3 className="mb-2 text-sm font-semibold text-zinc-900">
                {t("startTitle")}
              </h3>
              <p className="mb-4 text-sm text-zinc-600">{t("startBody")}</p>
              <Button onClick={handleStart} loading={starting}>
                {t("startCta")}
              </Button>
            </div>
          )}

          <div className="rounded-2xl border border-zinc-100 bg-zinc-50 p-5">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">
              {t("stepsTitle")}
            </h3>
            <ul className="flex flex-col gap-2">
              {(["identity", "background", "portfolio", "approval"] as const).map(
                (step, i) => {
                  const done =
                    status === "approved" ||
                    (status === "pending" && i < 2) ||
                    (status === "rejected" && i < 1);
                  return (
                    <li
                      key={step}
                      className="flex items-center gap-3 text-sm"
                    >
                      <span
                        className={clsx(
                          "flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                          done
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-zinc-200 text-zinc-500"
                        )}
                      >
                        {done ? <CheckCircle2 className="size-4" /> : i + 1}
                      </span>
                      <span
                        className={
                          done ? "text-zinc-900" : "text-zinc-400"
                        }
                      >
                        {t(`steps.${step}`)}
                      </span>
                    </li>
                  );
                }
              )}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

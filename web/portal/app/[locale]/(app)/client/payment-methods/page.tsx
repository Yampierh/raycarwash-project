"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import {
  listPaymentMethods,
  deletePaymentMethod,
  setDefaultPaymentMethod,
  type PaymentMethod,
} from "@/lib/api/payment-methods";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { Loader2, CreditCard, Trash2, Star, CheckCircle2 } from "lucide-react";
import clsx from "clsx";

const BRAND_ICONS: Record<string, string> = {
  visa: "VISA",
  mastercard: "MC",
  amex: "AMEX",
  discover: "DISC",
};

function CardBrandBadge({ brand }: { brand: string | null }) {
  const label = brand ? (BRAND_ICONS[brand.toLowerCase()] ?? brand.toUpperCase()) : "CARD";
  return (
    <span className="inline-flex h-7 min-w-[3rem] items-center justify-center rounded border border-zinc-200 bg-zinc-50 px-2 font-mono text-xs font-bold text-zinc-700">
      {label}
    </span>
  );
}

export default function PaymentMethodsPage() {
  const t = useTranslations("clientPaymentMethods");
  const { data, error, isLoading, mutate } = useSWR("payment-methods", listPaymentMethods);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [defaultingId, setDefaultingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function handleDelete(pm: PaymentMethod) {
    if (!window.confirm(t("confirmDelete", { last4: pm.last4 ?? "****" }))) return;
    setDeletingId(pm.id);
    setActionError(null);
    try {
      await deletePaymentMethod(pm.id);
      await mutate();
    } catch {
      setActionError(t("deleteError"));
    } finally {
      setDeletingId(null);
    }
  }

  async function handleSetDefault(pm: PaymentMethod) {
    setDefaultingId(pm.id);
    setActionError(null);
    try {
      await setDefaultPaymentMethod(pm.id);
      await mutate();
    } catch {
      setActionError(t("defaultError"));
    } finally {
      setDefaultingId(null);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <PageHeader title={t("title")} sub={t("sub")} />

      <div className="mb-6 rounded-2xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-600">
        {t("addHint")}
      </div>

      {actionError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {actionError}
        </div>
      )}

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

      {!isLoading && !error && data && data.length === 0 && (
        <EmptyState
          icon={<CreditCard className="size-5" />}
          title={t("emptyTitle")}
          body={t("emptyBody")}
        />
      )}

      {!isLoading && data && data.length > 0 && (
        <ul className="flex flex-col gap-3">
          {data.map((pm) => (
            <li
              key={pm.id}
              className={clsx(
                "rounded-2xl border bg-white p-5",
                pm.is_default ? "border-zinc-900" : "border-zinc-200"
              )}
            >
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                  <CardBrandBadge brand={pm.brand} />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-zinc-900">
                        •••• {pm.last4 ?? "····"}
                      </span>
                      {pm.is_default && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-zinc-900 px-2 py-0.5 text-xs font-medium text-white">
                          <CheckCircle2 className="size-3" />
                          {t("default")}
                        </span>
                      )}
                    </div>
                    {pm.exp_month && pm.exp_year && (
                      <p className="text-xs text-zinc-500">
                        {t("expires")} {String(pm.exp_month).padStart(2, "0")}/{pm.exp_year}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  {!pm.is_default && (
                    <button
                      type="button"
                      onClick={() => handleSetDefault(pm)}
                      disabled={defaultingId === pm.id}
                      title={t("setDefault")}
                      className="rounded-lg p-2 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 disabled:opacity-50"
                    >
                      {defaultingId === pm.id ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <Star className="size-4" />
                      )}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => handleDelete(pm)}
                    disabled={deletingId === pm.id}
                    title={t("remove")}
                    className="rounded-lg p-2 text-zinc-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                  >
                    {deletingId === pm.id ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : (
                      <Trash2 className="size-4" />
                    )}
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

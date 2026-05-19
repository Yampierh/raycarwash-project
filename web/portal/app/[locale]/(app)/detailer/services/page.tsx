"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useDetailerServices } from "@/lib/hooks/useDetailerServices";
import {
  toggleService,
  type DetailerService,
} from "@/lib/api/detailer";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { Button } from "@/components/forms/Button";
import { Wrench, Loader2, Pencil, X, Check } from "lucide-react";

export default function DetailerServicesPage() {
  const t = useTranslations("detailerServices");
  const { data, error, isLoading, mutate } = useDetailerServices();

  async function handleToggle(s: DetailerService, next: boolean) {
    await mutate(
      (cur) =>
        cur?.map((x) =>
          x.service_id === s.service_id ? { ...x, is_active: next } : x
        ),
      false
    );
    try {
      await toggleService(s.service_id, {
        is_active: next,
        custom_price_cents: s.custom_price_cents ?? undefined,
      });
    } catch {
      await mutate();
      window.alert(t("error"));
    }
  }

  async function handlePriceUpdate(
    s: DetailerService,
    customCents: number | null
  ) {
    await mutate(
      (cur) =>
        cur?.map((x) =>
          x.service_id === s.service_id
            ? { ...x, custom_price_cents: customCents }
            : x
        ),
      false
    );
    try {
      await toggleService(s.service_id, {
        is_active: s.is_active,
        custom_price_cents: customCents,
      });
    } catch {
      await mutate();
      window.alert(t("error"));
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
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

      {!isLoading && !error && data && data.length === 0 && (
        <EmptyState
          icon={<Wrench className="size-5" />}
          title={t("emptyTitle")}
          body={t("emptyBody")}
        />
      )}

      {data && data.length > 0 && (
        <ul className="flex flex-col gap-3">
          {data.map((s) => (
            <ServiceRow
              key={s.service_id}
              service={s}
              onToggle={(next) => handleToggle(s, next)}
              onPriceChange={(cents) => handlePriceUpdate(s, cents)}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function ServiceRow({
  service,
  onToggle,
  onPriceChange,
}: {
  service: DetailerService;
  onToggle: (next: boolean) => Promise<void>;
  onPriceChange: (cents: number | null) => Promise<void>;
}) {
  const t = useTranslations("detailerServices");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(
    service.custom_price_cents != null
      ? (service.custom_price_cents / 100).toFixed(2)
      : ""
  );

  async function commit() {
    const trimmed = draft.trim();
    if (!trimmed) {
      await onPriceChange(null);
      setEditing(false);
      return;
    }
    const cents = Math.round(parseFloat(trimmed) * 100);
    if (!Number.isFinite(cents) || cents <= 0) {
      window.alert(t("priceInvalid"));
      return;
    }
    await onPriceChange(cents);
    setEditing(false);
  }

  return (
    <li className="rounded-2xl border border-zinc-200 bg-white p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-semibold text-zinc-900">
            {service.name}
          </h3>
          {service.description && (
            <p className="mt-1 text-sm text-zinc-600">{service.description}</p>
          )}
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-zinc-700">
              {t("basePrice")}: ${(service.base_price_cents / 100).toFixed(2)}
            </span>
            {!editing && (
              <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-brand-700">
                {t("yourPrice")}:
                <span className="font-semibold">
                  $
                  {(
                    (service.custom_price_cents ?? service.base_price_cents) /
                    100
                  ).toFixed(2)}
                </span>
                <button
                  type="button"
                  onClick={() => setEditing(true)}
                  className="ml-1 text-brand-700 hover:text-brand-900"
                  aria-label={t("editPrice")}
                >
                  <Pencil className="size-3" />
                </button>
              </span>
            )}
            {editing && (
              <span className="inline-flex items-center gap-2">
                <span className="text-zinc-500">$</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  className="w-24 rounded-lg border border-zinc-200 px-2 py-1 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                  autoFocus
                />
                <Button size="sm" onClick={commit}>
                  <Check className="size-3.5" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setEditing(false);
                    setDraft(
                      service.custom_price_cents != null
                        ? (service.custom_price_cents / 100).toFixed(2)
                        : ""
                    );
                  }}
                >
                  <X className="size-3.5" />
                </Button>
              </span>
            )}
          </div>
        </div>

        <label className="relative inline-flex shrink-0 cursor-pointer items-center">
          <input
            type="checkbox"
            className="peer sr-only"
            checked={service.is_active}
            onChange={(e) => onToggle(e.target.checked)}
          />
          <span className="h-6 w-11 rounded-full bg-zinc-200 transition peer-checked:bg-brand-600 peer-focus:ring-2 peer-focus:ring-brand-500/30" />
          <span className="absolute left-0.5 top-0.5 size-5 rounded-full bg-white shadow transition peer-checked:translate-x-5" />
        </label>
      </div>
    </li>
  );
}

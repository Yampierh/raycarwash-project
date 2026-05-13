"use client";

import { useState, use } from "react";
import { useTranslations, useLocale } from "next-intl";
import useSWR from "swr";
import { useRouter, Link } from "@/i18n/navigation";
import {
  getAppointment,
  updateAppointmentStatus,
  type Appointment,
  type AppointmentStatus,
} from "@/lib/api/appointments";
import { PageHeader } from "@/components/app/PageHeader";
import { AppointmentStatusBadge } from "@/components/app/AppointmentStatusBadge";
import { Button } from "@/components/forms/Button";
import { FormError } from "@/components/forms/FormError";
import {
  ArrowLeft,
  MapPin,
  Calendar,
  Car,
  User,
  Phone,
  Loader2,
  FileText,
} from "lucide-react";

type NextAction = {
  status: AppointmentStatus;
  labelKey:
    | "actions.confirm"
    | "actions.markArrived"
    | "actions.start"
    | "actions.complete";
};

function nextActionFor(status: AppointmentStatus): NextAction | null {
  switch (status) {
    case "pending":
      return { status: "confirmed", labelKey: "actions.confirm" };
    case "confirmed":
      return { status: "arrived", labelKey: "actions.markArrived" };
    case "arrived":
      return { status: "in_progress", labelKey: "actions.start" };
    case "in_progress":
      return { status: "completed", labelKey: "actions.complete" };
    default:
      return null;
  }
}

const TERMINAL_STATUSES = new Set<AppointmentStatus>([
  "completed",
  "cancelled_by_client",
  "cancelled_by_detailer",
  "no_show",
  "no_detailer_found",
]);

export default function DetailerJobPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const t = useTranslations("detailerJob");
  const locale = useLocale();
  const router = useRouter();
  const { data, error, isLoading, mutate } = useSWR<Appointment>(
    `/appointments/${id}`,
    () => getAppointment(id)
  );

  const [transitioning, setTransitioning] = useState(false);
  const [showCompleteNotes, setShowCompleteNotes] = useState(false);
  const [completionNotes, setCompletionNotes] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  async function handleTransition(
    next: AppointmentStatus,
    detailer_notes?: string
  ) {
    setActionError(null);
    setTransitioning(true);
    try {
      const updated = await updateAppointmentStatus(id, next, detailer_notes);
      await mutate(updated, false);
      setShowCompleteNotes(false);
      setCompletionNotes("");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("error");
      setActionError(typeof msg === "string" ? msg : t("error"));
    } finally {
      setTransitioning(false);
    }
  }

  async function handleCancel() {
    const reason = window.prompt(t("cancelPrompt"));
    if (reason == null) return;
    await handleTransition("cancelled_by_detailer", reason || undefined);
  }

  const dateFormatter = new Intl.DateTimeFormat(locale, {
    dateStyle: "full",
    timeStyle: "short",
  });

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="size-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <Link
          href="/detailer/home"
          className="mb-6 inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-900"
        >
          <ArrowLeft className="size-4" />
          {t("back")}
        </Link>
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {t("loadError")}
        </div>
      </div>
    );
  }

  const next = nextActionFor(data.status);
  const canCancel = !TERMINAL_STATUSES.has(data.status);

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <Link
        href="/detailer/home"
        className="mb-6 inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-900"
      >
        <ArrowLeft className="size-4" />
        {t("back")}
      </Link>

      <PageHeader
        title={t("title")}
        action={
          <AppointmentStatusBadge
            status={data.status}
            label={t(`status.${data.status}` as const, {
              defaultMessage: data.status,
            })}
          />
        }
      />

      <div className="rounded-2xl border border-zinc-200 bg-white p-6">
        <DataRow
          icon={<Calendar className="size-4" />}
          label={t("scheduled")}
          value={dateFormatter.format(new Date(data.scheduled_time))}
        />
        <DataRow
          icon={<User className="size-4" />}
          label={t("client")}
          value={data.client?.full_name ?? "—"}
        />
        {data.client?.phone && (
          <DataRow
            icon={<Phone className="size-4" />}
            label={t("phone")}
            value={
              <a
                href={`tel:${data.client.phone}`}
                className="text-brand-600 underline-offset-4 hover:underline"
              >
                {data.client.phone}
              </a>
            }
          />
        )}
        {data.service_address && (
          <DataRow
            icon={<MapPin className="size-4" />}
            label={t("address")}
            value={data.service_address}
          />
        )}
        {data.vehicles.length > 0 && (
          <DataRow
            icon={<Car className="size-4" />}
            label={t("vehicles")}
            value={
              <ul className="flex flex-col gap-1">
                {data.vehicles.map((v) => (
                  <li key={v.id} className="text-sm">
                    {v.vehicle
                      ? `${v.vehicle.make} ${v.vehicle.model} · ${v.vehicle.color}`
                      : t("vehicle")}
                    <span className="ml-2 text-xs text-zinc-500">
                      ${(v.price_cents / 100).toFixed(2)} · {v.duration_minutes} min
                    </span>
                  </li>
                ))}
              </ul>
            }
          />
        )}
        {data.client_notes && (
          <DataRow
            icon={<FileText className="size-4" />}
            label={t("clientNotes")}
            value={data.client_notes}
          />
        )}

        <div className="mt-6 flex items-center justify-between border-t border-zinc-100 pt-4">
          <span className="text-xs uppercase tracking-wider text-zinc-500">
            {data.actual_price_cents ? t("finalPrice") : t("estimatedPrice")}
          </span>
          <span className="font-display text-2xl font-bold text-zinc-900">
            $
            {((data.actual_price_cents ?? data.estimated_price_cents) / 100).toFixed(
              2
            )}
          </span>
        </div>
      </div>

      {showCompleteNotes && (
        <div className="mt-6 rounded-2xl border border-zinc-200 bg-white p-6">
          <label className="mb-2 block text-sm font-medium text-zinc-700">
            {t("completionNotes")}
          </label>
          <textarea
            value={completionNotes}
            onChange={(e) => setCompletionNotes(e.target.value)}
            rows={3}
            maxLength={2000}
            placeholder={t("completionNotesPlaceholder")}
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          />
        </div>
      )}

      <FormError message={actionError} />

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        {canCancel ? (
          <Button
            variant="ghost"
            onClick={handleCancel}
            disabled={transitioning}
          >
            {t("actions.cancel")}
          </Button>
        ) : (
          <button
            type="button"
            onClick={() => router.push("/detailer/home")}
            className="text-sm font-medium text-zinc-500 underline-offset-4 hover:underline"
          >
            {t("backToJobs")}
          </button>
        )}

        {next && (
          <Button
            onClick={() => {
              if (next.status === "completed" && !showCompleteNotes) {
                setShowCompleteNotes(true);
                return;
              }
              handleTransition(
                next.status,
                next.status === "completed"
                  ? completionNotes || undefined
                  : undefined
              );
            }}
            loading={transitioning}
          >
            {t(next.labelKey)}
          </Button>
        )}
      </div>
    </div>
  );
}

function DataRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex gap-4 border-b border-zinc-100 py-3 last:border-b-0">
      <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-zinc-500">
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <div className="text-xs font-medium uppercase tracking-wider text-zinc-500">
          {label}
        </div>
        <div className="mt-1 text-sm text-zinc-900">{value}</div>
      </div>
    </div>
  );
}

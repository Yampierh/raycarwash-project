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
import { createReview } from "@/lib/api/reviews";
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
  FileText,
  Star,
  Loader2,
} from "lucide-react";
import clsx from "clsx";

const CANCELLABLE_STATUSES = new Set<AppointmentStatus>([
  "pending",
  "confirmed",
  "searching",
]);

export default function ClientAppointmentDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const t = useTranslations("clientAppointmentDetail");
  const locale = useLocale();
  const router = useRouter();
  const { data, error, isLoading, mutate } = useSWR<Appointment>(
    `/appointments/${id}`,
    () => getAppointment(id),
    { refreshInterval: 15000 }
  );

  const [cancelling, setCancelling] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Review state
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewSent, setReviewSent] = useState(false);

  const dateFormatter = new Intl.DateTimeFormat(locale, {
    dateStyle: "full",
    timeStyle: "short",
  });

  async function handleCancel() {
    if (!data) return;
    if (!window.confirm(t("confirmCancel"))) return;
    setActionError(null);
    setCancelling(true);
    try {
      const updated = await updateAppointmentStatus(
        data.id,
        "cancelled_by_client"
      );
      await mutate(updated, false);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("cancelError");
      setActionError(typeof msg === "string" ? msg : t("cancelError"));
    } finally {
      setCancelling(false);
    }
  }

  async function handleSubmitReview() {
    if (!data || rating < 1) return;
    setReviewError(null);
    setReviewLoading(true);
    try {
      await createReview({
        appointment_id: data.id,
        rating,
        comment: comment.trim() || undefined,
      });
      setReviewSent(true);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("reviewError");
      setReviewError(typeof msg === "string" ? msg : t("reviewError"));
    } finally {
      setReviewLoading(false);
    }
  }

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
          href="/client/appointments"
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

  const canCancel = CANCELLABLE_STATUSES.has(data.status);
  const isCompleted = data.status === "completed";

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <Link
        href="/client/appointments"
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
          label={t("detailer")}
          value={data.detailer?.full_name ?? t("searching")}
        />
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
              <ul className="flex flex-col gap-1 text-sm">
                {data.vehicles.map((v) => (
                  <li key={v.id}>
                    {v.vehicle
                      ? `${v.vehicle.make} ${v.vehicle.model} · ${v.vehicle.color}`
                      : t("vehicle")}
                    <span className="ml-2 text-xs text-zinc-500">
                      ${(v.price_cents / 100).toFixed(2)}
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
            label={t("yourNotes")}
            value={data.client_notes}
          />
        )}
        {data.detailer_notes && (
          <DataRow
            icon={<FileText className="size-4" />}
            label={t("detailerNotes")}
            value={data.detailer_notes}
          />
        )}

        <div className="mt-6 flex items-center justify-between border-t border-zinc-100 pt-4">
          <span className="text-xs uppercase tracking-wider text-zinc-500">
            {data.actual_price_cents ? t("finalPrice") : t("estimatedPrice")}
          </span>
          <span className="font-display text-2xl font-bold text-zinc-900">
            $
            {((data.actual_price_cents ?? data.estimated_price_cents) / 100).toFixed(2)}
          </span>
        </div>
      </div>

      <FormError message={actionError} />

      {canCancel && (
        <div className="mt-6 flex justify-end">
          <Button
            variant="ghost"
            onClick={handleCancel}
            loading={cancelling}
          >
            {t("cancel")}
          </Button>
        </div>
      )}

      {isCompleted && !reviewSent && (
        <section className="mt-10 rounded-2xl border border-zinc-200 bg-white p-6">
          <header className="mb-4">
            <h2 className="text-base font-semibold text-zinc-900">
              {t("review.title")}
            </h2>
            <p className="mt-1 text-sm text-zinc-600">{t("review.sub")}</p>
          </header>

          <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setRating(n)}
                className="p-1"
                aria-label={t("review.starLabel", { n })}
              >
                <Star
                  className={clsx(
                    "size-7 transition",
                    n <= rating
                      ? "fill-amber-400 text-amber-400"
                      : "text-zinc-300"
                  )}
                />
              </button>
            ))}
          </div>

          <textarea
            rows={3}
            maxLength={2000}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={t("review.commentPlaceholder")}
            className="mt-4 w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          />

          <FormError message={reviewError} />

          <div className="mt-4 flex justify-end">
            <Button
              onClick={handleSubmitReview}
              loading={reviewLoading}
              disabled={rating < 1}
            >
              {t("review.submit")}
            </Button>
          </div>
        </section>
      )}

      {reviewSent && (
        <div className="mt-10 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          {t("review.thanks")}
        </div>
      )}

      <div className="mt-10 flex justify-center">
        <Button variant="ghost" onClick={() => router.push("/client/home")}>
          {t("backToHome")}
        </Button>
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

"use client";

import { useEffect, useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import { useRouter, Link } from "@/i18n/navigation";
import { useVehicles } from "@/lib/hooks/useVehicles";
import { useServices } from "@/lib/hooks/useServices";
import { useAddons } from "@/lib/hooks/useAddons";
import { findMatches, type MatchingResult, type TimeSlot } from "@/lib/api/matching";
import { createAppointment } from "@/lib/api/appointments";
import { createPaymentIntent } from "@/lib/api/payments";
import { CheckoutForm } from "@/components/app/CheckoutForm";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { Input } from "@/components/forms/Input";
import { Button } from "@/components/forms/Button";
import { FormError } from "@/components/forms/FormError";
import {
  Car,
  Sparkles,
  Calendar,
  MapPin,
  Users,
  Loader2,
  CheckCircle2,
  ArrowLeft,
  Star,
  Plus,
  Minus,
} from "lucide-react";
import clsx from "clsx";

// Fort Wayne, IN center — fallback if geolocation isn't available.
const FALLBACK_COORDS = { lat: 41.0793, lng: -85.1394 };

type Step = 0 | 1 | 2 | 3;

export default function BookPage() {
  const t = useTranslations("book");
  const locale = useLocale();
  const router = useRouter();

  // Catalog
  const { data: vehicles, isLoading: vehiclesLoading } = useVehicles();
  const { data: services, isLoading: servicesLoading } = useServices();
  const { data: addons } = useAddons();

  // Step state
  const [step, setStep] = useState<Step>(0);
  const [serviceId, setServiceId] = useState<string | null>(null);
  const [vehicleIds, setVehicleIds] = useState<string[]>([]);
  const [addonIds, setAddonIds] = useState<string[]>([]);
  const [date, setDate] = useState(() => {
    const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
    return tomorrow.toISOString().slice(0, 10);
  });
  const [serviceAddress, setServiceAddress] = useState("");
  const [clientNotes, setClientNotes] = useState("");
  const [coords, setCoords] = useState<{ lat: number; lng: number }>(FALLBACK_COORDS);

  // Match state
  const [matches, setMatches] = useState<MatchingResult[]>([]);
  const [matchLoading, setMatchLoading] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);
  const [selectedDetailerId, setSelectedDetailerId] = useState<string | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null);

  // Confirm / checkout state
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [appointmentId, setAppointmentId] = useState<string | null>(null);
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [amountCents, setAmountCents] = useState<number | null>(null);

  // Geolocate on mount.
  useEffect(() => {
    if (typeof navigator === "undefined" || !navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => undefined,
      { timeout: 5000 }
    );
  }, []);

  const dateFormatter = new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  });
  const selectedService = services?.find((s) => s.id === serviceId) ?? null;
  const selectedVehicles =
    vehicles?.filter((v) => vehicleIds.includes(v.id)) ?? [];
  const selectedDetailer =
    matches.find((m) => m.user_id === selectedDetailerId) ?? null;

  function toggleVehicle(id: string) {
    setVehicleIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  function toggleAddon(id: string) {
    setAddonIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  async function handleSearchMatches({
    keepDetailer = false,
  }: { keepDetailer?: boolean } = {}) {
    if (!serviceId || vehicleIds.length === 0 || !selectedVehicles.length) return;
    setMatchError(null);
    setMatchLoading(true);
    setMatches([]);
    if (!keepDetailer) setSelectedDetailerId(null);
    setSelectedSlot(null);
    try {
      const sizes = selectedVehicles
        .map((v) => v.suggested_size ?? "medium")
        .join(",");
      const results = await findMatches({
        lat: coords.lat,
        lng: coords.lng,
        date,
        service_id: serviceId,
        vehicle_sizes: sizes,
        addon_ids: addonIds.length > 0 ? addonIds.join(",") : undefined,
      });
      setMatches(results);
      // If we were preserving the detailer but they dropped off the new
      // results, fall back to letting the user pick fresh.
      if (
        keepDetailer &&
        selectedDetailerId &&
        !results.some((r) => r.user_id === selectedDetailerId)
      ) {
        setSelectedDetailerId(null);
      }
      setStep(2);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("matchError");
      setMatchError(typeof msg === "string" ? msg : t("matchError"));
    } finally {
      setMatchLoading(false);
    }
  }

  async function handleConfirmBooking() {
    if (
      !selectedDetailerId ||
      !selectedSlot ||
      !serviceId ||
      vehicleIds.length === 0 ||
      !serviceAddress.trim()
    )
      return;
    setConfirmError(null);
    setConfirmLoading(true);
    try {
      const appt = await createAppointment({
        detailer_id: selectedDetailerId,
        scheduled_time: selectedSlot.start_time,
        service_address: serviceAddress.trim(),
        service_latitude: coords.lat,
        service_longitude: coords.lng,
        client_notes: clientNotes.trim() || null,
        vehicles: vehicleIds.map((id) => ({
          vehicle_id: id,
          service_id: serviceId,
          addon_ids: addonIds,
        })),
      });
      setAppointmentId(appt.id);

      // Authorize the funds now (manual capture). The hold stays until the
      // detailer marks the job COMPLETED, at which point the backend captures.
      const intent = await createPaymentIntent(appt.id);
      setClientSecret(intent.client_secret);
      setAmountCents(intent.amount_cents);
      setStep(3);
      return;
    } catch (err: unknown) {
      const response = (err as { response?: { status?: number; data?: { detail?: string } } })?.response;
      const status = response?.status;
      const backendMsg = response?.data?.detail;

      // 409 = the picked slot just got taken (or conflicts with travel buffer).
      // Drop the stale selection and refresh /matching keeping the detailer
      // pick when possible, so the user just re-picks a slot.
      if (status === 409) {
        setSelectedSlot(null);
        setConfirmError(t("slotTaken"));
        void handleSearchMatches({ keepDetailer: true });
        return;
      }

      const msg = typeof backendMsg === "string" ? backendMsg : t("confirmError");
      setConfirmError(msg);
    } finally {
      setConfirmLoading(false);
    }
  }

  function handlePaymentSuccess() {
    if (!appointmentId) return;
    router.push(`/client/appointments/${appointmentId}`);
  }

  const hasVehicles = (vehicles?.length ?? 0) > 0;
  const canProceedFromStep0 = serviceId && vehicleIds.length > 0;
  const canProceedFromStep1 =
    date && serviceAddress.trim().length >= 5;

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <Link
        href="/client/home"
        className="mb-6 inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-900"
      >
        <ArrowLeft className="size-4" />
        {t("back")}
      </Link>

      <PageHeader title={t("title")} sub={t("sub")} />

      <Steps current={step} />

      {/* STEP 0: Service + vehicles + addons */}
      {step === 0 && (
        <section className="space-y-6">
          <SectionCard icon={<Sparkles className="size-5" />} title={t("steps.service")}>
            {servicesLoading ? (
              <Loader2 className="size-6 animate-spin text-zinc-400" />
            ) : (
              <ul className="grid gap-3 sm:grid-cols-2">
                {services?.map((s) => (
                  <li key={s.id}>
                    <button
                      type="button"
                      onClick={() => setServiceId(s.id)}
                      className={clsx(
                        "flex w-full flex-col rounded-xl border-2 bg-white p-4 text-left transition",
                        serviceId === s.id
                          ? "border-brand-600 ring-2 ring-brand-500/20"
                          : "border-zinc-200 hover:border-zinc-300"
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold text-zinc-900">
                          {s.name}
                        </span>
                        <span className="font-display text-lg font-bold text-zinc-900">
                          ${(s.base_price_cents / 100).toFixed(0)}+
                        </span>
                      </div>
                      {s.description && (
                        <p className="mt-1 line-clamp-2 text-xs text-zinc-600">
                          {s.description}
                        </p>
                      )}
                      <p className="mt-2 text-[10px] uppercase tracking-wider text-zinc-500">
                        {s.base_duration_minutes} min · {t("startingAt")}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </SectionCard>

          <SectionCard
            icon={<Car className="size-5" />}
            title={t("steps.vehicles")}
          >
            {vehiclesLoading ? (
              <Loader2 className="size-6 animate-spin text-zinc-400" />
            ) : !hasVehicles ? (
              <EmptyState
                icon={<Car className="size-5" />}
                title={t("noVehicles.title")}
                body={t("noVehicles.body")}
                action={
                  <Button onClick={() => router.push("/client/vehicles/new")}>
                    <Plus className="size-4" />
                    {t("noVehicles.action")}
                  </Button>
                }
              />
            ) : (
              <ul className="flex flex-col gap-2">
                {vehicles?.map((v) => {
                  const checked = vehicleIds.includes(v.id);
                  return (
                    <li key={v.id}>
                      <button
                        type="button"
                        onClick={() => toggleVehicle(v.id)}
                        className={clsx(
                          "flex w-full items-center justify-between gap-3 rounded-xl border-2 px-4 py-3 text-left transition",
                          checked
                            ? "border-brand-600 bg-brand-50/50"
                            : "border-zinc-200 bg-white hover:border-zinc-300"
                        )}
                      >
                        <div>
                          <div className="text-sm font-semibold text-zinc-900">
                            {v.year} {v.make} {v.model}
                          </div>
                          <div className="text-xs text-zinc-500">
                            {v.color} · {v.license_plate}
                          </div>
                        </div>
                        <span
                          className={clsx(
                            "flex size-5 items-center justify-center rounded-full border-2",
                            checked
                              ? "border-brand-600 bg-brand-600 text-white"
                              : "border-zinc-300"
                          )}
                        >
                          {checked && <CheckCircle2 className="size-3" />}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </SectionCard>

          {addons && addons.length > 0 && (
            <SectionCard
              icon={<Plus className="size-5" />}
              title={t("steps.addons")}
            >
              <ul className="grid gap-2 sm:grid-cols-2">
                {addons.map((a) => {
                  const checked = addonIds.includes(a.id);
                  return (
                    <li key={a.id}>
                      <button
                        type="button"
                        onClick={() => toggleAddon(a.id)}
                        className={clsx(
                          "flex w-full items-center justify-between gap-2 rounded-xl border-2 px-3 py-2 text-left text-sm transition",
                          checked
                            ? "border-brand-600 bg-brand-50/50"
                            : "border-zinc-200 bg-white hover:border-zinc-300"
                        )}
                      >
                        <span className="text-zinc-900">{a.name}</span>
                        <span className="text-xs font-semibold text-zinc-700">
                          +${(a.price_cents / 100).toFixed(0)}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </SectionCard>
          )}

          <div className="flex justify-end">
            <Button
              size="lg"
              disabled={!canProceedFromStep0}
              onClick={() => setStep(1)}
            >
              {t("next")}
            </Button>
          </div>
        </section>
      )}

      {/* STEP 1: Date + address + notes */}
      {step === 1 && (
        <section className="space-y-6">
          <SectionCard
            icon={<Calendar className="size-5" />}
            title={t("steps.date")}
          >
            <Input
              type="date"
              label={t("date")}
              value={date}
              min={new Date(Date.now() + 24 * 60 * 60 * 1000)
                .toISOString()
                .slice(0, 10)}
              onChange={(e) => setDate(e.target.value)}
            />
          </SectionCard>

          <SectionCard
            icon={<MapPin className="size-5" />}
            title={t("steps.address")}
          >
            <Input
              label={t("address")}
              placeholder={t("addressPlaceholder")}
              value={serviceAddress}
              onChange={(e) => setServiceAddress(e.target.value)}
            />
            <p className="mt-2 text-xs text-zinc-500">
              {t("locationHint", {
                lat: coords.lat.toFixed(3),
                lng: coords.lng.toFixed(3),
              })}
            </p>

            <div className="mt-4 flex flex-col gap-1">
              <label className="text-sm font-medium text-zinc-700">
                {t("notes")}
              </label>
              <textarea
                rows={3}
                maxLength={2000}
                value={clientNotes}
                onChange={(e) => setClientNotes(e.target.value)}
                placeholder={t("notesPlaceholder")}
                className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              />
            </div>
          </SectionCard>

          <FormError message={matchError} />

          <div className="flex justify-between">
            <Button variant="ghost" onClick={() => setStep(0)}>
              {t("backStep")}
            </Button>
            <Button
              size="lg"
              loading={matchLoading}
              disabled={!canProceedFromStep1}
              onClick={() => handleSearchMatches()}
            >
              {t("findMatches")}
            </Button>
          </div>
        </section>
      )}

      {/* STEP 2: Pick detailer + slot */}
      {step === 2 && (
        <section className="space-y-6">
          <SectionCard
            icon={<Users className="size-5" />}
            title={t("steps.match")}
          >
            {matches.length === 0 ? (
              <EmptyState
                icon={<Users className="size-5" />}
                title={t("noMatches.title")}
                body={t("noMatches.body")}
              />
            ) : (
              <ul className="flex flex-col gap-3">
                {matches.map((m) => (
                  <li
                    key={m.user_id}
                    className={clsx(
                      "overflow-hidden rounded-xl border-2 bg-white transition",
                      selectedDetailerId === m.user_id
                        ? "border-brand-600 ring-2 ring-brand-500/20"
                        : "border-zinc-200 hover:border-zinc-300"
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedDetailerId(m.user_id);
                        setSelectedSlot(null);
                        setConfirmError(null);
                      }}
                      className="block w-full p-4 text-left"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-zinc-900">
                              {m.full_name}
                            </span>
                            {m.average_rating != null && (
                              <span className="inline-flex items-center gap-0.5 text-xs text-zinc-600">
                                <Star className="size-3 fill-amber-400 text-amber-400" />
                                {m.average_rating.toFixed(1)}
                                <span className="text-zinc-400">
                                  ({m.total_reviews})
                                </span>
                              </span>
                            )}
                          </div>
                          {m.distance_miles != null && (
                            <p className="mt-0.5 text-xs text-zinc-500">
                              {m.distance_miles.toFixed(1)} mi · {m.estimated_duration} min
                            </p>
                          )}
                        </div>
                        <span className="font-display text-xl font-bold text-zinc-900">
                          ${(m.estimated_price / 100).toFixed(2)}
                        </span>
                      </div>
                    </button>

                    {selectedDetailerId === m.user_id && (
                      <div className="border-t border-zinc-100 p-4 pt-3">
                        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-500">
                          {t("availableSlots")}
                        </p>
                        <ul className="flex flex-wrap gap-2">
                          {m.available_slots.map((s) => {
                            const isSel =
                              selectedSlot?.start_time === s.start_time;
                            return (
                              <li key={s.start_time}>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setSelectedSlot(s);
                                    setConfirmError(null);
                                  }}
                                  className={clsx(
                                    "rounded-lg border px-3 py-1.5 text-xs font-medium transition",
                                    isSel
                                      ? "border-brand-600 bg-brand-600 text-white"
                                      : "border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50"
                                  )}
                                >
                                  {dateFormatter.format(new Date(s.start_time))}
                                </button>
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </SectionCard>

          <SummaryCard
            service={selectedService?.name ?? "—"}
            vehiclesCount={selectedVehicles.length}
            address={serviceAddress}
            slotLabel={
              selectedSlot
                ? dateFormatter.format(new Date(selectedSlot.start_time))
                : null
            }
            detailerName={selectedDetailer?.full_name ?? null}
            priceCents={selectedDetailer?.estimated_price ?? null}
            t={t}
          />

          <FormError message={confirmError} />

          <div className="flex justify-between">
            <Button variant="ghost" onClick={() => setStep(1)}>
              {t("backStep")}
            </Button>
            <Button
              size="lg"
              loading={confirmLoading}
              disabled={!selectedDetailerId || !selectedSlot}
              onClick={handleConfirmBooking}
            >
              {t("confirmAndPay")}
            </Button>
          </div>
        </section>
      )}

      {/* STEP 3: Stripe Elements — authorize funds (manual capture) */}
      {step === 3 && clientSecret && amountCents !== null && (
        <section className="space-y-6">
          <SummaryCard
            service={selectedService?.name ?? "—"}
            vehiclesCount={selectedVehicles.length}
            address={serviceAddress}
            slotLabel={
              selectedSlot
                ? dateFormatter.format(new Date(selectedSlot.start_time))
                : null
            }
            detailerName={selectedDetailer?.full_name ?? null}
            priceCents={amountCents}
            t={t}
          />

          <SectionCard
            icon={<Sparkles className="size-5" />}
            title={t("steps.pay")}
          >
            <p className="mb-4 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs leading-relaxed text-zinc-600">
              {t("authNotice")}
            </p>
            <CheckoutForm
              clientSecret={clientSecret}
              amountCents={amountCents}
              returnUrl={
                typeof window !== "undefined"
                  ? `${window.location.origin}/client/appointments/${appointmentId}`
                  : ""
              }
              onSuccess={handlePaymentSuccess}
            />
          </SectionCard>
        </section>
      )}
    </div>
  );
}

function Steps({ current }: { current: Step }) {
  const t = useTranslations("book");
  const labels = [
    t("steps.service"),
    t("steps.date"),
    t("steps.match"),
    t("steps.pay"),
  ];
  return (
    <ol className="mb-8 flex items-center gap-2">
      {labels.map((label, i) => {
        const done = i < current;
        const isCurrent = i === current;
        return (
          <li key={label} className="flex flex-1 items-center gap-2">
            <span
              className={clsx(
                "flex size-7 shrink-0 items-center justify-center rounded-full border-2 text-xs font-semibold",
                done && "border-emerald-600 bg-emerald-600 text-white",
                isCurrent && "border-brand-600 bg-brand-600 text-white",
                !done && !isCurrent && "border-zinc-200 bg-white text-zinc-400"
              )}
            >
              {done ? <CheckCircle2 className="size-3.5" /> : i + 1}
            </span>
            <span
              className={clsx(
                "hidden text-xs font-medium sm:inline",
                done && "text-emerald-700",
                isCurrent && "text-zinc-900",
                !done && !isCurrent && "text-zinc-400"
              )}
            >
              {label}
            </span>
            {i < labels.length - 1 && (
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
  );
}

function SectionCard({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
      <header className="mb-4 flex items-center gap-2">
        <span className="flex size-8 items-center justify-center rounded-lg bg-zinc-100 text-zinc-700">
          {icon}
        </span>
        <h2 className="text-base font-semibold text-zinc-900">{title}</h2>
      </header>
      {children}
    </section>
  );
}

function SummaryCard({
  service,
  vehiclesCount,
  address,
  slotLabel,
  detailerName,
  priceCents,
  t,
}: {
  service: string;
  vehiclesCount: number;
  address: string;
  slotLabel: string | null;
  detailerName: string | null;
  priceCents: number | null;
  t: ReturnType<typeof useTranslations<"book">>;
}) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-5">
      <header className="mb-3 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
          {t("summary.title")}
        </h3>
        {priceCents != null && (
          <span className="font-display text-xl font-bold text-zinc-900">
            ${(priceCents / 100).toFixed(2)}
          </span>
        )}
      </header>
      <dl className="grid gap-2 text-sm">
        <SummaryRow label={t("summary.service")} value={service} />
        <SummaryRow
          label={t("summary.vehicles")}
          value={t("summary.vehiclesCount", { count: vehiclesCount })}
        />
        {slotLabel && (
          <SummaryRow label={t("summary.when")} value={slotLabel} />
        )}
        {detailerName && (
          <SummaryRow label={t("summary.detailer")} value={detailerName} />
        )}
        {address && (
          <SummaryRow label={t("summary.address")} value={address} />
        )}
      </dl>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-xs uppercase tracking-wider text-zinc-500">{label}</dt>
      <dd className="text-right text-sm text-zinc-900">{value}</dd>
    </div>
  );
}

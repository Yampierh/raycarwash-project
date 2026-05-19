"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Input } from "@/components/forms/Input";
import { Select } from "@/components/forms/Select";
import { Button } from "@/components/forms/Button";
import { FormError } from "@/components/forms/FormError";
import { lookupVin, type VehicleCreate } from "@/lib/api/vehicles";
import { Search, Loader2 } from "lucide-react";

const BODY_CLASSES = [
  "Sedan",
  "Coupe",
  "Hatchback",
  "SUV",
  "Truck",
  "Van",
  "Wagon",
  "Convertible",
  "Other",
];

const schema = z.object({
  make: z.string().min(1).max(60),
  model: z.string().min(1).max(60),
  year: z.number().int().min(1970).max(2030),
  body_class: z.string().min(1).max(60),
  vin: z
    .string()
    .trim()
    .transform((v) => (v === "" ? null : v.toUpperCase()))
    .pipe(
      z
        .string()
        .length(17, "VIN must be exactly 17 characters")
        .nullable()
    )
    .or(z.literal(null))
    .nullable(),
  color: z.string().max(40).optional(),
  license_plate: z
    .string()
    .max(20)
    .transform((v) => v.toUpperCase())
    .optional(),
  series: z.string().max(60).optional(),
  notes: z.string().max(1000).optional(),
});

export type VehicleFormValues = z.infer<typeof schema>;

type Props = {
  initialValues?: Partial<VehicleCreate>;
  onSubmit: (values: VehicleCreate) => Promise<void>;
  submitLabel: string;
  submittingLabel: string;
  serverError?: string | null;
};

export function VehicleForm({
  initialValues,
  onSubmit,
  submitLabel,
  submittingLabel,
  serverError,
}: Props) {
  const t = useTranslations("vehicleForm");
  const [vinLookupLoading, setVinLookupLoading] = useState(false);
  const [vinLookupError, setVinLookupError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<VehicleFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      make: initialValues?.make ?? "",
      model: initialValues?.model ?? "",
      year: initialValues?.year ?? new Date().getFullYear(),
      body_class: initialValues?.body_class ?? "Sedan",
      vin: initialValues?.vin ?? null,
      color: initialValues?.color ?? "",
      license_plate: initialValues?.license_plate ?? "",
      series: initialValues?.series ?? "",
      notes: initialValues?.notes ?? "",
    },
  });

  async function handleVinLookup() {
    setVinLookupError(null);
    const vin = (getValues("vin") ?? "").trim().toUpperCase();
    if (vin.length !== 17) {
      setVinLookupError(t("vinLength"));
      return;
    }
    setVinLookupLoading(true);
    try {
      const data = await lookupVin(vin);
      if (data.make) setValue("make", data.make);
      if (data.model) setValue("model", data.model);
      if (typeof data.year === "number") setValue("year", data.year);
      if (data.body_class) {
        const match = BODY_CLASSES.find(
          (c) => c.toLowerCase() === String(data.body_class).toLowerCase()
        );
        setValue("body_class", match ?? "Other");
      }
      if (data.series) setValue("series", String(data.series));
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("vinLookupError");
      setVinLookupError(typeof msg === "string" ? msg : t("vinLookupError"));
    } finally {
      setVinLookupLoading(false);
    }
  }

  async function submit(values: VehicleFormValues) {
    await onSubmit({
      make: values.make,
      model: values.model,
      year: values.year,
      body_class: values.body_class,
      vin: values.vin || null,
      color: values.color || null,
      license_plate: values.license_plate || null,
      series: values.series || null,
      notes: values.notes || null,
    });
  }

  return (
    <form
      onSubmit={handleSubmit(submit)}
      className="space-y-5 rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm"
    >
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-zinc-700">{t("vin")}</label>
        <div className="flex gap-2">
          <input
            {...register("vin")}
            placeholder="1HGCM82633A123456"
            maxLength={17}
            className="flex-1 rounded-lg border border-zinc-200 bg-white px-3 py-2 font-mono text-sm uppercase text-zinc-900 placeholder-zinc-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          />
          <Button
            type="button"
            variant="secondary"
            onClick={handleVinLookup}
            loading={vinLookupLoading}
          >
            {vinLookupLoading ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Search className="size-4" />
            )}
            {t("lookup")}
          </Button>
        </div>
        {vinLookupError && (
          <p className="text-xs text-red-600">{vinLookupError}</p>
        )}
        {errors.vin && (
          <p className="text-xs text-red-600">{errors.vin.message}</p>
        )}
        <p className="text-xs text-zinc-500">{t("vinHint")}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label={t("make")}
          error={errors.make?.message}
          {...register("make")}
        />
        <Input
          label={t("model")}
          error={errors.model?.message}
          {...register("model")}
        />
        <Input
          type="number"
          label={t("year")}
          error={errors.year?.message}
          {...register("year", { valueAsNumber: true })}
        />
        <Select
          label={t("bodyClass")}
          error={errors.body_class?.message}
          options={BODY_CLASSES.map((c) => ({ value: c, label: c }))}
          {...register("body_class")}
        />
        <Input
          label={t("color")}
          error={errors.color?.message}
          {...register("color")}
        />
        <Input
          label={t("plate")}
          error={errors.license_plate?.message}
          {...register("license_plate")}
        />
      </div>

      <FormError message={serverError} />

      <div className="flex justify-end">
        <Button type="submit" loading={isSubmitting}>
          {isSubmitting ? submittingLabel : submitLabel}
        </Button>
      </div>
    </form>
  );
}

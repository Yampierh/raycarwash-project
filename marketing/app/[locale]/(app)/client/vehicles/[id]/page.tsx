"use client";

import { useState, use } from "react";
import { useTranslations } from "next-intl";
import { useRouter, Link } from "@/i18n/navigation";
import { updateVehicle, type VehicleCreate } from "@/lib/api/vehicles";
import { useVehicles } from "@/lib/hooks/useVehicles";
import { VehicleForm } from "@/components/app/VehicleForm";
import { PageHeader } from "@/components/app/PageHeader";
import { ArrowLeft, Loader2 } from "lucide-react";

export default function EditVehiclePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const t = useTranslations("clientVehicleEdit");
  const router = useRouter();
  const { data: vehicles, mutate, isLoading } = useVehicles();
  const [serverError, setServerError] = useState<string | null>(null);

  const vehicle = vehicles?.find((v) => v.id === id);

  async function handleSubmit(values: VehicleCreate) {
    setServerError(null);
    try {
      const updated = await updateVehicle(id, values);
      await mutate(
        (cur) => cur?.map((v) => (v.id === id ? updated : v)),
        false
      );
      router.push("/client/vehicles");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("error");
      setServerError(typeof msg === "string" ? msg : t("error"));
      throw err;
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <Link
        href="/client/vehicles"
        className="mb-6 inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-900"
      >
        <ArrowLeft className="size-4" />
        {t("back")}
      </Link>

      <PageHeader title={t("title")} sub={t("sub")} />

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="size-6 animate-spin text-zinc-400" />
        </div>
      ) : !vehicle ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {t("notFound")}
        </div>
      ) : (
        <VehicleForm
          initialValues={{
            make: vehicle.make,
            model: vehicle.model,
            year: vehicle.year,
            body_class: vehicle.body_class ?? "Sedan",
            vin: vehicle.vin,
            series: vehicle.series,
            color: vehicle.color,
            license_plate: vehicle.license_plate,
          }}
          onSubmit={handleSubmit}
          submitLabel={t("submit")}
          submittingLabel={t("submitting")}
          serverError={serverError}
        />
      )}
    </div>
  );
}

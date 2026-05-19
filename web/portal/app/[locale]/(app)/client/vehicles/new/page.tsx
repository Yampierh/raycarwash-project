"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter, Link } from "@/i18n/navigation";
import { createVehicle, type VehicleCreate } from "@/lib/api/vehicles";
import { useVehicles } from "@/lib/hooks/useVehicles";
import { VehicleForm } from "@/components/app/VehicleForm";
import { PageHeader } from "@/components/app/PageHeader";
import { ArrowLeft } from "lucide-react";

export default function NewVehiclePage() {
  const t = useTranslations("clientVehicleNew");
  const router = useRouter();
  const { mutate } = useVehicles();
  const [serverError, setServerError] = useState<string | null>(null);

  async function handleSubmit(values: VehicleCreate) {
    setServerError(null);
    try {
      const created = await createVehicle(values);
      await mutate((cur) => (cur ? [...cur, created] : [created]), false);
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

      <VehicleForm
        onSubmit={handleSubmit}
        submitLabel={t("submit")}
        submittingLabel={t("submitting")}
        serverError={serverError}
      />
    </div>
  );
}

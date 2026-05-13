"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { useVehicles } from "@/lib/hooks/useVehicles";
import { deleteVehicle, type Vehicle } from "@/lib/api/vehicles";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { Button } from "@/components/forms/Button";
import { Car, Plus, Trash2, Loader2 } from "lucide-react";

export default function VehiclesPage() {
  const t = useTranslations("clientVehicles");
  const router = useRouter();
  const { data: vehicles, error, isLoading, mutate } = useVehicles();
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDelete(id: string, label: string) {
    if (!window.confirm(t("confirmDelete", { label }))) return;
    setDeletingId(id);
    try {
      await deleteVehicle(id);
      await mutate((current) =>
        current ? current.filter((v) => v.id !== id) : current
      );
    } catch {
      window.alert(t("deleteError"));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <PageHeader
        title={t("title")}
        sub={t("sub")}
        action={
          <Button onClick={() => router.push("/client/vehicles/new")}>
            <Plus className="size-4" /> {t("addVehicle")}
          </Button>
        }
      />

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

      {!isLoading && !error && vehicles && vehicles.length === 0 && (
        <EmptyState
          icon={<Car className="size-5" />}
          title={t("emptyTitle")}
          body={t("emptyBody")}
          action={
            <Button onClick={() => router.push("/client/vehicles/new")}>
              <Plus className="size-4" />
              {t("addVehicle")}
            </Button>
          }
        />
      )}

      {vehicles && vehicles.length > 0 && (
        <ul className="grid gap-4 md:grid-cols-2">
          {vehicles.map((v) => (
            <VehicleCard
              key={v.id}
              vehicle={v}
              onDelete={() =>
                handleDelete(v.id, `${v.year} ${v.make} ${v.model}`)
              }
              deleting={deletingId === v.id}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function VehicleCard({
  vehicle,
  onDelete,
  deleting,
}: {
  vehicle: Vehicle;
  onDelete: () => void;
  deleting: boolean;
}) {
  const t = useTranslations("clientVehicles");
  return (
    <li className="flex flex-col rounded-2xl border border-zinc-200 bg-white p-5">
      <div className="flex items-center justify-between">
        <span className="flex size-10 items-center justify-center rounded-lg bg-zinc-100 text-zinc-700">
          <Car className="size-5" />
        </span>
        {vehicle.suggested_size && (
          <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium uppercase tracking-wider text-brand-700">
            {vehicle.suggested_size}
          </span>
        )}
      </div>
      <h3 className="mt-4 text-base font-semibold text-zinc-900">
        {vehicle.year} {vehicle.make} {vehicle.model}
      </h3>
      <p className="mt-1 text-xs text-zinc-500">
        {vehicle.color} · {vehicle.license_plate}
      </p>
      {vehicle.vin && (
        <p className="mt-2 truncate font-mono text-[10px] uppercase text-zinc-400">
          VIN {vehicle.vin}
        </p>
      )}
      <div className="mt-4 flex items-center gap-2 border-t border-zinc-100 pt-4">
        <Link
          href={`/client/vehicles/${vehicle.id}`}
          className="text-sm font-medium text-zinc-700 underline-offset-4 hover:underline"
        >
          {t("edit")}
        </Link>
        <button
          type="button"
          onClick={onDelete}
          disabled={deleting}
          className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-red-600 transition hover:text-red-700 disabled:opacity-50"
        >
          {deleting ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <Trash2 className="size-3.5" />
          )}
          {t("delete")}
        </button>
      </div>
    </li>
  );
}

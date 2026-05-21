"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  listAddresses,
  createAddress,
  updateAddress,
  deleteAddress,
  setDefaultAddress,
  type Address,
} from "@/lib/api/addresses";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { Button } from "@/components/forms/Button";
import { Input } from "@/components/forms/Input";
import { FormError } from "@/components/forms/FormError";
import {
  MapPin,
  Plus,
  Star,
  Trash2,
  Pencil,
  X,
  Loader2,
  CheckCircle2,
} from "lucide-react";
import clsx from "clsx";

const schema = z.object({
  label: z.string().max(40).optional(),
  line1: z.string().min(1),
  line2: z.string().optional(),
  city: z.string().min(1),
  state: z.string().min(1),
  zip_code: z.string().min(1),
  is_default: z.boolean().optional(),
});
type FormValues = z.infer<typeof schema>;

export default function AddressesPage() {
  const t = useTranslations("clientAddresses");
  const { data, error, isLoading, mutate } = useSWR("addresses", listAddresses);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Address | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [defaultingId, setDefaultingId] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  function openCreate() {
    setEditing(null);
    reset({ label: "", line1: "", line2: "", city: "", state: "", zip_code: "" });
    setShowForm(true);
  }

  function openEdit(addr: Address) {
    setEditing(addr);
    reset({
      label: addr.label ?? "",
      line1: addr.line1,
      line2: addr.line2 ?? "",
      city: addr.city,
      state: addr.state,
      zip_code: addr.zip_code,
    });
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditing(null);
    setActionError(null);
  }

  async function onSubmit(values: FormValues) {
    setActionError(null);
    try {
      if (editing) {
        await updateAddress(editing.id, values);
      } else {
        await createAddress(values);
      }
      await mutate();
      closeForm();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("saveError");
      setActionError(typeof msg === "string" ? msg : t("saveError"));
    }
  }

  async function handleDelete(addr: Address) {
    if (!window.confirm(t("confirmDelete", { label: addr.line1 }))) return;
    setDeletingId(addr.id);
    setActionError(null);
    try {
      await deleteAddress(addr.id);
      await mutate();
    } catch {
      setActionError(t("deleteError"));
    } finally {
      setDeletingId(null);
    }
  }

  async function handleSetDefault(addr: Address) {
    setDefaultingId(addr.id);
    setActionError(null);
    try {
      await setDefaultAddress(addr.id);
      await mutate();
    } catch {
      setActionError(t("defaultError"));
    } finally {
      setDefaultingId(null);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <PageHeader
        title={t("title")}
        sub={t("sub")}
        action={
          !showForm ? (
            <Button size="sm" onClick={openCreate}>
              <Plus className="size-4" />
              {t("add")}
            </Button>
          ) : null
        }
      />

      {actionError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {actionError}
        </div>
      )}

      {showForm && (
        <div className="mb-6 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-zinc-900">
              {editing ? t("editTitle") : t("addTitle")}
            </h2>
            <button
              type="button"
              onClick={closeForm}
              className="rounded-lg p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
            >
              <X className="size-5" />
            </button>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label={t("label")}
              placeholder={t("labelPlaceholder")}
              error={errors.label?.message}
              {...register("label")}
            />
            <Input
              label={t("line1")}
              placeholder={t("line1Placeholder")}
              error={errors.line1?.message}
              {...register("line1")}
            />
            <Input
              label={t("line2")}
              placeholder={t("line2Placeholder")}
              error={errors.line2?.message}
              {...register("line2")}
            />
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <Input
                  label={t("city")}
                  error={errors.city?.message}
                  {...register("city")}
                />
              </div>
              <Input
                label={t("state")}
                placeholder="IN"
                error={errors.state?.message}
                {...register("state")}
              />
            </div>
            <Input
              label={t("zipCode")}
              placeholder="46802"
              error={errors.zip_code?.message}
              {...register("zip_code")}
            />

            <FormError message={actionError} />

            <div className="flex justify-end gap-3">
              <Button type="button" variant="ghost" onClick={closeForm}>
                {t("cancel")}
              </Button>
              <Button type="submit" loading={isSubmitting}>
                {isSubmitting ? t("saving") : t("save")}
              </Button>
            </div>
          </form>
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
          icon={<MapPin className="size-5" />}
          title={t("emptyTitle")}
          body={t("emptyBody")}
        />
      )}

      {!isLoading && data && data.length > 0 && (
        <ul className="flex flex-col gap-3">
          {data.map((addr) => (
            <li
              key={addr.id}
              className={clsx(
                "rounded-2xl border bg-white p-5 transition",
                addr.is_default ? "border-zinc-900" : "border-zinc-200"
              )}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    {addr.label && (
                      <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                        {addr.label}
                      </span>
                    )}
                    {addr.is_default && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-zinc-900 px-2 py-0.5 text-xs font-medium text-white">
                        <CheckCircle2 className="size-3" />
                        {t("default")}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-sm font-medium text-zinc-900">{addr.line1}</p>
                  {addr.line2 && (
                    <p className="text-sm text-zinc-600">{addr.line2}</p>
                  )}
                  <p className="text-sm text-zinc-600">
                    {addr.city}, {addr.state} {addr.zip_code}
                  </p>
                </div>

                <div className="flex shrink-0 items-center gap-1">
                  {!addr.is_default && (
                    <button
                      type="button"
                      onClick={() => handleSetDefault(addr)}
                      disabled={defaultingId === addr.id}
                      title={t("setDefault")}
                      className="rounded-lg p-2 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 disabled:opacity-50"
                    >
                      {defaultingId === addr.id ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <Star className="size-4" />
                      )}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => openEdit(addr)}
                    title={t("edit")}
                    className="rounded-lg p-2 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700"
                  >
                    <Pencil className="size-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(addr)}
                    disabled={deletingId === addr.id}
                    title={t("delete")}
                    className="rounded-lg p-2 text-zinc-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                  >
                    {deletingId === addr.id ? (
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

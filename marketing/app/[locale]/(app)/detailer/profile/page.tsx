"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useDetailerMe } from "@/lib/hooks/useDetailerMe";
import { updateMyDetailer } from "@/lib/api/detailer";
import { useAuthStore } from "@/lib/store/auth";
import { PageHeader } from "@/components/app/PageHeader";
import { Input } from "@/components/forms/Input";
import { Button } from "@/components/forms/Button";
import { FormError } from "@/components/forms/FormError";
import { Loader2, CheckCircle2 } from "lucide-react";

const schema = z.object({
  bio: z.string().max(1000).optional(),
  years_of_experience: z
    .number()
    .int()
    .min(0)
    .max(50)
    .nullable()
    .optional(),
  service_radius_miles: z.number().int().min(1).max(100),
});
type FormValues = z.infer<typeof schema>;

export default function DetailerProfilePage() {
  const t = useTranslations("detailerProfile");
  const { data: me, isLoading, mutate } = useDetailerMe();
  const clear = useAuthStore((s) => s.clear);
  const [serverError, setServerError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { bio: "", years_of_experience: null, service_radius_miles: 25 },
  });

  useEffect(() => {
    if (me) {
      reset({
        bio: me.bio ?? "",
        years_of_experience: me.years_of_experience ?? null,
        service_radius_miles: me.service_radius_miles,
      });
    }
  }, [me, reset]);

  async function onSubmit(values: FormValues) {
    setServerError(null);
    setSaved(false);
    try {
      const updated = await updateMyDetailer({
        bio: values.bio || null,
        years_of_experience: values.years_of_experience ?? null,
        service_radius_miles: values.service_radius_miles,
      });
      await mutate(updated, false);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("error");
      setServerError(typeof msg === "string" ? msg : t("error"));
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <PageHeader title={t("title")} sub={t("sub")} />

      {isLoading && (
        <div className="flex justify-center py-16">
          <Loader2 className="size-6 animate-spin text-zinc-400" />
        </div>
      )}

      {me && (
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-5 rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm"
        >
          <div className="flex items-center gap-4 border-b border-zinc-100 pb-4">
            <span className="flex size-12 items-center justify-center rounded-full bg-brand-600 text-base font-bold text-white">
              {me.full_name.slice(0, 1).toUpperCase()}
            </span>
            <div>
              <div className="text-base font-semibold text-zinc-900">
                {me.full_name}
              </div>
              <div className="text-xs text-zinc-500">
                {t("memberSince", {
                  date: new Date(me.created_at).toLocaleDateString(),
                })}
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-zinc-700">
              {t("bio")}
            </label>
            <textarea
              rows={4}
              maxLength={1000}
              placeholder={t("bioPlaceholder")}
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              {...register("bio")}
            />
            {errors.bio && (
              <p className="text-xs text-red-600">{errors.bio.message}</p>
            )}
          </div>

          <Input
            type="number"
            label={t("years")}
            error={errors.years_of_experience?.message}
            {...register("years_of_experience", {
              setValueAs: (v) => (v === "" || v == null ? null : Number(v)),
            })}
          />

          <Input
            type="number"
            label={t("radius")}
            hint={t("radiusHint")}
            error={errors.service_radius_miles?.message}
            {...register("service_radius_miles", { valueAsNumber: true })}
          />

          {saved && (
            <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              <CheckCircle2 className="size-4" />
              {t("saved")}
            </div>
          )}

          <FormError message={serverError} />

          <div className="flex items-center justify-between">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                clear();
                window.location.href = "/";
              }}
            >
              {t("signOut")}
            </Button>
            <Button type="submit" loading={isSubmitting} disabled={!isDirty}>
              {isSubmitting ? t("saving") : t("save")}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}

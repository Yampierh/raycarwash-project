"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMe } from "@/lib/hooks/useMe";
import { updateMe } from "@/lib/api/user";
import { useAuthStore } from "@/lib/store/auth";
import { PageHeader } from "@/components/app/PageHeader";
import { Input } from "@/components/forms/Input";
import { Button } from "@/components/forms/Button";
import { FormError } from "@/components/forms/FormError";
import { Loader2, CheckCircle2 } from "lucide-react";

const schema = z.object({
  full_name: z.string().min(2),
  phone_number: z.string().min(7).regex(/^[+0-9 ()\-]+$/),
});
type FormValues = z.infer<typeof schema>;

export default function ProfilePage() {
  const t = useTranslations("clientProfile");
  const { data: me, isLoading, mutate } = useMe();
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
    defaultValues: { full_name: "", phone_number: "" },
  });

  useEffect(() => {
    if (me) {
      reset({
        full_name: me.full_name ?? "",
        phone_number: me.phone_number ?? "",
      });
    }
  }, [me, reset]);

  async function onSubmit(values: FormValues) {
    setServerError(null);
    setSaved(false);
    try {
      const updated = await updateMe(values);
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
              {(me.full_name ?? me.email).slice(0, 1).toUpperCase()}
            </span>
            <div>
              <div className="text-xs uppercase tracking-wider text-zinc-500">
                {t("email")}
              </div>
              <div className="font-mono text-sm text-zinc-700">{me.email}</div>
            </div>
          </div>

          <Input
            label={t("fullName")}
            error={errors.full_name?.message}
            {...register("full_name")}
          />
          <Input
            label={t("phone")}
            type="tel"
            error={errors.phone_number?.message}
            {...register("phone_number")}
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

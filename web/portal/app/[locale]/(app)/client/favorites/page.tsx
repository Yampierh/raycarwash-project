"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import { Link } from "@/i18n/navigation";
import { listFavorites, removeFavorite, type FavoriteProvider } from "@/lib/api/favorites";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { Heart, Star, Trash2, Loader2, ArrowRight } from "lucide-react";

function ProviderAvatar({
  name,
  avatarUrl,
}: {
  name: string | null;
  avatarUrl: string | null;
}) {
  const initial = (name ?? "?").slice(0, 1).toUpperCase();
  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt={name ?? ""}
        className="size-12 rounded-full object-cover"
      />
    );
  }
  return (
    <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-brand-600 text-base font-bold text-white">
      {initial}
    </span>
  );
}

export default function FavoritesPage() {
  const t = useTranslations("clientFavorites");
  const { data, error, isLoading, mutate } = useSWR("favorites", listFavorites);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function handleRemove(fav: FavoriteProvider) {
    if (!window.confirm(t("confirmRemove", { name: fav.display_name ?? t("thisProvider") })))
      return;
    setRemovingId(fav.provider_user_id);
    setActionError(null);
    try {
      await removeFavorite(fav.provider_user_id);
      await mutate();
    } catch {
      setActionError(t("removeError"));
    } finally {
      setRemovingId(null);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <PageHeader title={t("title")} sub={t("sub")} />

      {actionError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {actionError}
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
          icon={<Heart className="size-5" />}
          title={t("emptyTitle")}
          body={t("emptyBody")}
        />
      )}

      {!isLoading && data && data.length > 0 && (
        <ul className="flex flex-col gap-3">
          {data.map((fav) => (
            <li
              key={fav.provider_user_id}
              className="flex items-center gap-4 rounded-2xl border border-zinc-200 bg-white p-5 transition hover:border-zinc-300"
            >
              <ProviderAvatar
                name={fav.display_name}
                avatarUrl={fav.avatar_url}
              />

              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-zinc-900">
                  {fav.display_name ?? t("unknownProvider")}
                </p>
                {fav.business_name && (
                  <p className="truncate text-xs text-zinc-500">{fav.business_name}</p>
                )}
                {fav.rating != null && (
                  <div className="mt-1 flex items-center gap-1">
                    <Star className="size-3.5 fill-amber-400 text-amber-400" />
                    <span className="text-xs font-medium text-zinc-700">
                      {fav.rating.toFixed(1)}
                    </span>
                  </div>
                )}
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <Link
                  href="/client/book"
                  className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs font-semibold text-zinc-700 transition hover:bg-zinc-50"
                >
                  {t("book")}
                  <ArrowRight className="size-3.5" />
                </Link>
                <button
                  type="button"
                  onClick={() => handleRemove(fav)}
                  disabled={removingId === fav.provider_user_id}
                  title={t("remove")}
                  className="rounded-lg p-2 text-zinc-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                >
                  {removingId === fav.provider_user_id ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Trash2 className="size-4" />
                  )}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

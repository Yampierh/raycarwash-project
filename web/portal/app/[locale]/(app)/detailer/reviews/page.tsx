"use client";

import { useTranslations, useLocale } from "next-intl";
import useSWR from "swr";
import { useDetailerMe } from "@/lib/hooks/useDetailerMe";
import { getDetailerReviews } from "@/lib/api/reviews";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { Star, MessageSquare, Loader2 } from "lucide-react";

function StarRow({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          className={`size-4 ${n <= rating ? "fill-amber-400 text-amber-400" : "text-zinc-200"}`}
        />
      ))}
    </div>
  );
}

function RatingBar({ rating, count, total }: { rating: number; count: number; total: number }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="w-4 text-right text-sm font-medium text-zinc-700">{rating}</span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-zinc-100">
        <div
          className="h-full rounded-full bg-amber-400 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-8 text-xs text-zinc-400">{count}</span>
    </div>
  );
}

export default function DetailerReviewsPage() {
  const t = useTranslations("detailerReviews");
  const locale = useLocale();
  const { data: me, isLoading: meLoading } = useDetailerMe();

  const { data, isLoading, error } = useSWR(
    me ? `/reviews/detailer/${me.user_id}` : null,
    () => getDetailerReviews(me!.user_id, { per_page: 50 })
  );

  const dateFormatter = new Intl.DateTimeFormat(locale, { dateStyle: "medium" });

  const reviews = data?.items ?? [];
  const avgRating = data?.average_rating ?? me?.average_rating ?? null;
  const totalCount = data?.total ?? 0;

  const ratingCounts = [5, 4, 3, 2, 1].map((r) => ({
    rating: r,
    count: reviews.filter((rv) => rv.rating === r).length,
  }));

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <PageHeader title={t("title")} sub={t("sub")} />

      {(isLoading || meLoading) && (
        <div className="flex justify-center py-16">
          <Loader2 className="size-6 animate-spin text-zinc-400" />
        </div>
      )}

      {error && !isLoading && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {t("loadError")}
        </div>
      )}

      {!isLoading && !meLoading && !error && (
        <>
          {avgRating != null && totalCount > 0 && (
            <div className="mb-6 rounded-2xl border border-zinc-200 bg-white p-6">
              <div className="flex items-center gap-6">
                <div className="text-center">
                  <div className="font-display text-5xl font-bold text-zinc-900">
                    {avgRating.toFixed(1)}
                  </div>
                  <StarRow rating={Math.round(avgRating)} />
                  <p className="mt-1 text-xs text-zinc-500">
                    {t("totalReviews", { count: totalCount })}
                  </p>
                </div>
                <div className="flex-1 space-y-1.5">
                  {ratingCounts.map(({ rating, count }) => (
                    <RatingBar
                      key={rating}
                      rating={rating}
                      count={count}
                      total={totalCount}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {reviews.length === 0 ? (
            <EmptyState
              icon={<MessageSquare className="size-5" />}
              title={t("emptyTitle")}
              body={t("emptyBody")}
            />
          ) : (
            <ul className="flex flex-col gap-4">
              {reviews.map((review) => (
                <li
                  key={review.id}
                  className="rounded-2xl border border-zinc-200 bg-white p-5"
                >
                  <div className="flex items-center justify-between gap-3">
                    <StarRow rating={review.rating} />
                    <time className="text-xs text-zinc-400">
                      {dateFormatter.format(new Date(review.created_at))}
                    </time>
                  </div>
                  {review.comment && (
                    <p className="mt-3 text-sm leading-relaxed text-zinc-700">
                      {review.comment}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

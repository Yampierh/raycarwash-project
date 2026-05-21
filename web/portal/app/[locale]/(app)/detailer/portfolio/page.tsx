"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import {
  listPortfolioPhotos,
  deletePortfolioPhoto,
  uploadPortfolioPhoto,
  type PortfolioPhoto,
} from "@/lib/api/provider-portfolio";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { Button } from "@/components/forms/Button";
import { Input } from "@/components/forms/Input";
import { Images, Trash2, Plus, Upload, Loader2, X } from "lucide-react";
import clsx from "clsx";

const TAGS = ["before", "after", "hero", "detail"];
const MAX_PHOTOS = 30;
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_SIZE_MB = 8;

export default function DetailerPortfolioPage() {
  const t = useTranslations("detailerPortfolio");
  const { data, isLoading, error, mutate } = useSWR(
    "/users/me/provider-portfolio",
    listPortfolioPhotos
  );

  const fileRef = useRef<HTMLInputElement>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [caption, setCaption] = useState("");
  const [tag, setTag] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const photos = data ?? [];
  const atCap = photos.length >= MAX_PHOTOS;

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!ALLOWED_TYPES.includes(file.type)) {
      setUploadError(t("invalidType"));
      return;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      setUploadError(t("tooLarge", { mb: MAX_SIZE_MB }));
      return;
    }
    setUploadError(null);
    setSelectedFile(file);
    setPreview(URL.createObjectURL(file));
  }

  function cancelUpload() {
    setShowUpload(false);
    setSelectedFile(null);
    setPreview(null);
    setCaption("");
    setTag("");
    setUploadError(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  async function handleUpload() {
    if (!selectedFile) return;
    setUploading(true);
    setUploadError(null);
    try {
      await uploadPortfolioPhoto(
        selectedFile,
        caption.trim() || undefined,
        tag || undefined
      );
      await mutate();
      cancelUpload();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? t("uploadError");
      setUploadError(typeof msg === "string" ? msg : t("uploadError"));
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(photo: PortfolioPhoto) {
    if (!window.confirm(t("confirmDelete"))) return;
    setDeletingId(photo.id);
    setActionError(null);
    try {
      await deletePortfolioPhoto(photo.id);
      await mutate();
    } catch {
      setActionError(t("deleteError"));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <PageHeader
        title={t("title")}
        sub={t("sub", { count: photos.length, max: MAX_PHOTOS })}
        action={
          !showUpload && !atCap ? (
            <Button size="sm" onClick={() => setShowUpload(true)}>
              <Plus className="size-4" />
              {t("addPhoto")}
            </Button>
          ) : undefined
        }
      />

      {actionError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {actionError}
        </div>
      )}

      {showUpload && (
        <div className="mb-8 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-zinc-900">
              {t("uploadTitle")}
            </h2>
            <button
              type="button"
              onClick={cancelUpload}
              className="rounded-lg p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
            >
              <X className="size-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <input
                ref={fileRef}
                type="file"
                accept={ALLOWED_TYPES.join(",")}
                onChange={handleFileChange}
                className="hidden"
                id="portfolio-file"
              />
              <label
                htmlFor="portfolio-file"
                className={clsx(
                  "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition",
                  preview
                    ? "border-zinc-200"
                    : "border-zinc-300 hover:border-zinc-400"
                )}
              >
                {preview ? (
                  <img
                    src={preview}
                    alt=""
                    className="max-h-48 rounded-lg object-contain"
                  />
                ) : (
                  <>
                    <Upload className="mb-2 size-8 text-zinc-400" />
                    <p className="text-sm font-medium text-zinc-700">
                      {t("dropzoneLabel")}
                    </p>
                    <p className="mt-1 text-xs text-zinc-400">
                      {t("dropzoneHint", { mb: MAX_SIZE_MB })}
                    </p>
                  </>
                )}
              </label>
            </div>

            <Input
              label={t("caption")}
              placeholder={t("captionPlaceholder")}
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              maxLength={200}
            />

            <div>
              <label className="mb-1.5 block text-sm font-medium text-zinc-700">
                {t("tag")}
              </label>
              <div className="flex flex-wrap gap-2">
                {TAGS.map((tg) => (
                  <button
                    key={tg}
                    type="button"
                    onClick={() => setTag(tag === tg ? "" : tg)}
                    className={clsx(
                      "rounded-full px-3 py-1 text-sm font-medium transition",
                      tag === tg
                        ? "bg-zinc-900 text-white"
                        : "border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50"
                    )}
                  >
                    {t(`tags.${tg}`)}
                  </button>
                ))}
              </div>
            </div>

            {uploadError && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {uploadError}
              </div>
            )}

            <div className="flex justify-end gap-3">
              <Button variant="ghost" onClick={cancelUpload}>
                {t("cancel")}
              </Button>
              <Button
                onClick={handleUpload}
                loading={uploading}
                disabled={!selectedFile}
              >
                {uploading ? t("uploading") : t("upload")}
              </Button>
            </div>
          </div>
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

      {!isLoading && !error && photos.length === 0 && (
        <EmptyState
          icon={<Images className="size-5" />}
          title={t("emptyTitle")}
          body={t("emptyBody")}
        />
      )}

      {!isLoading && photos.length > 0 && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {photos.map((photo) => (
            <div
              key={photo.id}
              className="group relative overflow-hidden rounded-2xl border border-zinc-200 bg-zinc-100"
            >
              {photo.photo_url ? (
                <img
                  src={photo.photo_url}
                  alt={photo.caption ?? ""}
                  className="aspect-square w-full object-cover"
                />
              ) : (
                <div className="flex aspect-square items-center justify-center">
                  <Images className="size-8 text-zinc-300" />
                </div>
              )}

              <div className="absolute inset-0 flex flex-col justify-between bg-gradient-to-t from-black/60 via-transparent to-transparent p-3 opacity-0 transition group-hover:opacity-100">
                {photo.tag && (
                  <span className="self-start rounded-full bg-white/20 px-2 py-0.5 text-xs font-semibold text-white backdrop-blur-sm">
                    {photo.tag}
                  </span>
                )}
                <div className="flex items-end justify-between">
                  {photo.caption && (
                    <p className="flex-1 truncate text-xs text-white">
                      {photo.caption}
                    </p>
                  )}
                  <button
                    type="button"
                    onClick={() => handleDelete(photo)}
                    disabled={deletingId === photo.id}
                    className="ml-2 shrink-0 rounded-full bg-red-600/90 p-1.5 text-white transition hover:bg-red-700 disabled:opacity-50"
                  >
                    {deletingId === photo.id ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="size-3.5" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {atCap && (
        <p className="mt-4 text-center text-xs text-zinc-400">
          {t("capReached", { max: MAX_PHOTOS })}
        </p>
      )}
    </div>
  );
}

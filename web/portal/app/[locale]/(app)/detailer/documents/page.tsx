"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import {
  listProviderDocuments,
  deleteProviderDocument,
  uploadProviderDocument,
  DOCUMENT_TYPES,
  type ProviderDocument,
} from "@/lib/api/provider-documents";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { Button } from "@/components/forms/Button";
import { Input } from "@/components/forms/Input";
import { Select } from "@/components/forms/Select";
import {
  FileText,
  Trash2,
  Plus,
  Download,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  X,
  Upload,
} from "lucide-react";
import clsx from "clsx";

const MAX_SIZE_MB = 20;
const ALLOWED_TYPES = ["image/jpeg", "image/png", "application/pdf"];

function isExpiringSoon(expiresAt: string | null): boolean {
  if (!expiresAt) return false;
  const days = (new Date(expiresAt).getTime() - Date.now()) / (1000 * 60 * 60 * 24);
  return days < 30 && days >= 0;
}

function isExpired(expiresAt: string | null): boolean {
  if (!expiresAt) return false;
  return new Date(expiresAt).getTime() < Date.now();
}

export default function DetailerDocumentsPage() {
  const t = useTranslations("detailerDocuments");
  const { data, isLoading, error, mutate } = useSWR(
    "/users/me/provider-documents",
    listProviderDocuments
  );

  const fileRef = useRef<HTMLInputElement>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<string>(DOCUMENT_TYPES[0]);
  const [docTitle, setDocTitle] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const docs = data ?? [];

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
  }

  function cancelUpload() {
    setShowUpload(false);
    setSelectedFile(null);
    setDocTitle("");
    setExpiresAt("");
    setDocType(DOCUMENT_TYPES[0]);
    setUploadError(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  async function handleUpload() {
    if (!selectedFile) return;
    setUploading(true);
    setUploadError(null);
    try {
      await uploadProviderDocument(
        selectedFile,
        docType,
        docTitle.trim() || undefined,
        expiresAt || undefined
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

  async function handleDelete(doc: ProviderDocument) {
    if (!window.confirm(t("confirmDelete", { title: doc.title ?? doc.type })))
      return;
    setDeletingId(doc.id);
    setActionError(null);
    try {
      await deleteProviderDocument(doc.id);
      await mutate();
    } catch {
      setActionError(t("deleteError"));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <PageHeader
        title={t("title")}
        sub={t("sub")}
        action={
          !showUpload ? (
            <Button size="sm" onClick={() => setShowUpload(true)}>
              <Plus className="size-4" />
              {t("addDocument")}
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
            <Select
              label={t("docType")}
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              options={DOCUMENT_TYPES.map((type) => ({
                value: type,
                label: t(`types.${type}` as `types.${typeof DOCUMENT_TYPES[number]}`),
              }))}
            />

            <Input
              label={t("docTitle")}
              placeholder={t("docTitlePlaceholder")}
              value={docTitle}
              onChange={(e) => setDocTitle(e.target.value)}
              maxLength={120}
            />

            <Input
              type="date"
              label={t("expiresAt")}
              hint={t("expiresAtHint")}
              value={expiresAt}
              onChange={(e) => setExpiresAt(e.target.value)}
            />

            <div>
              <input
                ref={fileRef}
                type="file"
                accept={ALLOWED_TYPES.join(",")}
                onChange={handleFileChange}
                className="hidden"
                id="doc-file"
              />
              <label
                htmlFor="doc-file"
                className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-zinc-300 p-6 text-center transition hover:border-zinc-400"
              >
                <Upload className="mb-2 size-7 text-zinc-400" />
                {selectedFile ? (
                  <p className="text-sm font-medium text-zinc-900">
                    {selectedFile.name}
                  </p>
                ) : (
                  <>
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

      {!isLoading && !error && docs.length === 0 && (
        <EmptyState
          icon={<FileText className="size-5" />}
          title={t("emptyTitle")}
          body={t("emptyBody")}
        />
      )}

      {!isLoading && docs.length > 0 && (
        <ul className="flex flex-col gap-3">
          {docs.map((doc) => {
            const expired = isExpired(doc.expires_at);
            const expiring = !expired && isExpiringSoon(doc.expires_at);
            return (
              <li
                key={doc.id}
                className={clsx(
                  "rounded-2xl border bg-white p-5",
                  expired
                    ? "border-red-200"
                    : expiring
                    ? "border-amber-200"
                    : "border-zinc-200"
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-semibold text-zinc-600">
                        {t(`types.${doc.type}` as const, {
                          defaultMessage: doc.type,
                        })}
                      </span>
                      {expired && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
                          <AlertTriangle className="size-3" />
                          {t("expired")}
                        </span>
                      )}
                      {expiring && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">
                          <AlertTriangle className="size-3" />
                          {t("expiringSoon")}
                        </span>
                      )}
                      {!expired && !expiring && doc.expires_at == null && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                          <CheckCircle2 className="size-3" />
                          {t("noExpiry")}
                        </span>
                      )}
                    </div>

                    <p className="mt-2 text-sm font-medium text-zinc-900">
                      {doc.title ?? t(`types.${doc.type}` as const, { defaultMessage: doc.type })}
                    </p>

                    {doc.expires_at && (
                      <p className="mt-1 text-xs text-zinc-500">
                        {t("expiresLabel")}:{" "}
                        {new Date(doc.expires_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>

                  <div className="flex shrink-0 items-center gap-1">
                    {doc.download_url && (
                      <a
                        href={doc.download_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title={t("download")}
                        className="rounded-lg p-2 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700"
                      >
                        <Download className="size-4" />
                      </a>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDelete(doc)}
                      disabled={deletingId === doc.id}
                      title={t("delete")}
                      className="rounded-lg p-2 text-zinc-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                    >
                      {deletingId === doc.id ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <Trash2 className="size-4" />
                      )}
                    </button>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

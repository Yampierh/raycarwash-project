"use client";

import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import useSWR from "swr";
import {
  getSecuritySummary,
  listSessions,
  revokeSession,
  revokeAllSessions,
  type Session,
} from "@/lib/api/security";
import { useAuthStore } from "@/lib/store/auth";
import { PageHeader } from "@/components/app/PageHeader";
import { Button } from "@/components/forms/Button";
import {
  Shield,
  Key,
  Smartphone,
  AlertTriangle,
  LogOut,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
} from "lucide-react";
import clsx from "clsx";

function SectionCard({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("rounded-2xl border border-zinc-200 bg-white p-6", className)}>
      {children}
    </div>
  );
}

function StatusRow({
  label,
  enabled,
  enabledLabel,
  disabledLabel,
}: {
  label: string;
  enabled: boolean;
  enabledLabel: string;
  disabledLabel: string;
}) {
  return (
    <div className="flex items-center justify-between py-3 first:pt-0 last:pb-0 border-b border-zinc-100 last:border-b-0">
      <span className="text-sm text-zinc-700">{label}</span>
      <span
        className={clsx(
          "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold",
          enabled
            ? "bg-emerald-50 text-emerald-700"
            : "bg-zinc-100 text-zinc-500"
        )}
      >
        {enabled ? (
          <CheckCircle2 className="size-3.5" />
        ) : (
          <XCircle className="size-3.5" />
        )}
        {enabled ? enabledLabel : disabledLabel}
      </span>
    </div>
  );
}

export default function SecurityPage() {
  const t = useTranslations("clientSecurity");
  const locale = useLocale();
  const clear = useAuthStore((s) => s.clear);

  const { data: summary, isLoading: summaryLoading } = useSWR("security-summary", getSecuritySummary);
  const { data: sessionsData, isLoading: sessionsLoading, mutate: mutateSessions } = useSWR(
    "sessions",
    listSessions
  );

  const [revokingId, setRevokingId] = useState<string | null>(null);
  const [revokeAllLoading, setRevokeAllLoading] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const dateFormatter = new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  async function handleRevokeSession(session: Session) {
    setRevokingId(session.family_id);
    setSessionError(null);
    try {
      await revokeSession(session.family_id);
      await mutateSessions();
    } catch {
      setSessionError(t("revokeError"));
    } finally {
      setRevokingId(null);
    }
  }

  async function handleRevokeAll() {
    if (!window.confirm(t("confirmRevokeAll"))) return;
    setRevokeAllLoading(true);
    setSessionError(null);
    try {
      await revokeAllSessions();
      clear();
    } catch {
      setSessionError(t("revokeError"));
      setRevokeAllLoading(false);
    }
  }

  const sessions = sessionsData?.sessions ?? [];
  const activeSessions = sessions.filter((s) => !s.revoked);

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <PageHeader title={t("title")} sub={t("sub")} />

      <div className="space-y-6">
        {/* Security Overview */}
        <SectionCard>
          <div className="mb-4 flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-zinc-100">
              <Shield className="size-5 text-zinc-600" />
            </div>
            <h2 className="text-base font-semibold text-zinc-900">{t("overview")}</h2>
          </div>

          {summaryLoading ? (
            <div className="flex justify-center py-6">
              <Loader2 className="size-5 animate-spin text-zinc-400" />
            </div>
          ) : summary ? (
            <div>
              <StatusRow
                label={t("password")}
                enabled={summary.has_password}
                enabledLabel={t("set")}
                disabledLabel={t("notSet")}
              />
              <StatusRow
                label={t("twoFactor")}
                enabled={summary.two_factor_enabled}
                enabledLabel={t("enabled")}
                disabledLabel={t("disabled")}
              />
              <StatusRow
                label={t("passkeys")}
                enabled={summary.passkeys_count > 0}
                enabledLabel={t("passkeysCount", { count: summary.passkeys_count })}
                disabledLabel={t("none")}
              />
              {summary.recent_failed_attempts > 0 && (
                <div className="mt-4 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3">
                  <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600" />
                  <p className="text-xs text-amber-800">
                    {t("failedAttempts", { count: summary.recent_failed_attempts })}
                  </p>
                </div>
              )}
            </div>
          ) : null}
        </SectionCard>

        {/* Password */}
        <SectionCard>
          <div className="mb-4 flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-zinc-100">
              <Key className="size-5 text-zinc-600" />
            </div>
            <h2 className="text-base font-semibold text-zinc-900">{t("passwordSection")}</h2>
          </div>
          <p className="mb-4 text-sm text-zinc-600">{t("passwordHint")}</p>
          <a
            href="/forgot-password"
            className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-4 py-2 text-sm font-semibold text-zinc-700 shadow-sm transition hover:bg-zinc-50"
          >
            {t("resetPassword")}
          </a>
        </SectionCard>

        {/* Active Sessions */}
        <SectionCard>
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex size-9 items-center justify-center rounded-lg bg-zinc-100">
                <Smartphone className="size-5 text-zinc-600" />
              </div>
              <h2 className="text-base font-semibold text-zinc-900">{t("sessions")}</h2>
            </div>
            {activeSessions.length > 1 && (
              <Button
                size="sm"
                variant="danger"
                onClick={handleRevokeAll}
                loading={revokeAllLoading}
              >
                <LogOut className="size-3.5" />
                {t("logOutAll")}
              </Button>
            )}
          </div>

          {sessionError && (
            <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {sessionError}
            </div>
          )}

          {sessionsLoading ? (
            <div className="flex justify-center py-6">
              <Loader2 className="size-5 animate-spin text-zinc-400" />
            </div>
          ) : activeSessions.length === 0 ? (
            <p className="text-sm text-zinc-500">{t("noSessions")}</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {activeSessions.map((session) => (
                <li
                  key={session.family_id}
                  className="flex items-center justify-between gap-3 rounded-xl border border-zinc-100 bg-zinc-50 px-4 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <Clock className="size-3.5 shrink-0 text-zinc-400" />
                      <span className="text-xs text-zinc-500">
                        {t("started")}{" "}
                        {dateFormatter.format(new Date(session.created_at))}
                      </span>
                    </div>
                    {session.last_used_at && (
                      <p className="mt-0.5 text-xs text-zinc-400">
                        {t("lastSeen")}{" "}
                        {dateFormatter.format(new Date(session.last_used_at))}
                      </p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRevokeSession(session)}
                    disabled={revokingId === session.family_id}
                    className="shrink-0 rounded-lg px-3 py-1.5 text-xs font-semibold text-red-600 transition hover:bg-red-50 disabled:opacity-50"
                  >
                    {revokingId === session.family_id ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      t("revoke")
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
      </div>
    </div>
  );
}

/**
 * frontend/src/services/auth-security.service.ts
 *
 * Wraps /api/v1/auth/{security,history,two-fa,passkeys} (Phase 3 chunk O).
 *
 * Lives under /auth/* on the backend per ADR-001 (identity stays out of
 * /users/me). The SecurityScreen reads `security` + `history` here and
 * issues the 2FA / passkey management calls from this same module so
 * there's one source of truth for the typed shapes.
 */
import { apiClient, unwrap } from "./api";

// ─── /auth/security ───────────────────────────────────────────────────────────

export interface SecuritySummary {
  has_password: boolean;
  two_factor_enabled: boolean;
  passkeys_count: number;
  last_password_change: string | null;
  last_login_at: string | null;
  step_up_recent: boolean;
  active_sessions_count: number;
  recent_failed_attempts: number;
}

export async function getSecuritySummary(): Promise<SecuritySummary> {
  const res = await apiClient.get("/auth/security");
  return unwrap<SecuritySummary>(res);
}

// ─── /auth/history ────────────────────────────────────────────────────────────

export interface SecurityHistoryItem {
  id: string;
  type: "login" | "audit";
  occurred_at: string;
  summary: string;
  ip_address: string | null;
  user_agent: string | null;
  device_name: string | null;
  was_successful: boolean | null;
  failure_reason: string | null;
  details: Record<string, unknown> | null;
}

export async function getSecurityHistory(limit = 20): Promise<SecurityHistoryItem[]> {
  const res = await apiClient.get("/auth/history", { params: { limit } });
  // PaginatedEnvelope -> data is the array directly.
  return res.data.data as SecurityHistoryItem[];
}

// ─── /auth/two-fa ─────────────────────────────────────────────────────────────

export interface TotpEnrollResult {
  secret: string;
  otpauth_uri: string;
  backup_codes: string[];
}

export async function enrollTotp(): Promise<TotpEnrollResult> {
  const res = await apiClient.post("/auth/two-fa/enroll");
  return unwrap<TotpEnrollResult>(res);
}

export async function verifyTotp(code: string): Promise<SecuritySummary> {
  // /verify echoes back the refreshed summary.
  const res = await apiClient.post("/auth/two-fa/verify", { code });
  return unwrap<SecuritySummary>(res);
}

export async function disableTotp(): Promise<void> {
  await apiClient.delete("/auth/two-fa");
}

export async function regenerateBackupCodes(): Promise<string[]> {
  const res = await apiClient.post("/auth/two-fa/backup-codes/regenerate");
  return unwrap<{ backup_codes: string[] }>(res).backup_codes;
}

// ─── /auth/passkeys ───────────────────────────────────────────────────────────

export interface PasskeySummary {
  id: string;
  device_name: string | null;
  created_at: string;
  last_used_at: string | null;
}

export async function listPasskeys(): Promise<PasskeySummary[]> {
  const res = await apiClient.get("/auth/passkeys");
  return unwrap<PasskeySummary[]>(res);
}

export async function renamePasskey(id: string, deviceName: string): Promise<PasskeySummary> {
  const res = await apiClient.patch(`/auth/passkeys/${id}`, { device_name: deviceName });
  return unwrap<PasskeySummary>(res);
}

export async function revokePasskey(id: string): Promise<void> {
  await apiClient.delete(`/auth/passkeys/${id}`);
}

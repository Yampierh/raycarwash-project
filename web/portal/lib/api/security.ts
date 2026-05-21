import { authClient } from "./auth-client";
import { apiClient, unwrap } from "./client";

export type Session = {
  family_id: string;
  created_at: string;
  last_used_at: string | null;
  revoked: boolean;
  expires_at: string;
};

export type SecuritySummary = {
  has_password: boolean;
  two_factor_enabled: boolean;
  passkeys_count: number;
  last_password_change: string | null;
  last_login_at: string | null;
  step_up_required: boolean;
  active_sessions_count: number;
  recent_failed_attempts: number;
};

export async function getSecuritySummary(): Promise<SecuritySummary> {
  const res = await apiClient.get("/auth/security");
  return unwrap<SecuritySummary>(res);
}

export async function listSessions(): Promise<{ sessions: Session[]; total: number }> {
  const res = await authClient.get<{ sessions: Session[]; total: number }>("/sessions");
  return res.data;
}

export async function revokeSession(familyId: string): Promise<void> {
  await authClient.delete(`/sessions/${familyId}`);
}

export async function revokeAllSessions(): Promise<void> {
  await authClient.delete("/sessions");
}

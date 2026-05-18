/**
 * frontend/src/services/provider-verification.service.ts
 *
 * Wraps /api/v1/users/me/provider-verification + /me/provider-achievements
 * (Phase 5 chunk Y5).
 */
import { apiClient, unwrap } from "./api";

export interface VerificationStart {
  is_dev_bypass: boolean;
  client_secret: string | null;
  session_id: string | null;
  stripe_publishable_key: string | null;
}

export interface VerificationStatus {
  verification_status:
    | "not_submitted"
    | "pending"
    | "approved"
    | "rejected";
  legal_full_name: string | null;
  verification_submitted_at: string | null;
  verification_reviewed_at: string | null;
  rejection_reason: string | null;
  has_active_session: boolean;
}

export interface Achievement {
  id: string;
  achievement_type: string;
  metadata_: Record<string, unknown> | null;
  awarded_at: string;
}

export async function startVerification(): Promise<VerificationStart> {
  const res = await apiClient.post("/api/v1/users/me/provider-verification");
  return unwrap<VerificationStart>(res);
}

export async function getVerificationStatus(): Promise<VerificationStatus> {
  const res = await apiClient.get("/api/v1/users/me/provider-verification");
  return unwrap<VerificationStatus>(res);
}

export async function listAchievements(): Promise<Achievement[]> {
  const res = await apiClient.get("/api/v1/users/me/provider-achievements");
  return unwrap<Achievement[]>(res);
}

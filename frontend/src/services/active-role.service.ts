/**
 * frontend/src/services/active-role.service.ts
 *
 * Master plan Phase 6 (ADR-003). Wraps PATCH /api/v1/users/me/active-role,
 * which rotates the refresh token alongside the role switch so a stolen
 * refresh can't continue minting access tokens carrying the old role.
 */
import { apiClient, unwrap } from "./api";

export type SwitchableRole = "client" | "detailer" | "mechanic";

export interface ActiveRoleResponse {
  access_token: string;
  refresh_token: string;
  active_role: SwitchableRole;
}

/**
 * Switch the caller's active role. Returns the freshly rotated token
 * pair plus the confirmed active_role. The caller MUST persist both
 * tokens (SecureStore + Zustand) before the next request — the old
 * refresh is revoked atomically as part of this call.
 */
export async function switchActiveRole(
  role: SwitchableRole,
  refreshToken: string,
): Promise<ActiveRoleResponse> {
  const res = await apiClient.patch("/api/v1/users/me/active-role", {
    role,
    refresh_token: refreshToken,
  });
  return unwrap<ActiveRoleResponse>(res);
}

/**
 * frontend/src/services/contact-change.service.ts
 *
 * Wraps /api/v1/users/me/email/* + /phone/* (Phase 3 chunk N).
 *
 * The flow has two halves:
 *   - request*: caller submits the new value + current password, gets a
 *     generic ack with an optional `dev_token` populated only when
 *     RAYCARWASH_ENV=development (so the dev menu can paste the code
 *     without scraping logs).
 *   - confirm/verify: caller proves possession (link token or 6-digit OTP).
 */
import { apiClient, unwrap } from "./api";

export interface ContactChangeAck {
  accepted: boolean;
  message: string;
  dev_token: string | null;
}

export interface ContactChangeSuccess {
  new_value_masked: string;
  sessions_invalidated: boolean;
}

// ─── email ───────────────────────────────────────────────────────────────────

export async function requestEmailChange(
  newEmail: string,
  currentPassword: string,
): Promise<ContactChangeAck> {
  const res = await apiClient.post("/users/me/email/change-request", {
    new_email: newEmail,
    current_password: currentPassword,
  });
  return unwrap<ContactChangeAck>(res);
}

export async function confirmEmailChange(token: string): Promise<ContactChangeSuccess> {
  const res = await apiClient.post("/users/me/email/change-confirm", { token });
  return unwrap<ContactChangeSuccess>(res);
}

// ─── phone ───────────────────────────────────────────────────────────────────

export async function requestPhoneChange(
  newPhone: string,
  currentPassword: string,
): Promise<ContactChangeAck> {
  const res = await apiClient.post("/users/me/phone/change-request", {
    new_phone: newPhone,
    current_password: currentPassword,
  });
  return unwrap<ContactChangeAck>(res);
}

export async function verifyPhoneChange(otp: string): Promise<ContactChangeSuccess> {
  const res = await apiClient.post("/users/me/phone/change-verify", { otp });
  return unwrap<ContactChangeSuccess>(res);
}

/**
 * frontend/src/lib/api-error.ts
 *
 * Typed errors thrown by `apiClient` / `authClient` response interceptors.
 * Mirrors `shared/schemas.py` (Phase 0 ADR-007) so the mobile app, the admin
 * web, and the marketing web all surface the same shapes.
 *
 *   ApiError              — generic 4xx/5xx from /api/v1/* with an error envelope.
 *   StepUpRequiredError   — 401 + code "step_up_required". Carries the list of
 *                           blocks that need re-auth (`requires_step_up`).
 *   isLegacyDetailError() — helper for the small set of legacy endpoints that
 *                           still return `{ detail: ... }`.
 */
export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: { field: string; reason: string }[] | null;
  request_id?: string | null;
}

export interface ApiErrorMeta {
  requires_step_up?: string[];
  skipped_due_to_step_up?: string[];
  [k: string]: unknown;
}

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: { field: string; reason: string }[] | null;
  readonly requestId: string | null;
  readonly meta: ApiErrorMeta | null;

  constructor(payload: ApiErrorPayload, status: number, meta: ApiErrorMeta | null = null) {
    super(payload.message || payload.code);
    this.name = "ApiError";
    this.code = payload.code;
    this.status = status;
    this.details = payload.details ?? null;
    this.requestId = payload.request_id ?? null;
    this.meta = meta;
  }
}

export class StepUpRequiredError extends ApiError {
  readonly requires: string[];

  constructor(payload: ApiErrorPayload, meta: ApiErrorMeta | null = null) {
    super(payload, 401, meta);
    this.name = "StepUpRequiredError";
    this.requires = meta?.requires_step_up ?? [];
  }
}

/**
 * Map an axios error body to one of our typed errors. Returns `null` when the
 * body is not in envelope shape — caller should re-throw the original error.
 */
export function toApiError(body: unknown, status: number): ApiError | null {
  if (!body || typeof body !== "object") return null;
  const obj = body as Record<string, unknown>;
  const errorBlock = obj.error;
  if (!errorBlock || typeof errorBlock !== "object") return null;

  const payload = errorBlock as ApiErrorPayload;
  const meta = (obj.meta as ApiErrorMeta | undefined) ?? null;

  if (payload.code === "step_up_required") {
    return new StepUpRequiredError(payload, meta);
  }
  return new ApiError(payload, status, meta);
}

/**
 * Legacy /auth/* endpoints still return `{ detail: "..." }`. Pre-existing UI
 * code reads that shape directly; this helper centralizes the check so we can
 * grep for it when the legacy endpoints finally migrate.
 */
export function isLegacyDetailError(
  body: unknown,
): body is { detail: string | object } {
  return (
    !!body &&
    typeof body === "object" &&
    "detail" in (body as Record<string, unknown>) &&
    !("error" in (body as Record<string, unknown>))
  );
}

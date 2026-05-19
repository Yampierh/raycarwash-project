/**
 * marketing/lib/api/api-error.ts
 *
 * Typed errors thrown by the marketing/customer web's apiClient for responses
 * from /api/v1/* endpoints following the Phase 0 envelope contract (ADR-007).
 *
 * Mirror of frontend/src/lib/api-error.ts and web/lib/api-error.ts so all
 * three frontend tracks parse server errors the same way. When the shared
 * `@raycarwash/api-client` package is extracted, this file is the source.
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

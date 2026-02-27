/**
 * Lightweight fetch wrapper for API calls.
 *
 * Responsibilities:
 *   - Prepend base URL
 *   - Inject Authorization header when access token exists
 *   - JSON serialisation / deserialisation
 *   - Normalise error responses into a consistent shape
 *   - Notify auth layer on 401 (session expired)
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ApiResponse<T> =
  | { ok: true; data: T; status: number }
  | { ok: false; error: ApiError; status: number };

export interface ApiError {
  message: string;
  fieldErrors?: Record<string, string[]>;
}

// ---------------------------------------------------------------------------
// Token storage (module-scoped, not React state)
// ---------------------------------------------------------------------------

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

// ---------------------------------------------------------------------------
// 401 handler callback
// ---------------------------------------------------------------------------

/** Callback invoked when a 401 response is received (session expired). */
let onUnauthorized: (() => void) | null = null;

/** Register a callback for 401 responses (called by AuthContext). */
export function setOnUnauthorized(cb: (() => void) | null): void {
  onUnauthorized = cb;
}

// ---------------------------------------------------------------------------
// Base URL
// ---------------------------------------------------------------------------

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

// ---------------------------------------------------------------------------
// Core fetch wrapper
// ---------------------------------------------------------------------------

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<ApiResponse<T>> {
  const url = `${BASE_URL}${path}`;

  const headers = new Headers(options.headers);

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  // Auto-set JSON content-type for requests with a non-FormData body.
  // FormData bodies must NOT have Content-Type set manually — the browser
  // must set it (with the multipart boundary) automatically.
  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  try {
    const res = await fetch(url, { ...options, headers });

    // No-content responses
    if (res.status === 204) {
      return { ok: true, data: undefined as T, status: 204 };
    }

    const body = await res.json().catch(() => null);

    if (res.ok) {
      return { ok: true, data: body as T, status: res.status };
    }

    // 401 → session expired, notify auth layer
    if (res.status === 401 && onUnauthorized) {
      onUnauthorized();
    }

    // Normalise error shape
    const error = normaliseError(body, res.status);
    return { ok: false, error, status: res.status };
  } catch {
    return {
      ok: false,
      error: { message: "Network error. Please check your connection." },
      status: 0,
    };
  }
}

// ---------------------------------------------------------------------------
// Convenience methods
// ---------------------------------------------------------------------------

export function apiGet<T>(path: string): Promise<ApiResponse<T>> {
  return apiFetch<T>(path, { method: "GET" });
}

export function apiPost<T>(path: string, body?: unknown): Promise<ApiResponse<T>> {
  return apiFetch<T>(path, {
    method: "POST",
    body: body != null ? JSON.stringify(body) : undefined,
  });
}

export function apiPut<T>(path: string, body?: unknown): Promise<ApiResponse<T>> {
  return apiFetch<T>(path, {
    method: "PUT",
    body: body != null ? JSON.stringify(body) : undefined,
  });
}

export function apiPatch<T>(path: string, body?: unknown): Promise<ApiResponse<T>> {
  return apiFetch<T>(path, {
    method: "PATCH",
    body: body != null ? JSON.stringify(body) : undefined,
  });
}

export function apiDelete<T = void>(path: string): Promise<ApiResponse<T>> {
  return apiFetch<T>(path, { method: "DELETE" });
}

/**
 * POST with multipart/form-data (e.g. file uploads).
 * Do NOT set Content-Type — the browser sets the boundary automatically.
 */
export function apiPostForm<T>(path: string, formData: FormData): Promise<ApiResponse<T>> {
  return apiFetch<T>(path, {
    method: "POST",
    body: formData,
    // headers intentionally omitted so Content-Type is not set
  });
}

/**
 * PATCH with multipart/form-data.
 */
export function apiPatchForm<T>(path: string, formData: FormData): Promise<ApiResponse<T>> {
  return apiFetch<T>(path, {
    method: "PATCH",
    body: formData,
  });
}

// ---------------------------------------------------------------------------
// Error normalisation
// ---------------------------------------------------------------------------

function normaliseError(body: unknown, status: number): ApiError {
  if (body && typeof body === "object") {
    const obj = body as Record<string, unknown>;

    // DRF standard: { detail: "..." }
    if (typeof obj.detail === "string") {
      return { message: obj.detail };
    }

    // DRF validation: { field: ["error1", "error2"], ... }
    // Also captures non_field_errors as a top-level message
    const fieldErrors: Record<string, string[]> = {};
    let hasFields = false;
    for (const [key, val] of Object.entries(obj)) {
      if (Array.isArray(val) && val.every((v) => typeof v === "string")) {
        fieldErrors[key] = val as string[];
        hasFields = true;
      }
    }
    if (hasFields) {
      // Use non_field_errors as the main message if present
      const nonField = fieldErrors["non_field_errors"];
      const firstFieldMessage = Object.values(fieldErrors)
        .find((messages) => messages.length > 0)?.[0];
      const message = nonField?.[0] ?? firstFieldMessage ?? "Validation error";
      return {
        message,
        fieldErrors,
      };
    }

    // DRF detail as array: { detail: ["err1", "err2"] }
    if (Array.isArray(obj.detail) && obj.detail.length > 0) {
      return { message: String(obj.detail[0]) };
    }

    // Custom backend error shape: { message: "..." }
    if (typeof obj.message === "string") {
      return { message: obj.message };
    }
  }

  return { message: `Request failed (HTTP ${status})` };
}

/**
 * API error helpers — extract human-readable messages from Axios errors.
 *
 * Error handling strategy:
 *  - 400 → field-level or non-field validation errors → shown inline
 *  - 401 → interceptor handles refresh; if that fails → redirect to /login
 *  - 403 → "Forbidden" banner or ProtectedRoute guards it entirely
 *  - 404 → "Not found" message
 *  - 5xx → generic "Something went wrong" toast
 */
import type { AxiosError } from 'axios';
import type { ApiError } from '@/types/api.types';

/** True if this AxiosError carries our backend's error shape. */
export function isApiError(
  error: unknown,
): error is AxiosError<ApiError> {
  return (
    typeof error === 'object' &&
    error !== null &&
    'isAxiosError' in error &&
    (error as AxiosError).isAxiosError === true
  );
}

/**
 * Extract the most useful single-string message from any error.
 * Use this for toasts / snackbars.
 */
export function extractErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    const data = error.response?.data;
    if (data?.detail) return data.detail;
    if (data?.non_field_errors?.length) return data.non_field_errors.join(' ');
    if (data?.field_errors) {
      const first = Object.entries(data.field_errors)[0];
      if (first) return `${first[0]}: ${first[1].join(', ')}`;
    }
    // Fallback to status text
    return error.response?.statusText ?? 'Request failed';
  }
  if (error instanceof Error) return error.message;
  return 'An unexpected error occurred';
}

/**
 * Extract per-field error strings for form handling.
 */
export function extractFieldErrors(
  error: unknown,
): Record<string, string> | null {
  if (!isApiError(error)) return null;
  const fe = error.response?.data?.field_errors;
  if (!fe) return null;
  const result: Record<string, string> = {};
  for (const [field, messages] of Object.entries(fe)) {
    result[field] = messages.join(', ');
  }
  return result;
}

/** Get the HTTP status code (or 0 if unavailable). */
export function getErrorStatus(error: unknown): number {
  if (isApiError(error)) return error.response?.status ?? 0;
  return 0;
}

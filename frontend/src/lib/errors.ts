/**
 * Error extraction utilities.
 *
 * Helpers for working with the normalised `ApiError` shape
 * returned by `apiFetch`. Designed to be used in form handlers,
 * toast notifications, and error-state components.
 */

import type { ApiError } from "../api/client";

// ---------------------------------------------------------------------------
// Extract helpers
// ---------------------------------------------------------------------------

/**
 * Get the first validation error string for a specific field.
 * Returns `undefined` if none exists.
 */
export function getFieldError(
  error: ApiError | undefined | null,
  field: string,
): string | undefined {
  return error?.fieldErrors?.[field]?.[0];
}

/**
 * Get all validation errors for a specific field.
 * Returns an empty array if none exist.
 */
export function getFieldErrors(
  error: ApiError | undefined | null,
  field: string,
): string[] {
  return error?.fieldErrors?.[field] ?? [];
}

/**
 * Check whether the error has any field-level validation errors.
 */
export function hasFieldErrors(error: ApiError | undefined | null): boolean {
  return (
    error?.fieldErrors != null &&
    Object.keys(error.fieldErrors).length > 0
  );
}

/**
 * Get the top-level error message (non-field-specific).
 * Falls back to a generic message when nothing is available.
 */
export function getErrorMessage(
  error: ApiError | undefined | null,
  fallback = "An unexpected error occurred.",
): string {
  return error?.message ?? fallback;
}

/**
 * Collect all errors (field + non-field) into a flat string array.
 * Useful for rendering a summary list of problems.
 */
export function flattenErrors(error: ApiError | undefined | null): string[] {
  if (!error) return [];

  const msgs: string[] = [];

  if (error.message && error.message !== "Validation error") {
    msgs.push(error.message);
  }

  if (error.fieldErrors) {
    for (const [field, fieldMsgs] of Object.entries(error.fieldErrors)) {
      if (field === "non_field_errors") {
        msgs.push(...fieldMsgs);
      } else {
        for (const msg of fieldMsgs) {
          msgs.push(`${field}: ${msg}`);
        }
      }
    }
  }

  return msgs.length > 0 ? msgs : [error.message ?? "Unknown error"];
}

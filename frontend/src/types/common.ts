/**
 * Shared utility types and base interfaces used across all domain types.
 */

/** ISO 8601 date-time string (e.g. "2025-01-15T10:30:00Z") */
export type ISODateTime = string;

/** Paginated response wrapper matching DRF's PageNumberPagination */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Base fields present on all TimeStampedModel entities */
export interface TimeStamped {
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

/** API error response shape from DRF */
export interface ApiError {
  detail?: string;
  [field: string]: unknown;
}

/** Generic ID reference (when the API returns just an ID, not nested) */
export type EntityId = number;

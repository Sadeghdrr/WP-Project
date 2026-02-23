/**
 * Shared API response / request shapes used across all services.
 */

/* ── Generic pagination envelope (DRF default) ──────────────────── */

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/* ── Standard error shapes ───────────────────────────────────────── */

export interface FieldErrors {
  [field: string]: string[];
}

export interface ApiError {
  detail?: string;
  code?: string;
  field_errors?: FieldErrors;
  non_field_errors?: string[];
}

/* ── Auth tokens (SimpleJWT) ─────────────────────────────────────── */

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface LoginRequest {
  identifier: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  email: string;
  first_name: string;
  last_name: string;
  national_id: string;
  phone_number: string;
}

export interface TokenRefreshRequest {
  refresh: string;
}

export interface TokenRefreshResponse {
  access: string;
}

/* ── Query-string helpers ────────────────────────────────────────── */

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

export interface OrderingParams {
  ordering?: string;
}

export interface SearchParams {
  search?: string;
}

export type ListParams = PaginationParams & OrderingParams & SearchParams;

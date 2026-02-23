/**
 * Shared API response types — mirror backend DRF response shapes.
 * Error format matches DRF ValidationError and domain exception handler.
 */

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * DRF error response shape.
 * - detail: single error message (e.g. "Invalid credentials.", 409 Conflict)
 * - field_name: array of validation errors for that field
 */
export interface ApiError {
  detail?: string;
  [field: string]: string[] | string | undefined;
}

/**
 * JWT tokens from login response.
 * Backend: CustomTokenObtainPairSerializer returns access + refresh.
 */
export interface AuthTokens {
  access: string;
  refresh: string;
}

/**
 * Login request — backend LoginRequestSerializer / CustomTokenObtainPairSerializer.
 * identifier: username | national_id | phone_number | email
 */
export interface LoginRequest {
  identifier: string;
  password: string;
}

/**
 * Register request — backend RegisterRequestSerializer.
 * Fields must match exactly.
 */
export interface RegisterRequest {
  username: string;
  password: string;
  password_confirm: string;
  email: string;
  phone_number: string;
  first_name: string;
  last_name: string;
  national_id: string;
}

/**
 * Login response — backend TokenResponseSerializer + UserDetailSerializer.
 */
export interface LoginResponse {
  access: string;
  refresh: string;
  user: {
    id: number;
    username: string;
    email: string;
    national_id: string;
    phone_number: string;
    first_name: string;
    last_name: string;
    is_active: boolean;
    date_joined: string;
    role: number;
    role_detail: { id: number; name: string; description: string; hierarchy_level: number };
    permissions: string[];
  };
}

/**
 * Token refresh request — SimpleJWT TokenRefreshView.
 * ROTATE_REFRESH_TOKENS=True → response includes new refresh.
 */
export interface TokenRefreshRequest {
  refresh: string;
}

/**
 * Token refresh response — SimpleJWT with ROTATE_REFRESH_TOKENS.
 */
export interface TokenRefreshResponse {
  access: string;
  refresh?: string;
}

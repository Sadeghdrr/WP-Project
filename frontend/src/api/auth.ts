/**
 * Auth-related API calls.
 *
 * Each function wraps an API client call and returns the normalized
 * ApiResponse. Token management (storing, clearing) is NOT done here —
 * that's the AuthContext's job. These are pure data-fetching functions.
 */

import { apiPost, apiGet } from "./client";
import type { ApiResponse } from "./client";
import { API } from "./endpoints";
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  TokenRefreshResponse,
  User,
} from "../types/auth";

/** POST /accounts/auth/login/ */
export function loginApi(
  payload: LoginRequest,
): Promise<ApiResponse<LoginResponse>> {
  return apiPost<LoginResponse>(API.LOGIN, payload);
}

/** POST /accounts/auth/register/ (returns user only, no tokens) */
export function registerApi(
  payload: RegisterRequest,
): Promise<ApiResponse<RegisterResponse>> {
  return apiPost<RegisterResponse>(API.REGISTER, payload);
}

/** POST /accounts/auth/token/refresh/ */
export function refreshTokenApi(
  refresh: string,
): Promise<ApiResponse<TokenRefreshResponse>> {
  return apiPost<TokenRefreshResponse>(API.TOKEN_REFRESH, { refresh });
}

/** GET /accounts/me/ */
export function fetchMeApi(): Promise<ApiResponse<User>> {
  return apiGet<User>(API.ME);
}

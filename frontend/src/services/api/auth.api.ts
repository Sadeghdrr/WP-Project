/**
 * Auth API — mirrors backend accounts app endpoints.
 * Base path: /api/accounts/
 *
 * Endpoints (from backend accounts/urls.py):
 * - POST /auth/register/
 * - POST /auth/login/
 * - POST /auth/token/refresh/
 * - GET  /me/
 */

import axios from 'axios';
import { apiClient } from './api.client';
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  TokenRefreshRequest,
  TokenRefreshResponse,
} from '../../types/api.types';
import type { User } from '../../types/user.types';
import { API_BASE_URL, ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from '../../config/constants';

const ACCOUNTS_BASE = `${API_BASE_URL}/accounts`;

/**
 * Public endpoints (no auth) — use raw axios to avoid interceptor loops.
 */
const publicClient = axios.create({
  baseURL: ACCOUNTS_BASE,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * POST /api/accounts/auth/register/
 * Request: RegisterRequestSerializer
 * Response: UserDetailSerializer (201)
 * Error: 409 Conflict — { detail: "The following field(s) already exist: ..." }
 */
export async function register(data: RegisterRequest): Promise<User> {
  const { data: user } = await publicClient.post<User>(`/auth/register/`, data);
  return user;
}

/**
 * POST /api/accounts/auth/login/
 * Request: { identifier, password }
 * Response: { access, refresh, user } (200)
 * Error: 400 — { detail: "Invalid credentials." } or { detail: "User account is disabled." }
 */
export async function login(data: LoginRequest): Promise<LoginResponse> {
  const { data: response } = await publicClient.post<LoginResponse>(`/auth/login/`, data);
  return response;
}

/**
 * POST /api/accounts/auth/token/refresh/
 * Request: { refresh }
 * Response: { access, refresh? } — refresh included when ROTATE_REFRESH_TOKENS=True
 */
export async function refreshToken(refresh: string): Promise<TokenRefreshResponse> {
  const { data } = await publicClient.post<TokenRefreshResponse>(
    `/auth/token/refresh/`,
    { refresh } satisfies TokenRefreshRequest
  );
  return data;
}

/**
 * GET /api/accounts/me/
 * Requires: Bearer access token
 * Response: UserDetailSerializer
 */
export async function getMe(): Promise<User> {
  const { data } = await apiClient.get<User>(`/accounts/me/`);
  return data;
}

/**
 * Persist tokens to localStorage after login.
 */
export function persistTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, access);
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
}

/**
 * Clear tokens from localStorage.
 */
export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

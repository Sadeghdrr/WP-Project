/**
 * Pre-configured Axios instance with JWT interceptors.
 *
 * Request  → attaches the access token from localStorage.
 * Response → on 401 attempts a silent token refresh;
 *            if refresh also fails, clears tokens and redirects to /login.
 */
import axios, {
  type AxiosError,
  type InternalAxiosRequestConfig,
} from 'axios';
import { API_BASE_URL } from '@/config/constants';
import { tokenStorage } from '@/utils/storage';

/* ── Instance ────────────────────────────────────────────────────── */

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
});

/* ── Request interceptor ─────────────────────────────────────────── */

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.getAccessToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/* ── Response interceptor (silent refresh) ───────────────────────── */

let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refresh = tokenStorage.getRefreshToken();
  if (!refresh) throw new Error('No refresh token');

  const { data } = await axios.post<{ access: string }>(
    `${API_BASE_URL}/accounts/auth/token/refresh/`,
    { refresh },
  );
  tokenStorage.setAccessToken(data.access);
  return data.access;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config;
    if (!original) return Promise.reject(error);

    // Only try refresh on 401, and not on the refresh endpoint itself
    const isRefreshUrl = original.url?.includes('/token/refresh/');
    if (error.response?.status === 401 && !isRefreshUrl) {
      try {
        // Deduplicate concurrent refresh attempts
        if (!refreshPromise) {
          refreshPromise = refreshAccessToken().finally(() => {
            refreshPromise = null;
          });
        }
        const newToken = await refreshPromise;
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      } catch {
        // Refresh failed → force logout
        tokenStorage.clearTokens();
        window.location.href = '/login';
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  },
);

export default api;

/**
 * AuthContext — React context that manages the complete auth lifecycle.
 *
 * Responsibilities:
 *   - Bootstrap session on app load (refresh token → access token → /me)
 *   - Provide login / register / logout actions
 *   - Expose current user + auth state to the component tree
 *   - Handle token refresh transparently
 *   - Provide permission set for fast access checks
 *
 * Provider ordering in App.tsx:
 *   QueryClientProvider → AuthProvider → ErrorBoundary → Router
 */

import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";
import { setAccessToken } from "../api/client";
import { setOnUnauthorized } from "../api/client";
import { loginApi, registerApi, refreshTokenApi, fetchMeApi } from "../api/auth";
import {
  getStoredRefreshToken,
  storeRefreshToken,
  clearStoredRefreshToken,
} from "./tokenStorage";
import { buildPermissionSet } from "./can";
import type { User, LoginRequest, RegisterRequest } from "../types/auth";
import type { ApiError } from "../api/client";

// ---------------------------------------------------------------------------
// Context shape
// ---------------------------------------------------------------------------

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthContextValue {
  /** Current auth status */
  status: AuthStatus;
  /** Authenticated user (null when unauthenticated or loading) */
  user: User | null;
  /** Pre-built permission set for O(1) checks */
  permissionSet: ReadonlySet<string>;
  /** Login with identifier + password */
  login: (req: LoginRequest) => Promise<{ ok: true } | { ok: false; error: ApiError }>;
  /** Register then auto-login */
  register: (req: RegisterRequest) => Promise<{ ok: true } | { ok: false; error: ApiError }>;
  /** Clear session and redirect to login */
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<User | null>(null);

  // ── Derived values ──────────────────────────────────────────────────
  const permissionSet = useMemo(
    () => buildPermissionSet(user?.permissions ?? []),
    [user],
  );


  // ── Internal helpers ────────────────────────────────────────────────

  /** Set tokens in memory + storage, then fetch current user. */
  const establishSession = useCallback(
    async (access: string, refresh: string): Promise<boolean> => {
      setAccessToken(access);
      storeRefreshToken(refresh);

      const meResult = await fetchMeApi();
      if (meResult.ok) {
        setUser(meResult.data);
        setStatus("authenticated");
        return true;
      }

      // /me failed — clear everything
      setAccessToken(null);
      clearStoredRefreshToken();
      setUser(null);
      setStatus("unauthenticated");
      return false;
    },
    [],
  );

  /** Try to refresh the access token using the stored refresh token. */
  const tryRefresh = useCallback(async (): Promise<boolean> => {
    const refresh = getStoredRefreshToken();
    if (!refresh) return false;

    const result = await refreshTokenApi(refresh);
    if (!result.ok) {
      clearStoredRefreshToken();
      return false;
    }

    const newAccess = result.data.access;
    // If backend rotates refresh tokens, use the new one
    const newRefresh = (result.data as Record<string, unknown>).refresh;
    const refreshToStore = typeof newRefresh === "string" ? newRefresh : refresh;

    setAccessToken(newAccess);
    storeRefreshToken(refreshToStore);
    return true;
  }, []);

  // ── Bootstrap on mount ──────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;

    // Register 401 handler — when any API call gets 401, clear session
    setOnUnauthorized(() => {
      if (!cancelled) {
        setAccessToken(null);
        clearStoredRefreshToken();
        setUser(null);
        setStatus("unauthenticated");
      }
    });

    async function bootstrap() {
      const refreshed = await tryRefresh();
      if (cancelled) return;

      if (refreshed) {
        const meResult = await fetchMeApi();
        if (cancelled) return;

        if (meResult.ok) {
          setUser(meResult.data);
          setStatus("authenticated");
          return;
        }
      }

      // No valid session
      setAccessToken(null);
      clearStoredRefreshToken();
      setStatus("unauthenticated");
    }

    bootstrap();

    return () => {
      cancelled = true;
      setOnUnauthorized(null);
    };
  }, [tryRefresh]);

  // ── Actions ─────────────────────────────────────────────────────────

  const login = useCallback(
    async (req: LoginRequest) => {
      const result = await loginApi(req);

      if (!result.ok) {
        return { ok: false as const, error: result.error };
      }

      const { access, refresh, user: userData } = result.data;
      setAccessToken(access);
      storeRefreshToken(refresh);
      setUser(userData);
      setStatus("authenticated");

      return { ok: true as const };
    },
    [],
  );

  const register = useCallback(
    async (req: RegisterRequest) => {
      const regResult = await registerApi(req);

      if (!regResult.ok) {
        return { ok: false as const, error: regResult.error };
      }

      // Backend does NOT return tokens on register → auto-login
      const loginResult = await loginApi({
        identifier: req.username,
        password: req.password,
      });

      if (!loginResult.ok) {
        // Registration succeeded but auto-login failed (e.g. account inactive)
        return { ok: false as const, error: loginResult.error };
      }

      const { access, refresh, user: userData } = loginResult.data;
      setAccessToken(access);
      storeRefreshToken(refresh);
      setUser(userData);
      setStatus("authenticated");

      return { ok: true as const };
    },
    [],
  );

  const logout = useCallback(() => {
    setAccessToken(null);
    clearStoredRefreshToken();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  // ── Context value ───────────────────────────────────────────────────
  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      permissionSet,
      login,
      register,
      logout,
    }),
    [status, user, permissionSet, login, register, logout],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

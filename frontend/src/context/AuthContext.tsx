/**
 * AuthContext — JWT authentication & current-user state.
 *
 * Responsibilities:
 *  1. Persist access/refresh tokens in localStorage.
 *  2. On mount, if tokens exist, fetch the current user from /me/.
 *  3. Expose login / logout helpers.
 *  4. Expose the user object and derived permission list.
 *  5. Provide isAuthenticated / isLoading flags for guard components.
 */
import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { authApi, type LoginResponse } from '@/services/api/auth.api';
import { tokenStorage } from '@/utils/storage';
import type { User } from '@/types/user.types';
import type { LoginRequest, RegisterRequest } from '@/types/api.types';
import { queryClient } from '@/config/queryClient';

/* ── Context value shape ─────────────────────────────────────────── */

export interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  /** All permission codenames the current user has (via their role). */
  permissions: string[];
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  /** Re-fetch /me/ — useful after profile update. */
  refreshUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined,
);

/* ── Provider ────────────────────────────────────────────────────── */

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true); // true while hydrating

  /* ── Hydrate session on mount ──────────────────────────────────── */
  const fetchUser = useCallback(async () => {
    if (!tokenStorage.hasTokens()) {
      setIsLoading(false);
      return;
    }
    try {
      const me = await authApi.getMe();
      setUser(me);
    } catch {
      // Token expired/invalid — clean up silently
      tokenStorage.clearTokens();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  /* ── Login ─────────────────────────────────────────────────────── */
  const login = useCallback(async (credentials: LoginRequest) => {
    const data: LoginResponse = await authApi.login(credentials);
    tokenStorage.setTokens(data.access, data.refresh);
    setUser(data.user);
  }, []);

  /* ── Register ──────────────────────────────────────────────────── */
  const register = useCallback(async (data: RegisterRequest) => {
    await authApi.register(data);
    // After registration the user needs to log in.
  }, []);

  /* ── Logout ────────────────────────────────────────────────────── */
  const logout = useCallback(() => {
    tokenStorage.clearTokens();
    setUser(null);
    queryClient.clear(); // wipe all cached server state
  }, []);

  /* ── Refresh user ──────────────────────────────────────────────── */
  const refreshUser = useCallback(async () => {
    const me = await authApi.getMe();
    setUser(me);
  }, []);

  /* ── Derived ───────────────────────────────────────────────────── */
  const permissions = useMemo(
    () => user?.permissions ?? [],
    [user?.permissions],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: !!user,
      isLoading,
      permissions,
      login,
      register,
      logout,
      refreshUser,
    }),
    [user, isLoading, permissions, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

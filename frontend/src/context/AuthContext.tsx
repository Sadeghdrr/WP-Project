/**
 * AuthContext — JWT token management, user state, login/logout.
 * Persists tokens in localStorage, hydrates user from /me/ on mount.
 * Scalable for RBAC (permissions from user.permissions).
 */

import React, { createContext, useCallback, useEffect, useState } from 'react';
import type { User } from '../types/user.types';
import type { LoginRequest } from '../types/api.types';
import {
  login as apiLogin,
  getMe,
  persistTokens,
  clearTokens,
} from '../services/api/auth.api';
import { ACCESS_TOKEN_KEY } from '../config/constants';

export interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (data: LoginRequest) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadUser = useCallback(async () => {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (!token) {
      setIsLoading(false);
      return;
    }
    try {
      const profile = await getMe();
      setUser(profile);
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = useCallback(
    async (data: LoginRequest) => {
      const response = await apiLogin(data);
      persistTokens(response.access, response.refresh);
      setUser(response.user);
    },
    []
  );

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  const value: AuthContextValue = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

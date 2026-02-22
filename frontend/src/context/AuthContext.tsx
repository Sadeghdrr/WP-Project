import React from 'react';

// TODO: Implement AuthContext with:
// - JWT access/refresh token management (login, logout, refresh)
// - Current user state (User object from /api/accounts/me/)
// - User permissions list (from role.permissions)
// - isAuthenticated, isLoading flags
// - Persist tokens in localStorage, hydrate on mount

interface AuthContextValue {
  // TODO: Define context value shape
}

export const AuthContext = React.createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // TODO: Implement provider with token storage, refresh logic, user fetch
  return <AuthContext.Provider value={undefined as unknown as AuthContextValue}>{children}</AuthContext.Provider>;
};

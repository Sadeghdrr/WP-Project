/**
 * ProtectedRoute — guards routes that require authentication.
 * Redirects to /login if not authenticated.
 * Scalable for RBAC: requiredPermissions can be added in a future phase.
 */

import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

export interface ProtectedRouteProps {
  children?: React.ReactNode;
  /** Optional: required permissions for RBAC (future phase) */
  requiredPermissions?: string[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredPermissions = [],
}) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-900">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Future: check requiredPermissions against user.permissions
  // if (requiredPermissions.length > 0 && !hasAllPermissions(requiredPermissions)) {
  //   return <Navigate to="/403" replace />;
  // }

  return <>{children ?? <Outlet />}</>;
};

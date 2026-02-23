/**
 * ProtectedRoute — wraps any route that requires authentication and
 * optionally specific permissions.
 *
 * Usage inside the router:
 *   <Route element={<ProtectedRoute />}>          — auth only
 *   <Route element={<ProtectedRoute requiredPermissions={['view_case']} />}>
 *
 * Behaviour:
 *   • Not authenticated → redirect to /login (preserving intended URL)
 *   • Authenticated but missing permissions → 403 Alert
 *   • Loading → fullscreen Loader spinner
 */
import type { ReactNode } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { usePermissions } from '@/hooks/usePermissions';
import { Loader } from '@/components/ui/Loader';
import { Alert } from '@/components/ui/Alert';

interface ProtectedRouteProps {
  /** If set, user must have at least ONE of these permission codenames. */
  requiredPermissions?: string[];
  /** If true, user must have ALL of requiredPermissions instead of any. */
  requireAll?: boolean;
  children?: ReactNode;
}

export const ProtectedRoute = ({
  requiredPermissions,
  requireAll = false,
  children,
}: ProtectedRouteProps) => {
  const { isAuthenticated, isLoading } = useAuth();
  const { hasAnyPermission, hasAllPermissions } = usePermissions();
  const location = useLocation();

  if (isLoading) {
    return <Loader fullScreen label="Authenticating…" />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredPermissions && requiredPermissions.length > 0) {
    const allowed = requireAll
      ? hasAllPermissions(requiredPermissions)
      : hasAnyPermission(requiredPermissions);

    if (!allowed) {
      return (
        <div style={{ padding: '3rem', maxWidth: '480px', margin: '4rem auto' }}>
          <Alert type="error" title="403 — Forbidden">
            You do not have permission to access this page.
          </Alert>
        </div>
      );
    }
  }

  return children ? <>{children}</> : <Outlet />;
};

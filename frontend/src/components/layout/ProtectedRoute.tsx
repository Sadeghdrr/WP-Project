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
 *   • Authenticated but missing permissions → 403 placeholder
 *   • Loading → null (or a global spinner if desired)
 */
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { usePermissions } from '@/hooks/usePermissions';

interface ProtectedRouteProps {
  /** If set, user must have at least ONE of these permission codenames. */
  requiredPermissions?: string[];
  /** If true, user must have ALL of requiredPermissions instead of any. */
  requireAll?: boolean;
  children?: React.ReactNode;
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
    // While hydrating the session, render nothing (or a spinner).
    return null;
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
        <div style={{ padding: '2rem', textAlign: 'center' }}>
          <h1>403 — Forbidden</h1>
          <p>You do not have permission to access this page.</p>
        </div>
      );
    }
  }

  return children ? <>{children}</> : <Outlet />;
};

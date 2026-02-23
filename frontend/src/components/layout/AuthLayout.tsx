/**
 * AuthLayout — minimal centered layout for Login / Register pages.
 * Redirects to /dashboard if the user is already logged in.
 */
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

export const AuthLayout = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return null;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  return (
    <div className="auth-layout">
      <div className="auth-layout__card">
        <Outlet />
      </div>
    </div>
  );
};

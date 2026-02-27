/**
 * Route guard components for auth-based access control.
 *
 * - <ProtectedRoute>  — requires authentication, redirects to /login if not
 * - <GuestRoute>      — only for unauthenticated users, redirects to /dashboard if logged in
 *
 * These wrap route elements in the router definition.
 * Permission-based guards (hierarchy, specific permissions) will be added
 * in a later step on top of this foundation.
 */

import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../../auth/useAuth";

/**
 * Wraps authenticated routes. Redirects to / when unauthenticated.
 * While auth is bootstrapping (status === "loading"), shows a loading state
 * to prevent flash-of-login-page.
 */
export function ProtectedRoute() {
  const { status } = useAuth();

  if (status === "loading") {
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        Loading…
      </div>
    );
  }

  if (status === "unauthenticated") {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}

/**
 * Wraps guest-only routes (login, register).
 * Redirects to /dashboard when already authenticated.
 */
export function GuestRoute() {
  const { status } = useAuth();

  if (status === "loading") {
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        Loading…
      </div>
    );
  }

  if (status === "authenticated") {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}

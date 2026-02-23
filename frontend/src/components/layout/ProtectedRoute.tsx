import React from 'react';

// TODO: ProtectedRoute wrapper component
// - Check if user is authenticated (from AuthContext)
// - Optionally check required permissions (usePermissions)
// - Redirect to /login if not authenticated
// - Show 403 Forbidden if authenticated but lacks permissions
// - Render children / <Outlet /> if authorized

export const ProtectedRoute: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  // TODO: Implement auth + permission checks
  return <>{children}</>;
};

/**
 * Hook for checking RBAC permissions on the UI.
 * Reads permissions from AuthContext (user's role permissions).
 */

import { useAuth } from './useAuth';

export function usePermissions() {
  const { user } = useAuth();

  const permissions = user?.permissions ?? [];

  function hasPermission(codename: string): boolean {
    const fullCodename = codename.includes('.') ? codename : `cases.${codename}`;
    return permissions.includes(fullCodename);
  }

  function hasAnyPermission(codenames: string[]): boolean {
    return codenames.some((c) => hasPermission(c));
  }

  function hasAllPermissions(codenames: string[]): boolean {
    return codenames.every((c) => hasPermission(c));
  }

  return {
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    permissions,
  };
}

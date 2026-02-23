/**
 * usePermissions — RBAC permission helpers derived from the current user's
 * role permissions (stored in AuthContext).
 *
 * Permission codenames are dynamic strings fetched from the backend —
 * no role names are hardcoded. The UI only checks whether the current
 * user's permission set includes the required codename(s).
 */
import { useCallback, useMemo } from 'react';
import { useAuth } from './useAuth';

export function usePermissions() {
  const { permissions, user } = useAuth();

  const permSet = useMemo(() => new Set(permissions), [permissions]);

  /** True if the user has the given permission codename */
  const hasPermission = useCallback(
    (codename: string) => permSet.has(codename),
    [permSet],
  );

  /** True if the user has at least one of the listed permissions */
  const hasAnyPermission = useCallback(
    (codenames: string[]) => codenames.some((c) => permSet.has(c)),
    [permSet],
  );

  /** True if the user has ALL of the listed permissions */
  const hasAllPermissions = useCallback(
    (codenames: string[]) => codenames.every((c) => permSet.has(c)),
    [permSet],
  );

  /** Check hierarchy level (e.g. "user must be at least level 5") */
  const hasMinHierarchy = useCallback(
    (minLevel: number) => (user?.role?.hierarchy_level ?? 0) >= minLevel,
    [user?.role?.hierarchy_level],
  );

  return {
    permissions,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    hasMinHierarchy,
    /** The name of the user's current role (if any) */
    roleName: user?.role?.name ?? null,
  };
}

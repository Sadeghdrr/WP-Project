/**
 * RoleGuard — component-level RBAC guard supporting permissions AND hierarchy.
 *
 * Unlike PermissionGate (permissions only), RoleGuard also supports
 * minimum hierarchy level checks via the `minHierarchy` prop.
 *
 * Usage:
 *   <RoleGuard permissions={['can_approve_case']} minHierarchy={3}>
 *     <ApproveButton />
 *   </RoleGuard>
 */
import type { ReactNode } from 'react';
import { usePermissions } from '@/hooks/usePermissions';

export interface RoleGuardProps {
  /** Permission codenames required to render children */
  permissions?: string[];
  /** When true, ALL permissions are needed; otherwise ANY suffices */
  requireAll?: boolean;
  /** Minimum hierarchy level (role rank) required */
  minHierarchy?: number;
  /** Rendered when the user is unauthorized */
  fallback?: ReactNode;
  children: ReactNode;
}

export function RoleGuard({
  permissions = [],
  requireAll = false,
  minHierarchy,
  fallback = null,
  children,
}: RoleGuardProps) {
  const { hasAnyPermission, hasAllPermissions, hasMinHierarchy } =
    usePermissions();

  let allowed = true;

  if (permissions.length > 0) {
    allowed = requireAll
      ? hasAllPermissions(permissions)
      : hasAnyPermission(permissions);
  }

  if (allowed && minHierarchy !== undefined) {
    allowed = hasMinHierarchy(minHierarchy);
  }

  return <>{allowed ? children : fallback}</>;
}

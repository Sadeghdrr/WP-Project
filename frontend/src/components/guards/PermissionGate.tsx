/**
 * PermissionGate — conditionally renders children based on RBAC permissions.
 *
 * Unlike ProtectedRoute (which guards routes), PermissionGate is used
 * *within* a page to show/hide UI sections.
 *
 * Usage:
 *   <PermissionGate permissions={['can_verify_evidence']}>
 *     <VerifyButton />
 *   </PermissionGate>
 *
 *   <PermissionGate permissions={['can_approve_case']} fallback={<Locked />}>
 *     <ApproveSection />
 *   </PermissionGate>
 */
import type { ReactNode } from 'react';
import { usePermissions } from '@/hooks/usePermissions';

export interface PermissionGateProps {
  /** Permission codenames to check. */
  permissions: string[];
  /** If true, ALL permissions must be present (default: any). */
  requireAll?: boolean;
  /** Rendered when the check fails (default: nothing). */
  fallback?: ReactNode;
  children: ReactNode;
}

export const PermissionGate = ({
  permissions,
  requireAll = false,
  fallback = null,
  children,
}: PermissionGateProps) => {
  const { hasAnyPermission, hasAllPermissions } = usePermissions();

  const allowed =
    permissions.length === 0 ||
    (requireAll
      ? hasAllPermissions(permissions)
      : hasAnyPermission(permissions));

  return <>{allowed ? children : fallback}</>;
};

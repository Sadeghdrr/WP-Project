/**
 * useDashboardModules — the Modular Dashboard Engine hook.
 *
 * Consumes the centralised module registry and filters it against
 * the current user's permissions. Returns only the modules the user
 * is authorised to see.
 *
 * Features:
 *  - Dynamic: evaluates permissions at render time
 *  - Multi-role safe: works with any combination of permissions
 *  - No hardcoded role names: purely permission-codename driven
 *  - Runtime extensible: includes modules added via registerDashboardModule()
 *  - Memoised: re-computes only when permissions change
 *
 * Usage:
 *   const { visibleModules, getStatValue } = useDashboardModules(stats);
 */
import { useMemo } from 'react';
import { usePermissions } from '@/hooks/usePermissions';
import { getAllDashboardModules } from '@/config/dashboardModules';
import type { DashboardModuleDefinition } from '@/config/dashboardModules';
import type { DashboardStats } from '@/types/notification.types';

export interface UseDashboardModulesResult {
  /** Modules the current user is authorised to see. */
  visibleModules: DashboardModuleDefinition[];
  /** Convenience: extract the stat value for a module, or '—'. */
  getStatValue: (module: DashboardModuleDefinition) => string | number;
  /** Sidebar-eligible items, ordered by sidebarOrder. */
  sidebarItems: DashboardModuleDefinition[];
}

export function useDashboardModules(
  stats?: DashboardStats | null,
): UseDashboardModulesResult {
  const { hasAnyPermission, hasAllPermissions } = usePermissions();

  const allModules = getAllDashboardModules();

  const visibleModules = useMemo(() => {
    return allModules.filter((mod) => {
      if (mod.permissions.length === 0) return true;
      return mod.requireAll
        ? hasAllPermissions(mod.permissions)
        : hasAnyPermission(mod.permissions);
    });
  }, [allModules, hasAnyPermission, hasAllPermissions]);

  const sidebarItems = useMemo(() => {
    return visibleModules
      .filter((mod) => mod.showInSidebar !== false)
      .sort((a, b) => (a.sidebarOrder ?? 999) - (b.sidebarOrder ?? 999));
  }, [visibleModules]);

  const getStatValue = (module: DashboardModuleDefinition): string | number => {
    if (!stats || !module.statAccessor) return '—';
    return module.statAccessor(stats) ?? '—';
  };

  return { visibleModules, getStatValue, sidebarItems };
}

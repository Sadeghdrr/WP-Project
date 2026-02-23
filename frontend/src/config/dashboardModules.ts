/**
 * Centralised Dashboard Module Registry.
 *
 * Every dashboard module is registered here with its metadata.
 * The system evaluates visibility at runtime based on the user's
 * permission set — no role names are ever referenced.
 *
 * To add a new module:
 *   1. Append an entry to DASHBOARD_MODULES
 *   2. Ensure the required permission codename exists in the backend
 *   3. That's it — the dashboard, sidebar, and routing layer pick it up
 *
 * To support a new dynamic role:
 *   - Create the role + assign permissions in the admin panel
 *   - No code change needed — the registry is already permission-driven
 *
 * The registry is intentionally a plain array (not a Map or object)
 * so ordering controls the render order on the dashboard.
 */
import type { DashboardStats } from '@/types/notification.types';

/* ── Module definition ───────────────────────────────────────────── */

export interface DashboardModuleDefinition {
  /** Unique identifier for the module. */
  id: string;
  /** Display title on the dashboard card. */
  title: string;
  /** Short description shown below the value. */
  description: string;
  /** Route path within the dashboard (relative to root). */
  route: string;
  /** Permission codenames required to view this module. Empty = visible to all authenticated users. */
  permissions: string[];
  /** If true, ALL permissions are required (default: any one suffices). */
  requireAll?: boolean;
  /**
   * Extract a display value from dashboard stats.
   * Return undefined to show "—" when stats aren't available.
   */
  statAccessor?: (stats: DashboardStats) => string | number | undefined;
  /** Icon rendered on the module card (emoji or React node string). */
  icon?: string;
  /** Whether to show in the sidebar navigation. Defaults to true. */
  showInSidebar?: boolean;
  /** Order weight for sidebar rendering. Lower = higher. Defaults to id order. */
  sidebarOrder?: number;
}

/* ── Registry ────────────────────────────────────────────────────── */

export const DASHBOARD_MODULES: readonly DashboardModuleDefinition[] = [
  {
    id: 'cases',
    title: 'Case Management',
    description: 'View and manage all cases',
    route: '/cases',
    permissions: ['view_case'],
    statAccessor: (s) => s.total_cases,
    icon: '📋',
    sidebarOrder: 10,
  },
  {
    id: 'evidence',
    title: 'Evidence Vault',
    description: 'Register and review evidence',
    route: '/evidence',
    permissions: ['view_evidence'],
    statAccessor: (s) => s.total_evidence,
    icon: '🔍',
    sidebarOrder: 20,
  },
  {
    id: 'suspects',
    title: 'Suspects',
    description: 'Manage suspects and interrogations',
    route: '/suspects',
    permissions: ['view_suspect'],
    statAccessor: (s) => s.total_suspects,
    icon: '🕵️',
    sidebarOrder: 30,
  },
  {
    id: 'board',
    title: 'Detective Board',
    description: 'Visual crime investigation board',
    route: '/boards',
    permissions: ['view_detectiveboard'],
    icon: '📌',
    sidebarOrder: 40,
    showInSidebar: true,
  },
  {
    id: 'reports',
    title: 'Reports',
    description: 'General case reporting',
    route: '/reports',
    permissions: ['can_forward_to_judiciary'],
    icon: '📊',
    sidebarOrder: 50,
  },
  {
    id: 'bounty',
    title: 'Bounty Tips',
    description: 'Submit or review bounty tip information',
    route: '/bounty',
    permissions: [],
    icon: '💰',
    sidebarOrder: 60,
  },
  {
    id: 'most-wanted',
    title: 'Most Wanted',
    description: 'View most wanted suspects and criminals',
    route: '/most-wanted',
    permissions: [],
    icon: '🚨',
    sidebarOrder: 70,
    showInSidebar: true,
  },
  {
    id: 'admin',
    title: 'Admin Panel',
    description: 'Manage roles and users',
    route: '/admin',
    permissions: ['add_role', 'change_role'],
    statAccessor: (s) => s.total_employees,
    icon: '⚙️',
    sidebarOrder: 80,
  },
] as const;

/**
 * Runtime-extensible module list.
 *
 * Plugins or feature flags can push additional modules at app startup:
 *
 *   registerDashboardModule({ id: 'analytics', title: 'Analytics', ... });
 *
 * These modules will appear on the next dashboard render.
 */
const _runtimeModules: DashboardModuleDefinition[] = [];

export function registerDashboardModule(module: DashboardModuleDefinition): void {
  // Prevent duplicates
  if (
    DASHBOARD_MODULES.some((m) => m.id === module.id) ||
    _runtimeModules.some((m) => m.id === module.id)
  ) {
    return;
  }
  _runtimeModules.push(module);
}

/**
 * Returns the complete module list (static + runtime).
 * The dashboard engine hook consumes this.
 */
export function getAllDashboardModules(): DashboardModuleDefinition[] {
  return [...DASHBOARD_MODULES, ..._runtimeModules];
}

/**
 * OverviewPage — modular dashboard with role-based module cards.
 *
 * Module visibility is driven entirely by the centralised module registry
 * (dashboardModules.ts) and the user's permission set. No role names are
 * referenced in gating logic. Adding a new module to the registry is
 * sufficient — this page renders whatever the engine returns.
 *
 * Each user sees modules relevant ONLY to their role(s):
 * - System Administrator → Admin Panel module
 * - Detective → Detective Board module
 * - Cadet → Complaint Review module
 * - Coroner → Forensic Review module
 * - Police ranks → Case Management modules
 * - Base user → Public modules only (Bounty Tips, Most Wanted)
 */
import { useQuery } from '@tanstack/react-query';
import { Alert } from '@/components/ui/Alert';
import { StatsSkeleton } from '@/components/ui/SkeletonPresets';
import { useDelayedLoading } from '@/hooks/useDelayedLoading';
import { useDashboardModules } from '@/hooks/useDashboardModules';
import { useAuth } from '@/hooks/useAuth';
import { StatsCards } from '@/features/dashboard/StatsCards';
import { DashboardModule } from '@/features/dashboard/DashboardModule';
import { coreApi } from '@/services/api/core.api';
import type { DashboardStats } from '@/types/notification.types';

export function OverviewPage() {
  const { user } = useAuth();
  const { data: stats, isLoading, error } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: () => coreApi.dashboardStats(),
  });

  const showSkeleton = useDelayedLoading(isLoading);
  const { visibleModules, getStatValue } = useDashboardModules(stats);

  const greeting = user
    ? `Welcome, ${user.first_name || user.username}`
    : 'Dashboard';

  const roleLabel = user?.role?.name ?? 'Base User';

  return (
    <div className="page-overview">
      <div className="page-header">
        <h1 className="page-header__title">{greeting}</h1>
        <span className="page-header__role-badge">{roleLabel}</span>
      </div>

      {error && <Alert type="error">Failed to load dashboard stats.</Alert>}

      {showSkeleton ? (
        <StatsSkeleton cards={6} />
      ) : stats ? (
        <StatsCards stats={stats} loading={isLoading} />
      ) : null}

      {/* Module cards — rendered dynamically from the registry, filtered by permissions */}
      {visibleModules.length > 0 ? (
        <div className="dashboard-modules">
          {visibleModules.map((mod) => (
            <DashboardModule
              key={mod.id}
              module={mod}
              value={getStatValue(mod)}
              loading={isLoading}
            />
          ))}
        </div>
      ) : (
        <div className="dashboard-modules dashboard-modules--empty">
          <Alert type="info">
            No modules available for your current role. Contact your administrator
            if you believe this is an error.
          </Alert>
        </div>
      )}
    </div>
  );
}

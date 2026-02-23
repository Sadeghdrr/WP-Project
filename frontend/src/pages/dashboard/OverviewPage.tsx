/**
 * OverviewPage — modular dashboard with role-based module cards.
 *
 * Module visibility is driven entirely by the centralised module registry
 * (dashboardModules.ts) and the user's permission set. No role names are
 * referenced. Adding a new module to the registry is sufficient — this page
 * renders whatever the engine returns.
 */
import { useQuery } from '@tanstack/react-query';
import { Alert } from '@/components/ui/Alert';
import { StatsSkeleton } from '@/components/ui/SkeletonPresets';
import { useDelayedLoading } from '@/hooks/useDelayedLoading';
import { useDashboardModules } from '@/hooks/useDashboardModules';
import { StatsCards } from '@/features/dashboard/StatsCards';
import { DashboardModule } from '@/features/dashboard/DashboardModule';
import { coreApi } from '@/services/api/core.api';
import type { DashboardStats } from '@/types/notification.types';

export function OverviewPage() {
  const { data: stats, isLoading, error } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: () => coreApi.dashboardStats(),
  });

  const showSkeleton = useDelayedLoading(isLoading);
  const { visibleModules, getStatValue } = useDashboardModules(stats);

  return (
    <div className="page-overview">
      <div className="page-header">
        <h1 className="page-header__title">Dashboard</h1>
      </div>

      {error && <Alert type="error">Failed to load dashboard stats.</Alert>}

      {showSkeleton ? (
        <StatsSkeleton cards={6} />
      ) : stats ? (
        <StatsCards stats={stats} loading={isLoading} />
      ) : null}

      {/* Module cards — rendered dynamically from the registry */}
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
    </div>
  );
}

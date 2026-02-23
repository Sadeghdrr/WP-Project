/**
 * OverviewPage — modular dashboard with role-based module cards.
 */
import { useQuery } from '@tanstack/react-query';
import { Skeleton } from '@/components/ui/Skeleton';
import { Alert } from '@/components/ui/Alert';
import { StatsCards } from '@/features/dashboard/StatsCards';
import { DashboardModule } from '@/features/dashboard/DashboardModule';
import { coreApi } from '@/services/api/core.api';
import { CasesPerms, EvidencePerms, SuspectsPerms, BoardPerms, AccountsPerms } from '@/config/permissions';
import type { DashboardStats } from '@/types/notification.types';

export function OverviewPage() {
  const { data: stats, isLoading, error } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: () => coreApi.dashboardStats(),
  });

  return (
    <div className="page-overview">
      <div className="page-header">
        <h1 className="page-header__title">Dashboard</h1>
      </div>

      {error && <Alert type="error">Failed to load dashboard stats.</Alert>}

      {isLoading ? (
        <Skeleton height={300} />
      ) : stats ? (
        <StatsCards stats={stats} loading={isLoading} />
      ) : null}

      {/* Permission-gated module cards */}
      <div className="dashboard-modules">
        <DashboardModule
          permission={CasesPerms.VIEW_CASE}
          title="Case Management"
          value={stats?.total_cases ?? 0}
          description="View and manage all cases"
          to="/cases"
          loading={isLoading}
        />
        <DashboardModule
          permission={EvidencePerms.VIEW_EVIDENCE}
          title="Evidence Vault"
          value={stats?.total_evidence ?? 0}
          description="Register and review evidence"
          to="/evidence"
          loading={isLoading}
        />
        <DashboardModule
          permission={SuspectsPerms.VIEW_SUSPECT}
          title="Suspects"
          value={stats?.total_suspects ?? 0}
          description="Manage suspects and interrogations"
          to="/suspects"
          loading={isLoading}
        />
        <DashboardModule
          permission={BoardPerms.VIEW_DETECTIVEBOARD}
          title="Detective Board"
          value="—"
          description="Visual crime investigation board"
          to="/boards"
          loading={isLoading}
        />
        <DashboardModule
          permission={AccountsPerms.VIEW_ROLE}
          title="Admin Panel"
          value={stats?.total_employees ?? 0}
          description="Manage roles and users"
          to="/admin"
          loading={isLoading}
        />
        <DashboardModule
          permission={CasesPerms.CAN_FORWARD_TO_JUDICIARY}
          title="Reports"
          value="—"
          description="General case reporting"
          to="/reports"
          loading={isLoading}
        />
      </div>
    </div>
  );
}

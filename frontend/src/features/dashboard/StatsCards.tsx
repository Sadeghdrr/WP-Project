/**
 * StatsCards — renders a grid of ModuleCards from DashboardStats.
 * Used on the Home page (public) and Dashboard (authenticated).
 */
import { ModuleCard } from '@/components/dashboard/ModuleCard';
import type { DashboardStats } from '@/types/notification.types';

interface StatsCardsProps {
  stats: DashboardStats | null;
  loading: boolean;
}

export function StatsCards({ stats, loading }: StatsCardsProps) {
  return (
    <div className="stats-cards">
      <ModuleCard
        title="Solved Cases"
        value={stats?.closed_cases ?? 0}
        icon={<span aria-hidden>&#9989;</span>}
        loading={loading}
      />
      <ModuleCard
        title="Active Cases"
        value={stats?.active_cases ?? 0}
        icon={<span aria-hidden>&#128269;</span>}
        loading={loading}
      />
      <ModuleCard
        title="Total Employees"
        value={stats?.total_employees ?? 0}
        icon={<span aria-hidden>&#128101;</span>}
        loading={loading}
      />
      <ModuleCard
        title="Total Suspects"
        value={stats?.total_suspects ?? 0}
        icon={<span aria-hidden>&#128110;</span>}
        loading={loading}
      />
      <ModuleCard
        title="Evidence Items"
        value={stats?.total_evidence ?? 0}
        icon={<span aria-hidden>&#128270;</span>}
        loading={loading}
      />
      <ModuleCard
        title="Voided Cases"
        value={stats?.voided_cases ?? 0}
        icon={<span aria-hidden>&#10060;</span>}
        loading={loading}
      />
    </div>
  );
}

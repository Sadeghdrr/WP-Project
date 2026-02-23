/**
 * DashboardModule — renders a single module card from a registry definition.
 *
 * The parent (OverviewPage) has already filtered the registry via
 * useDashboardModules, so this component does NOT re-check permissions.
 * It simply renders the ModuleCard with the data it receives.
 *
 * Navigation uses React Router (useNavigate) — no page reloads.
 */
import { useNavigate } from 'react-router-dom';
import { ModuleCard } from '@/components/dashboard/ModuleCard';
import type { DashboardModuleDefinition } from '@/config/dashboardModules';

interface DashboardModuleProps {
  module: DashboardModuleDefinition;
  value: string | number;
  loading?: boolean;
}

export function DashboardModule({
  module,
  value,
  loading,
}: DashboardModuleProps) {
  const navigate = useNavigate();

  return (
    <ModuleCard
      title={module.title}
      value={value}
      subtitle={module.description}
      icon={module.icon ? <span aria-hidden>{module.icon}</span> : undefined}
      loading={loading}
      onClick={() => navigate(module.route)}
    />
  );
}

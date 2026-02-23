/**
 * DashboardModule — a permission-gated module card for the dashboard.
 *
 * Wraps a ModuleCard and only renders if the user has the required permission.
 */
import { ModuleCard } from '@/components/dashboard/ModuleCard';
import { usePermissions } from '@/hooks/usePermissions';
import type { ReactNode } from 'react';

interface DashboardModuleProps {
  permission: string;
  title: string;
  value: string | number;
  description?: string;
  icon?: ReactNode;
  to?: string;
  trend?: { value: number; direction: 'up' | 'down' | 'neutral' };
  loading?: boolean;
}

export function DashboardModule({
  permission,
  title,
  value,
  description,
  icon,
  to,
  trend,
  loading,
}: DashboardModuleProps) {
  const { hasPermission } = usePermissions();

  if (!hasPermission(permission)) return null;

  return (
    <ModuleCard
      title={title}
      value={value}
      subtitle={description}
      icon={icon}
      trend={trend}
      loading={loading}
      onClick={to ? () => window.location.assign(to) : undefined}
    />
  );
}

/**
 * ModuleCard — dashboard metric card with optional icon, trend, and children.
 *
 * Supports loading skeleton, click interaction, and custom content injection
 * for the Modular Dashboard (800pts requirement).
 */
import type { ReactNode } from 'react';
import { Skeleton } from '@/components/ui/Skeleton';

export interface ModuleCardProps {
  title: string;
  value?: string | number;
  subtitle?: string;
  icon?: ReactNode;
  trend?: {
    value: number;
    direction: 'up' | 'down' | 'neutral';
  };
  onClick?: () => void;
  loading?: boolean;
  className?: string;
  /** Optional custom content rendered below the value */
  children?: ReactNode;
}

export function ModuleCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  onClick,
  loading = false,
  className = '',
  children,
}: ModuleCardProps) {
  if (loading) {
    return (
      <div className={`module-card ${className}`}>
        <div className="module-card__header">
          <Skeleton variant="circular" width={40} height={40} />
        </div>
        <Skeleton variant="text" width="60%" height="1.75rem" />
        <Skeleton variant="text" width="40%" />
      </div>
    );
  }

  return (
    <div
      className={`module-card ${onClick ? 'module-card--clickable' : ''} ${className}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
    >
      <div className="module-card__header">
        {icon && <div className="module-card__icon">{icon}</div>}
        <span className="module-card__title">{title}</span>
      </div>

      {value !== undefined && (
        <div className="module-card__value">{value}</div>
      )}

      {(subtitle || trend) && (
        <div className="module-card__footer">
          {subtitle && (
            <span className="module-card__subtitle">{subtitle}</span>
          )}
          {trend && (
            <span
              className={`module-card__trend module-card__trend--${trend.direction}`}
            >
              {trend.direction === 'up'
                ? '↑'
                : trend.direction === 'down'
                  ? '↓'
                  : '→'}{' '}
              {Math.abs(trend.value)}%
            </span>
          )}
        </div>
      )}

      {children && <div className="module-card__content">{children}</div>}
    </div>
  );
}

/**
 * Skeleton Presets — pre-composed skeleton layouts matching real components.
 *
 * These avoid the "generic shimmer rectangle" anti-pattern by matching
 * the exact structure of the component being loaded. This dramatically
 * improves perceived performance because the user sees a recognisable
 * placeholder instead of a blank/flash.
 *
 * Usage:
 *   import { TableSkeleton } from '@/components/ui/SkeletonPresets';
 *   if (isLoading) return <TableSkeleton columns={5} rows={8} />;
 *
 * Presets:
 *  - TableSkeleton  → matches <Table> with header row + N data rows
 *  - CardSkeleton   → matches <Card> with title + body
 *  - DetailSkeleton → matches detail pages (header + info grid + sections)
 *  - ListSkeleton   → matches card-list pages
 *  - StatsSkeleton  → matches StatsCards grid
 *  - FormSkeleton   → matches a typical form layout
 */
import { Skeleton } from './Skeleton';

/* ── Table Skeleton ──────────────────────────────────────────────── */

interface TableSkeletonProps {
  columns?: number;
  rows?: number;
}

export function TableSkeleton({ columns = 5, rows = 6 }: TableSkeletonProps) {
  return (
    <div className="skeleton-table">
      {/* Header row */}
      <div className="skeleton-table__header">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={`h-${i}`} variant="text" width="80%" height="0.875rem" />
        ))}
      </div>
      {/* Data rows */}
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="skeleton-table__row">
          {Array.from({ length: columns }).map((_, c) => (
            <Skeleton
              key={`${r}-${c}`}
              variant="text"
              width={c === 0 ? '60%' : '75%'}
              height="0.8125rem"
            />
          ))}
        </div>
      ))}
    </div>
  );
}

/* ── Card Skeleton ───────────────────────────────────────────────── */

interface CardSkeletonProps {
  lines?: number;
  hasHeader?: boolean;
}

export function CardSkeleton({ lines = 3, hasHeader = true }: CardSkeletonProps) {
  return (
    <div className="skeleton-card">
      {hasHeader && (
        <div className="skeleton-card__header">
          <Skeleton variant="text" width="40%" height="1.25rem" />
        </div>
      )}
      <div className="skeleton-card__body">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton
            key={i}
            variant="text"
            width={i === lines - 1 ? '55%' : '90%'}
            height="0.875rem"
          />
        ))}
      </div>
    </div>
  );
}

/* ── Detail Page Skeleton ────────────────────────────────────────── */

interface DetailSkeletonProps {
  sections?: number;
}

export function DetailSkeleton({ sections = 3 }: DetailSkeletonProps) {
  return (
    <div className="skeleton-detail">
      {/* Page header */}
      <div className="skeleton-detail__header">
        <Skeleton variant="text" width="45%" height="1.5rem" />
        <div className="skeleton-detail__badges">
          <Skeleton variant="rectangular" width={80} height={24} />
          <Skeleton variant="rectangular" width={80} height={24} />
        </div>
      </div>

      {/* Info grid */}
      <div className="skeleton-detail__grid">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="skeleton-detail__field">
            <Skeleton variant="text" width="35%" height="0.75rem" />
            <Skeleton variant="text" width="65%" height="0.875rem" />
          </div>
        ))}
      </div>

      {/* Sections */}
      {Array.from({ length: sections }).map((_, i) => (
        <CardSkeleton key={i} lines={4} />
      ))}
    </div>
  );
}

/* ── List Skeleton (card grid) ───────────────────────────────────── */

interface ListSkeletonProps {
  cards?: number;
}

export function ListSkeleton({ cards = 6 }: ListSkeletonProps) {
  return (
    <div className="skeleton-list">
      {Array.from({ length: cards }).map((_, i) => (
        <CardSkeleton key={i} lines={2} />
      ))}
    </div>
  );
}

/* ── Stats Cards Skeleton ────────────────────────────────────────── */

interface StatsSkeletonProps {
  cards?: number;
}

export function StatsSkeleton({ cards = 4 }: StatsSkeletonProps) {
  return (
    <div className="skeleton-stats">
      {Array.from({ length: cards }).map((_, i) => (
        <div key={i} className="skeleton-stats__card">
          <Skeleton variant="text" width="50%" height="0.75rem" />
          <Skeleton variant="text" width="35%" height="1.75rem" />
        </div>
      ))}
    </div>
  );
}

/* ── Form Skeleton ───────────────────────────────────────────────── */

interface FormSkeletonProps {
  fields?: number;
}

export function FormSkeleton({ fields = 4 }: FormSkeletonProps) {
  return (
    <div className="skeleton-form">
      {Array.from({ length: fields }).map((_, i) => (
        <div key={i} className="skeleton-form__field">
          <Skeleton variant="text" width="30%" height="0.75rem" />
          <Skeleton variant="rectangular" width="100%" height={40} />
        </div>
      ))}
      <Skeleton variant="rectangular" width={120} height={40} />
    </div>
  );
}

/**
 * Formatting helpers used across pages and components.
 */
import { CRIME_LEVEL_LABELS } from '@/config/constants';

/** Format an ISO date string to a localised date */
export function formatDate(date: string | Date | null): string {
  if (!date) return '—';
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/** Format an ISO date string to a localised date+time */
export function formatDateTime(date: string | Date | null): string {
  if (!date) return '—';
  return new Date(date).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Human-readable crime level */
export function formatCrimeLevel(level: number): string {
  return CRIME_LEVEL_LABELS[level] ?? `Level ${level}`;
}

/** Replace underscores with spaces and capitalise */
export function formatStatus(status: string): string {
  return status
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Format a number as Rial currency */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('fa-IR').format(amount) + ' ﷼';
}

/** Truncate text to maxLength with ellipsis */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength).trimEnd() + '…';
}

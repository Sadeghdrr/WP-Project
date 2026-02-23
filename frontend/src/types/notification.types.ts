/**
 * Notification & Dashboard types — mirrors backend core.models.
 */
import type { UserListItem } from './user.types';

/* ── Notification ─────────────────────────────────────────────────── */

export interface Notification {
  id: number;
  recipient: UserListItem;
  title: string;
  message: string;
  is_read: boolean;
  content_type: string | null;
  object_id: number | null;
  created_at: string;
}

/* ── Dashboard Stats ──────────────────────────────────────────────── */

export interface CasesByStatus {
  status: string;
  count: number;
}

export interface CasesByCrimeLevel {
  crime_level: number;
  count: number;
}

export interface DashboardStats {
  total_cases: number;
  active_cases: number;
  closed_cases: number;
  voided_cases: number;
  total_suspects: number;
  total_evidence: number;
  total_employees: number;
  unassigned_evidence_count: number;
  cases_by_status: CasesByStatus[];
  cases_by_crime_level: CasesByCrimeLevel[];
  top_wanted_suspects: unknown[];
  recent_activity: unknown[];
}

/* ── Global Search ────────────────────────────────────────────────── */

export interface GlobalSearchResponse {
  cases: unknown[];
  suspects: unknown[];
  evidence: unknown[];
}

/* ── System Constants ─────────────────────────────────────────────── */

export interface SystemConstants {
  crime_levels: { value: number; label: string }[];
  case_statuses: { value: string; label: string }[];
  evidence_types: { value: string; label: string }[];
  suspect_statuses: { value: string; label: string }[];
  [key: string]: unknown;
}

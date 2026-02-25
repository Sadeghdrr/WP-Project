/**
 * Core domain types (dashboard stats, notifications, search).
 * Maps to: core app models + aggregation endpoints.
 */

import type { TimeStamped } from "./common";

// ---------------------------------------------------------------------------
// Notification
// ---------------------------------------------------------------------------

export interface Notification extends TimeStamped {
  id: number;
  recipient: number;
  title: string;
  message: string;
  is_read: boolean;
  content_type: number | null;
  object_id: number | null;
}

export interface NotificationMarkReadRequest {
  is_read: boolean;
}

// ---------------------------------------------------------------------------
// Dashboard Statistics (from core aggregation endpoints)
// ---------------------------------------------------------------------------

export interface DashboardStats {
  total_solved_cases: number;
  total_employees: number;
  active_cases: number;
  // Server may include additional stats
  [key: string]: number;
}

// ---------------------------------------------------------------------------
// Search (from GET /api/core/search/?q=...)
// ---------------------------------------------------------------------------

export type SearchCategory = "cases" | "suspects" | "evidence";

export interface SearchCaseResult {
  id: number;
  title: string;
  status: string;
  crime_level: number;
  crime_level_label: string;
  created_at: string;
}

export interface SearchSuspectResult {
  id: number;
  full_name: string;
  national_id: string;
  status: string;
  case_id: number;
  case_title: string;
}

export interface SearchEvidenceResult {
  id: number;
  title: string;
  evidence_type: string;
  evidence_type_label: string;
  case_id: number;
  case_title: string;
}

export interface GlobalSearchResponse {
  query: string;
  total_results: number;
  cases: SearchCaseResult[];
  suspects: SearchSuspectResult[];
  evidence: SearchEvidenceResult[];
}

// ---------------------------------------------------------------------------
// System Constants (from GET /api/core/constants/)
// ---------------------------------------------------------------------------

/** Generic choice item returned by the constants endpoint. */
export interface ChoiceItem {
  value: string;
  label: string;
}

/** Role hierarchy entry returned by the constants endpoint. */
export interface RoleHierarchyItem {
  id: number;
  name: string;
  hierarchy_level: number;
}

/**
 * Full shape of GET /api/core/constants/ response.
 *
 * Matches `SystemConstantsService.get_constants()` output.
 */
export interface SystemConstants {
  crime_levels: ChoiceItem[];
  case_statuses: ChoiceItem[];
  case_creation_types: ChoiceItem[];
  evidence_types: ChoiceItem[];
  evidence_file_types: ChoiceItem[];
  suspect_statuses: ChoiceItem[];
  verdict_choices: ChoiceItem[];
  bounty_tip_statuses: ChoiceItem[];
  complainant_statuses: ChoiceItem[];
  role_hierarchy: RoleHierarchyItem[];
}

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
// Search
// ---------------------------------------------------------------------------

export interface SearchRequest {
  q: string;
  type?: "cases" | "suspects" | "evidence" | "users";
}

export interface SearchResultItem {
  id: number;
  type: string;
  title: string;
  description: string;
  url: string;
}

export interface SearchResponse {
  query: string;
  results: SearchResultItem[];
  count: number;
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

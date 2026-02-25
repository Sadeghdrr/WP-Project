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
// System Constants
// ---------------------------------------------------------------------------

export interface SystemConstants {
  reward_multiplier: number; // 20_000_000 Rials
  crime_levels: Array<{ value: number; label: string }>;
  case_statuses: Array<{ value: string; label: string }>;
  evidence_types: Array<{ value: string; label: string }>;
  suspect_statuses: Array<{ value: string; label: string }>;
}

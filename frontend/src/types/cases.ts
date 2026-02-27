/**
 * Case domain types.
 * Maps to: cases app models (Case, CaseComplainant, CaseWitness, CaseStatusLog).
 */

import type { ISODateTime, TimeStamped } from "./common";
import type { UserRef } from "./auth";

// ---------------------------------------------------------------------------
// Enumerations (string literal unions — no enum keyword due to erasableSyntaxOnly)
// ---------------------------------------------------------------------------

/** Crime severity. Integer values: 1=Level3(minor), 2=Level2, 3=Level1(major), 4=Critical */
export type CrimeLevel = 1 | 2 | 3 | 4;

export const CRIME_LEVEL_LABELS: Record<CrimeLevel, string> = {
  1: "Level 3 (Minor)",
  2: "Level 2 (Medium)",
  3: "Level 1 (Major)",
  4: "Critical",
};

export type CaseStatus =
  | "complaint_registered"
  | "cadet_review"
  | "returned_to_complainant"
  | "officer_review"
  | "returned_to_cadet"
  | "voided"
  | "pending_approval"
  | "open"
  | "investigation"
  | "judiciary"
  | "closed";

export type CaseCreationType = "complaint" | "crime_scene";

export type ComplainantStatus = "pending" | "approved" | "rejected";

// ---------------------------------------------------------------------------
// Case
// ---------------------------------------------------------------------------

export interface Case extends TimeStamped {
  id: number;
  title: string;
  description: string;
  crime_level: CrimeLevel;
  status: CaseStatus;
  creation_type: CaseCreationType;
  rejection_count: number;
  incident_date: ISODateTime | null;
  location: string;
  created_by: UserRef;
  approved_by: UserRef | null;
  assigned_detective: UserRef | null;
  assigned_sergeant: UserRef | null;
  assigned_captain: UserRef | null;
  assigned_judge: UserRef | null;
  is_open: boolean;
}

/** Minimal case reference for nested use (e.g. inside Suspect) */
export interface CaseRef {
  id: number;
  title: string;
  status: CaseStatus;
  crime_level: CrimeLevel;
}

// ---------------------------------------------------------------------------
// CaseComplainant
// ---------------------------------------------------------------------------

export interface CaseComplainant extends TimeStamped {
  id: number;
  case: number;
  user: number;
  user_display: string;
  is_primary: boolean;
  status: ComplainantStatus;
  reviewed_by: number | null;
}

// ---------------------------------------------------------------------------
// CaseWitness
// ---------------------------------------------------------------------------

export interface CaseWitness extends TimeStamped {
  id: number;
  case: number;
  full_name: string;
  phone_number: string;
  national_id: string;
}

// ---------------------------------------------------------------------------
// CaseStatusLog
// ---------------------------------------------------------------------------

export interface CaseStatusLog extends TimeStamped {
  id: number;
  case: number;
  from_status: CaseStatus;
  to_status: CaseStatus;
  changed_by: number | null;
  changed_by_name: string | null;
  message: string;
}

// ---------------------------------------------------------------------------
// Request DTOs
// ---------------------------------------------------------------------------

export interface CaseCreateComplaintRequest {
  title: string;
  description: string;
  crime_level: CrimeLevel;
  incident_date?: ISODateTime;
  location?: string;
}

export interface CaseCreateCrimeSceneRequest {
  title: string;
  description: string;
  crime_level: CrimeLevel;
  incident_date?: ISODateTime;
  location?: string;
  witnesses?: Array<{
    full_name: string;
    phone_number: string;
    national_id: string;
  }>;
}

export interface CaseStatusTransitionRequest {
  message?: string;
}

export interface CaseGenericTransitionRequest {
  target_status: CaseStatus;
  message?: string;
}

export interface ReviewDecisionRequest {
  decision: "approve" | "reject";
  message?: string;
}

export interface ResubmitComplaintRequest {
  title?: string;
  description?: string;
  incident_date?: ISODateTime;
  location?: string;
}

export interface AssignPersonnelRequest {
  user_id: number;
}

export interface ComplainantCreateRequest {
  user_id: number;
  is_primary?: boolean;
}

export interface ComplainantReviewRequest {
  status: "approved" | "rejected";
}

// ---------------------------------------------------------------------------
// List item (lightweight, from CaseListSerializer)
// ---------------------------------------------------------------------------

export interface CaseListItem {
  id: number;
  title: string;
  crime_level: CrimeLevel;
  crime_level_display: string;
  status: CaseStatus;
  status_display: string;
  creation_type: CaseCreationType;
  incident_date: ISODateTime | null;
  location: string;
  assigned_detective: number | null;
  assigned_detective_name: string | null;
  complainant_count: number;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

// ---------------------------------------------------------------------------
// Detail (full, from CaseDetailSerializer)
// ---------------------------------------------------------------------------

export interface CaseDetail extends TimeStamped {
  id: number;
  title: string;
  description: string;
  crime_level: CrimeLevel;
  crime_level_display: string;
  status: CaseStatus;
  status_display: string;
  creation_type: CaseCreationType;
  rejection_count: number;
  incident_date: ISODateTime | null;
  location: string;
  created_by: number;
  approved_by: number | null;
  assigned_detective: number | null;
  assigned_sergeant: number | null;
  assigned_captain: number | null;
  assigned_judge: number | null;
  complainants: CaseComplainant[];
  witnesses: CaseWitness[];
  status_logs: CaseStatusLog[];
  calculations: CaseCalculations | null;
}

export interface CaseCalculations {
  crime_level_degree: number;
  days_since_creation: number;
  tracking_threshold: number;
  reward_rials: number;
}

// ---------------------------------------------------------------------------
// Case Report (from GET /api/cases/{id}/report/)
// ---------------------------------------------------------------------------

/** Lightweight person reference in the report payload */
export interface ReportPersonRef {
  id: number;
  full_name: string;
  role: string | null;
}

export interface ReportCaseInfo {
  id: number;
  title: string;
  description: string;
  crime_level: CrimeLevel;
  crime_level_display: string;
  status: CaseStatus;
  status_display: string;
  creation_type: CaseCreationType;
  rejection_count: number;
  incident_date: string | null;
  location: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ReportPersonnel {
  created_by: ReportPersonRef | null;
  approved_by: ReportPersonRef | null;
  assigned_detective: ReportPersonRef | null;
  assigned_sergeant: ReportPersonRef | null;
  assigned_captain: ReportPersonRef | null;
  assigned_judge: ReportPersonRef | null;
}

export interface ReportComplainant {
  id: number;
  user: ReportPersonRef | null;
  is_primary: boolean;
  status: string;
  reviewed_by: ReportPersonRef | null;
}

export interface ReportWitness {
  id: number;
  full_name: string;
  phone_number: string | null;
  national_id: string | null;
}

export interface ReportEvidence {
  id: number;
  evidence_type: string;
  title: string;
  description: string | null;
  registered_by: ReportPersonRef | null;
  created_at: string | null;
}

export interface ReportInterrogation {
  id: number;
  detective: ReportPersonRef | null;
  sergeant: ReportPersonRef | null;
  detective_guilt_score: number | null;
  sergeant_guilt_score: number | null;
  notes: string | null;
  created_at: string | null;
}

export interface ReportTrial {
  id: number;
  judge: ReportPersonRef | null;
  verdict: string;
  punishment_title: string | null;
  punishment_description: string | null;
  created_at: string | null;
}

export interface ReportSuspect {
  id: number;
  full_name: string;
  national_id: string | null;
  status: string;
  status_display: string;
  wanted_since: string | null;
  days_wanted: number | null;
  identified_by: ReportPersonRef | null;
  sergeant_approval_status: string | null;
  approved_by_sergeant: ReportPersonRef | null;
  sergeant_rejection_message: string | null;
  interrogations: ReportInterrogation[];
  trials: ReportTrial[];
}

export interface ReportStatusEntry {
  id: number;
  from_status: string | null;
  to_status: string;
  changed_by: ReportPersonRef | null;
  message: string | null;
  created_at: string | null;
}

export interface CaseReport {
  case: ReportCaseInfo;
  personnel: ReportPersonnel;
  complainants: ReportComplainant[];
  witnesses: ReportWitness[];
  evidence: ReportEvidence[];
  suspects: ReportSuspect[];
  status_history: ReportStatusEntry[];
  calculations: CaseCalculations | null;
}

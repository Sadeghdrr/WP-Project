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
  | "suspect_identified"
  | "sergeant_review"
  | "arrest_ordered"
  | "interrogation"
  | "captain_review"
  | "chief_review"
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
  user: UserRef;
  is_primary: boolean;
  status: ComplainantStatus;
  reviewed_by: UserRef | null;
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
  changed_by: UserRef | null;
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

/**
 * Suspects domain types.
 * Maps to: suspects app models (Suspect, Warrant, Interrogation, Trial, BountyTip, Bail, SuspectStatusLog).
 */

import type { ISODateTime, TimeStamped } from "./common";
import type { UserRef } from "./auth";

// ---------------------------------------------------------------------------
// Enumerations
// ---------------------------------------------------------------------------

export type SuspectStatus =
  | "wanted"
  | "arrested"
  | "under_interrogation"
  | "pending_captain_verdict"
  | "pending_chief_approval"
  | "under_trial"
  | "convicted"
  | "acquitted"
  | "released";

export type WarrantStatus = "active" | "executed" | "expired" | "cancelled";
export type WarrantPriority = "normal" | "high" | "critical";

export type VerdictChoice = "guilty" | "innocent";

export type BountyTipStatus =
  | "pending"
  | "officer_reviewed"
  | "verified"
  | "rejected";

export type SergeantApprovalStatus = "pending" | "approved" | "rejected";

// ---------------------------------------------------------------------------
// Suspect
// ---------------------------------------------------------------------------

export interface Suspect extends TimeStamped {
  id: number;
  case: number;
  user: UserRef | null;
  full_name: string;
  national_id: string;
  phone_number: string;
  photo: string | null; // URL
  address: string;
  description: string;
  status: SuspectStatus;
  wanted_since: ISODateTime;
  arrested_at: ISODateTime | null;
  identified_by: UserRef;
  approved_by_sergeant: UserRef | null;
  sergeant_approval_status: SergeantApprovalStatus;
  sergeant_rejection_message: string;
  // Computed properties from backend
  days_wanted: number;
  is_most_wanted: boolean;
  most_wanted_score: number;
  reward_amount: number; // in Rials
}

/** Most-wanted list item — maps to backend MostWantedSerializer */
export interface MostWantedEntry {
  id: number;
  full_name: string;
  national_id: string;
  photo: string | null;
  description: string;
  address: string;
  status: SuspectStatus;
  status_display: string;
  case: number;
  case_title: string | null;
  wanted_since: ISODateTime;
  days_wanted: number;
  most_wanted_score: number;
  reward_amount: number;
  calculated_reward: number;
}

// ---------------------------------------------------------------------------
// Warrant
// ---------------------------------------------------------------------------

export interface Warrant extends TimeStamped {
  id: number;
  suspect: number;
  reason: string;
  issued_by: UserRef;
  issued_at: ISODateTime;
  status: WarrantStatus;
  priority: WarrantPriority;
}

// ---------------------------------------------------------------------------
// Interrogation
// ---------------------------------------------------------------------------

export interface Interrogation extends TimeStamped {
  id: number;
  suspect: number;
  case: number;
  detective: UserRef;
  sergeant: UserRef;
  detective_guilt_score: number; // 1–10
  sergeant_guilt_score: number; // 1–10
  notes: string;
}

export interface InterrogationCreateRequest {
  suspect: number;
  case: number;
  detective_guilt_score: number;
  sergeant_guilt_score: number;
  notes?: string;
}

// ---------------------------------------------------------------------------
// Trial
// ---------------------------------------------------------------------------

export interface Trial extends TimeStamped {
  id: number;
  suspect: number;
  case: number;
  judge: UserRef;
  verdict: VerdictChoice;
  punishment_title: string;
  punishment_description: string;
}

export interface TrialCreateRequest {
  suspect: number;
  case: number;
  verdict: VerdictChoice;
  punishment_title?: string;
  punishment_description?: string;
}

// ---------------------------------------------------------------------------
// BountyTip
// ---------------------------------------------------------------------------

/** Compact bounty-tip item — maps to BountyTipListSerializer */
export interface BountyTipListItem {
  id: number;
  suspect: number | null;
  case: number | null;
  informant: number;
  informant_name: string | null;
  status: BountyTipStatus;
  status_display: string;
  is_claimed: boolean;
  created_at: ISODateTime;
}

/** Full bounty-tip detail — maps to BountyTipDetailSerializer */
export interface BountyTip extends TimeStamped {
  id: number;
  suspect: number | null;
  case: number | null;
  informant: number;
  informant_name: string | null;
  information: string;
  status: BountyTipStatus;
  status_display: string;
  reviewed_by: number | null;
  reviewed_by_name: string | null;
  verified_by: number | null;
  verified_by_name: string | null;
  unique_code: string | null;
  reward_amount: number | null; // Rials
  is_claimed: boolean;
}

export interface BountyTipCreateRequest {
  suspect?: number;
  case?: number;
  information: string;
}

export interface BountyTipReviewRequest {
  decision: "accept" | "reject";
  review_notes?: string;
}

export interface BountyTipVerifyRequest {
  decision: "verify" | "reject";
  verification_notes?: string;
}

export interface BountyVerifyLookupRequest {
  national_id: string;
  unique_code: string;
}

export interface BountyVerifyLookupResponse {
  tip_id: number;
  informant_name: string;
  informant_national_id: string;
  reward_amount: number;
  is_claimed: boolean;
  suspect_name: string | null;
  case_id: number | null;
}

// ---------------------------------------------------------------------------
// Bail
// ---------------------------------------------------------------------------

export interface Bail extends TimeStamped {
  id: number;
  suspect: number;
  case: number;
  amount: number; // Rials
  approved_by: UserRef;
  conditions: string;
  is_paid: boolean;
  payment_reference: string;
  paid_at: ISODateTime | null;
}

export interface BailCreateRequest {
  suspect: number;
  case: number;
  amount: number;
  conditions?: string;
}

// ---------------------------------------------------------------------------
// SuspectStatusLog
// ---------------------------------------------------------------------------

export interface SuspectStatusLog extends TimeStamped {
  id: number;
  suspect: number;
  from_status: SuspectStatus;
  to_status: SuspectStatus;
  changed_by: UserRef | null;
  notes: string;
}

// ---------------------------------------------------------------------------
// Suspect Create / Update
// ---------------------------------------------------------------------------

export interface SuspectCreateRequest {
  case: number;
  full_name: string;
  national_id?: string;
  phone_number?: string;
  address?: string;
  description?: string;
  // photo is uploaded as FormData, not JSON
}

export interface SuspectApprovalRequest {
  sergeant_approval_status: "approved" | "rejected";
  sergeant_rejection_message?: string;
}

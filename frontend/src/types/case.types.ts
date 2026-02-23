/**
 * Case types — mirrors backend cases.models.
 */
import type { UserListItem } from './user.types';

/* ── Enums (as const objects — erasableSyntaxOnly) ────────────────── */

export const CrimeLevel = {
  LEVEL_3: 1,
  LEVEL_2: 2,
  LEVEL_1: 3,
  CRITICAL: 4,
} as const;
export type CrimeLevel = (typeof CrimeLevel)[keyof typeof CrimeLevel];

export const CaseStatus = {
  DRAFT: 'draft',
  COMPLAINT_REGISTERED: 'complaint_registered',
  CADET_REVIEW: 'cadet_review',
  RETURNED_TO_COMPLAINANT: 'returned_to_complainant',
  OFFICER_REVIEW: 'officer_review',
  RETURNED_TO_CADET: 'returned_to_cadet',
  VOIDED: 'voided',
  PENDING_APPROVAL: 'pending_approval',
  OPEN: 'open',
  INVESTIGATION: 'investigation',
  SUSPECT_IDENTIFIED: 'suspect_identified',
  SERGEANT_REVIEW: 'sergeant_review',
  ARREST_ORDERED: 'arrest_ordered',
  INTERROGATION: 'interrogation',
  CAPTAIN_REVIEW: 'captain_review',
  CHIEF_REVIEW: 'chief_review',
  JUDICIARY: 'judiciary',
  CLOSED: 'closed',
} as const;
export type CaseStatus = (typeof CaseStatus)[keyof typeof CaseStatus];

export const CaseCreationType = {
  COMPLAINT: 'complaint',
  CRIME_SCENE: 'crime_scene',
} as const;
export type CaseCreationType = (typeof CaseCreationType)[keyof typeof CaseCreationType];

export const ComplainantStatus = {
  PENDING: 'pending',
  APPROVED: 'approved',
  REJECTED: 'rejected',
} as const;
export type ComplainantStatus = (typeof ComplainantStatus)[keyof typeof ComplainantStatus];

/* ── Interfaces ───────────────────────────────────────────────────── */

export interface CaseListItem {
  id: number;
  title: string;
  crime_level: CrimeLevel;
  status: CaseStatus;
  creation_type: CaseCreationType;
  incident_date: string | null;
  location: string;
  assigned_detective: UserListItem | null;
  complainant_count: number;
}

export interface CaseDetail extends CaseListItem {
  description: string;
  rejection_count: number;
  created_by: UserListItem;
  approved_by: UserListItem | null;
  assigned_sergeant: UserListItem | null;
  assigned_captain: UserListItem | null;
  assigned_judge: UserListItem | null;
  complainants: CaseComplainant[];
  witnesses: CaseWitness[];
  status_logs: CaseStatusLog[];
  calculations: CaseCalculations | null;
  created_at: string;
  updated_at: string;
}

export interface CaseComplainant {
  id: number;
  user: UserListItem;
  is_primary: boolean;
  status: ComplainantStatus;
  reviewed_by: UserListItem | null;
}

export interface CaseWitness {
  id: number;
  full_name: string;
  phone_number: string;
  national_id: string;
}

export interface CaseStatusLog {
  id: number;
  from_status: CaseStatus;
  to_status: CaseStatus;
  changed_by: UserListItem;
  message: string;
  created_at: string;
}

export interface CaseCalculations {
  total_evidence: number;
  total_suspects: number;
  total_witnesses: number;
  total_complainants: number;
}

/* ── Request DTOs ─────────────────────────────────────────────────── */

export interface CaseCreateRequest {
  title: string;
  description: string;
  crime_level: CrimeLevel;
  incident_date?: string;
  location?: string;
  creation_type?: CaseCreationType;
}

export interface CaseUpdateRequest {
  title?: string;
  description?: string;
  incident_date?: string;
  location?: string;
}

export interface CaseReviewRequest {
  action: 'approve' | 'reject' | 'return';
  message?: string;
}

export interface WitnessCreateRequest {
  full_name: string;
  phone_number: string;
  national_id: string;
}

export interface ComplainantCreateRequest {
  user_id: number;
  is_primary?: boolean;
}

export interface ComplainantReviewRequest {
  action: 'approve' | 'reject';
}

/* ── Filter params ────────────────────────────────────────────────── */

export interface CaseFilterParams {
  status?: CaseStatus;
  crime_level?: CrimeLevel;
  creation_type?: CaseCreationType;
  assigned_detective?: number;
}

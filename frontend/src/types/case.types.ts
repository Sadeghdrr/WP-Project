/**
 * Case types — mirror backend cases app models and serializers.
 * DO NOT modify without verifying backend DTOs.
 */

/** CrimeLevel from backend CrimeLevel IntegerChoices */
export const CrimeLevel = {
  LEVEL_3: 1,
  LEVEL_2: 2,
  LEVEL_1: 3,
  CRITICAL: 4,
} as const;

export type CrimeLevelValue = (typeof CrimeLevel)[keyof typeof CrimeLevel];

/** CaseStatus from backend CaseStatus TextChoices */
export const CaseStatus = {
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

export type CaseStatusValue = (typeof CaseStatus)[keyof typeof CaseStatus];

/** CaseCreationType from backend */
export const CaseCreationType = {
  COMPLAINT: 'complaint',
  CRIME_SCENE: 'crime_scene',
} as const;

export type CaseCreationTypeValue = (typeof CaseCreationType)[keyof typeof CaseCreationType];

/** ComplainantStatus from backend ComplainantStatus */
export const ComplainantStatus = {
  PENDING: 'pending',
  APPROVED: 'approved',
  REJECTED: 'rejected',
} as const;

export type ComplainantStatusValue = (typeof ComplainantStatus)[keyof typeof ComplainantStatus];

/** CaseComplainant — from CaseComplainantSerializer */
export interface CaseComplainant {
  id: number;
  user: number;
  user_display: string;
  is_primary: boolean;
  status: ComplainantStatusValue;
  reviewed_by: number | null;
  created_at: string;
  updated_at: string;
}

/** CaseWitness — from CaseWitnessSerializer */
export interface CaseWitness {
  id: number;
  full_name: string;
  phone_number: string;
  national_id: string;
  created_at: string;
  updated_at: string;
}

/** CaseStatusLog — from CaseStatusLogSerializer */
export interface CaseStatusLog {
  id: number;
  from_status: CaseStatusValue;
  to_status: CaseStatusValue;
  changed_by: number | null;
  changed_by_name: string | null;
  message: string;
  created_at: string;
}

/** Case calculations — from CaseCalculationsSerializer */
export interface CaseCalculations {
  crime_level_degree: number;
  days_since_creation: number;
  tracking_threshold: number;
  reward_rials: number;
}

/** Case detail — from CaseDetailSerializer */
export interface Case {
  id: number;
  title: string;
  description: string;
  crime_level: CrimeLevelValue;
  crime_level_display: string;
  status: CaseStatusValue;
  status_display: string;
  creation_type: CaseCreationTypeValue;
  rejection_count: number;
  incident_date: string | null;
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
  calculations: CaseCalculations;
  created_at: string;
  updated_at: string;
}

/** Case list item — from CaseListSerializer */
export interface CaseListItem {
  id: number;
  title: string;
  crime_level: CrimeLevelValue;
  crime_level_display: string;
  status: CaseStatusValue;
  status_display: string;
  creation_type: CaseCreationTypeValue;
  incident_date: string | null;
  location: string;
  assigned_detective: number | null;
  assigned_detective_name: string | null;
  complainant_count: number;
  created_at: string;
  updated_at: string;
}

/** Complaint case create — from ComplaintCaseCreateSerializer */
export interface ComplaintCaseCreateRequest {
  title: string;
  description: string;
  crime_level: CrimeLevelValue;
  incident_date?: string | null;
  location?: string;
}

/** Resubmit — from ResubmitComplaintSerializer */
export interface ResubmitComplaintRequest {
  title?: string;
  description?: string;
  incident_date?: string | null;
  location?: string;
}

/** Cadet/Officer review — from CadetReviewSerializer, OfficerReviewSerializer */
export interface ReviewDecisionRequest {
  decision: 'approve' | 'reject';
  message?: string;
}

/** Add complainant — from AddComplainantSerializer */
export interface AddComplainantRequest {
  user_id: number;
}

/** Complainant review — from ComplainantReviewSerializer */
export interface ComplainantReviewRequest {
  decision: 'approve' | 'reject';
}

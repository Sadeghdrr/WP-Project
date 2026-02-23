/**
 * Suspect, Interrogation, Trial, Bounty, Bail types
 * — mirrors backend suspects.models.
 */
import type { UserListItem } from './user.types';

/* ── Enums (as const objects — erasableSyntaxOnly) ────────────────── */

export const SuspectStatus = {
  WANTED: 'wanted',
  IN_CUSTODY: 'in_custody',
  UNDER_INTERROGATION: 'under_interrogation',
  CAPTAIN_REVIEW: 'captain_review',
  PENDING_CHIEF_APPROVAL: 'pending_chief_approval',
  UNDER_TRIAL: 'under_trial',
  CONVICTED: 'convicted',
  RELEASED: 'released',
  ACQUITTED: 'acquitted',
} as const;
export type SuspectStatus = (typeof SuspectStatus)[keyof typeof SuspectStatus];

export const VerdictChoice = {
  GUILTY: 'guilty',
  NOT_GUILTY: 'not_guilty',
} as const;
export type VerdictChoice = (typeof VerdictChoice)[keyof typeof VerdictChoice];

export const BountyTipStatus = {
  PENDING: 'pending',
  OFFICER_REVIEWED: 'officer_reviewed',
  VERIFIED: 'verified',
  REJECTED: 'rejected',
} as const;
export type BountyTipStatus = (typeof BountyTipStatus)[keyof typeof BountyTipStatus];

export const WarrantPriority = {
  NORMAL: 'normal',
  HIGH: 'high',
  CRITICAL: 'critical',
} as const;
export type WarrantPriority = (typeof WarrantPriority)[keyof typeof WarrantPriority];

export const WarrantStatus = {
  ACTIVE: 'active',
  EXECUTED: 'executed',
  EXPIRED: 'expired',
  CANCELLED: 'cancelled',
} as const;
export type WarrantStatus = (typeof WarrantStatus)[keyof typeof WarrantStatus];

/* ── Suspect ──────────────────────────────────────────────────────── */

export interface SuspectListItem {
  id: number;
  full_name: string;
  national_id: string;
  status: SuspectStatus;
  approval_status: string;
  case: number;
  most_wanted_score: number;
}

export interface SuspectDetail extends SuspectListItem {
  first_name: string;
  last_name: string;
  date_of_birth: string | null;
  phone_number: string;
  photo: string | null;
  address: string;
  description: string;
  aliases: string;
  arrest_date: string | null;
  arrest_location: string;
  days_wanted: number;
  reward_amount: number;
  interrogations: InterrogationListItem[];
  trials: TrialListItem[];
  bails: BailListItem[];
  created_at: string;
  updated_at: string;
}

export interface SuspectCreateRequest {
  first_name: string;
  last_name: string;
  national_id: string;
  case: number;
  date_of_birth?: string;
  gender?: string;
  address?: string;
  phone_number?: string;
  photo?: File;
  description?: string;
  aliases?: string;
}

export type SuspectUpdateRequest = Partial<Omit<SuspectCreateRequest, 'case'>>;

/* ── Interrogation ────────────────────────────────────────────────── */

export interface InterrogationListItem {
  id: number;
  suspect: number;
  conducted_by: UserListItem;
  technique: string;
  score: number;
  duration_minutes: number;
  created_at: string;
}

export interface InterrogationDetail extends InterrogationListItem {
  questions: string;
  responses: string;
  notes: string;
}

export interface InterrogationCreateRequest {
  technique?: string;
  questions?: string;
  responses?: string;
  score: number;
  notes?: string;
  duration_minutes?: number;
}

/* ── Trial ─────────────────────────────────────────────────────────── */

export interface TrialListItem {
  id: number;
  suspect: number;
  judge: UserListItem;
  verdict: VerdictChoice;
  sentence: string;
  trial_date: string;
}

export interface TrialDetail extends TrialListItem {
  notes: string;
}

export interface TrialCreateRequest {
  verdict: VerdictChoice;
  sentence?: string;
  notes?: string;
  trial_date?: string;
}

/* ── Bounty Tip ───────────────────────────────────────────────────── */

export interface BountyTipListItem {
  id: number;
  suspect: number | null;
  case: number | null;
  informant: UserListItem;
  status: BountyTipStatus;
  created_at: string;
}

export interface BountyTipDetail extends BountyTipListItem {
  information: string;
  reviewed_by: UserListItem | null;
  verified_by: UserListItem | null;
  unique_code: string;
  reward_amount: number;
  is_claimed: boolean;
}

export interface BountyTipCreateRequest {
  suspect?: number;
  case?: number;
  information: string;
}

export interface BountyTipReviewRequest {
  action: 'approve' | 'reject';
}

export interface BountyRewardLookupRequest {
  national_id: string;
  unique_code: string;
}

/* ── Bail ──────────────────────────────────────────────────────────── */

export interface BailListItem {
  id: number;
  suspect: number;
  case: number;
  amount: number;
  conditions: string;
  is_paid: boolean;
  payment_reference: string;
  paid_at: string | null;
  approved_by: UserListItem | null;
}

export type BailDetail = BailListItem;

export interface BailCreateRequest {
  amount: number;
  conditions?: string;
}

/* ── Suspect filters ──────────────────────────────────────────────── */

export interface SuspectFilterParams {
  status?: SuspectStatus;
  case?: number;
}

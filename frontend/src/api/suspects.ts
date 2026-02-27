/**
 * Suspects & Bounty Tips API service.
 *
 * All suspect/bounty-related API calls — CRUD, workflow actions,
 * interrogations, trials, bails, most wanted, bounty tips.
 */

import { apiGet, apiPost, apiPatch, apiDelete, apiPostForm } from "./client";
import type { ApiResponse } from "./client";
import { API } from "./endpoints";
import type {
  Suspect,
  SuspectCreateRequest,
  Warrant,
  Interrogation,
  InterrogationCreateRequest,
  Trial,
  TrialCreateRequest,
  Bail,
  BailCreateRequest,
  MostWantedEntry,
  BountyTipListItem,
  BountyTip,
  BountyTipCreateRequest,
  BountyTipReviewRequest,
  BountyTipVerifyRequest,
  BountyVerifyLookupRequest,
  BountyVerifyLookupResponse,
} from "../types";

// ---------------------------------------------------------------------------
// Query params helpers
// ---------------------------------------------------------------------------

export interface SuspectFilters {
  case?: number;
  status?: string;
  sergeant_approval_status?: string;
  search?: string;
}

export interface BountyTipFilters {
  status?: string;
  search?: string;
}

function buildQuery(filters: Record<string, unknown>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "" && value !== null) {
      params.set(key, String(value));
    }
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

// ---------------------------------------------------------------------------
// Suspects — CRUD
// ---------------------------------------------------------------------------

/** List suspects, optionally filtered by case / status. */
export function fetchSuspects(
  filters: SuspectFilters = {},
): Promise<ApiResponse<Suspect[]>> {
  return apiGet<Suspect[]>(`${API.SUSPECTS}${buildQuery(filters)}`);
}

/** Fetch suspect detail (includes nested interrogations, trials, bails). */
export function fetchSuspectDetail(id: number): Promise<ApiResponse<Suspect>> {
  return apiGet<Suspect>(API.suspect(id));
}

/** Create (identify) a new suspect. Accepts JSON or FormData (for photo upload). */
export function createSuspect(
  data: SuspectCreateRequest | FormData,
): Promise<ApiResponse<Suspect>> {
  if (data instanceof FormData) {
    return apiPostForm<Suspect>(API.SUSPECTS, data);
  }
  return apiPost<Suspect>(API.SUSPECTS, data);
}

/** Update a suspect profile. */
export function updateSuspect(
  id: number,
  data: Partial<SuspectCreateRequest>,
): Promise<ApiResponse<Suspect>> {
  return apiPatch<Suspect>(API.suspect(id), data);
}

/** Delete a suspect record. */
export function deleteSuspect(id: number): Promise<ApiResponse<void>> {
  return apiDelete<void>(API.suspect(id));
}

// ---------------------------------------------------------------------------
// Suspects — Workflow Actions
// ---------------------------------------------------------------------------

export interface ApproveRequest {
  decision: "approve" | "reject";
  rejection_message?: string;
}

/** Sergeant approves / rejects a suspect. */
export function approveSuspect(
  id: number,
  data: ApproveRequest,
): Promise<ApiResponse<Suspect>> {
  return apiPost<Suspect>(API.SUSPECT_APPROVE(id), data);
}

export interface ArrestRequest {
  arrest_location: string;
  arrest_notes?: string;
  warrant_override_justification?: string;
}

/** Execute arrest on a suspect. */
export function arrestSuspect(
  id: number,
  data: ArrestRequest,
): Promise<ApiResponse<Suspect>> {
  return apiPost<Suspect>(API.SUSPECT_ARREST(id), data);
}

export interface CaptainVerdictRequest {
  verdict: "guilty" | "innocent";
  notes: string;
}

/** Captain renders verdict on suspect. */
export function submitCaptainVerdict(
  id: number,
  data: CaptainVerdictRequest,
): Promise<ApiResponse<Suspect>> {
  return apiPost<Suspect>(API.SUSPECT_CAPTAIN_VERDICT(id), data);
}

export interface ChiefApprovalRequest {
  decision: "approve" | "reject";
  notes?: string;
}

/** Chief approves / rejects suspect for trial. */
export function submitChiefApproval(
  id: number,
  data: ChiefApprovalRequest,
): Promise<ApiResponse<Suspect>> {
  return apiPost<Suspect>(API.SUSPECT_CHIEF_APPROVAL(id), data);
}

// ---------------------------------------------------------------------------
// Interrogations (nested under suspect)
// ---------------------------------------------------------------------------

export function fetchInterrogations(
  suspectId: number,
): Promise<ApiResponse<Interrogation[]>> {
  return apiGet<Interrogation[]>(API.suspectInterrogations(suspectId));
}

export function createInterrogation(
  suspectId: number,
  data: Omit<InterrogationCreateRequest, "suspect">,
): Promise<ApiResponse<Interrogation>> {
  return apiPost<Interrogation>(API.suspectInterrogations(suspectId), data);
}

// ---------------------------------------------------------------------------
// Trials (nested under suspect)
// ---------------------------------------------------------------------------

export function fetchTrials(
  suspectId: number,
): Promise<ApiResponse<Trial[]>> {
  return apiGet<Trial[]>(API.suspectTrials(suspectId));
}

export function createTrial(
  suspectId: number,
  data: Omit<TrialCreateRequest, "suspect">,
): Promise<ApiResponse<Trial>> {
  return apiPost<Trial>(API.suspectTrials(suspectId), data);
}

// ---------------------------------------------------------------------------
// Bails (nested under suspect)
// ---------------------------------------------------------------------------

export function fetchBails(
  suspectId: number,
): Promise<ApiResponse<Bail[]>> {
  return apiGet<Bail[]>(API.suspectBails(suspectId));
}

export function createBail(
  suspectId: number,
  data: Omit<BailCreateRequest, "suspect">,
): Promise<ApiResponse<Bail>> {
  return apiPost<Bail>(API.suspectBails(suspectId), data);
}

// ---------------------------------------------------------------------------
// Most Wanted
// ---------------------------------------------------------------------------

/** Fetch public most-wanted list (ranked by score). */
export function fetchMostWanted(): Promise<ApiResponse<MostWantedEntry[]>> {
  return apiGet<MostWantedEntry[]>(API.MOST_WANTED);
}

// ---------------------------------------------------------------------------
// Bounty Tips — List / Detail
// ---------------------------------------------------------------------------

/** List bounty tips (role-scoped on backend). */
export function fetchBountyTips(
  filters: BountyTipFilters = {},
): Promise<ApiResponse<BountyTipListItem[]>> {
  return apiGet<BountyTipListItem[]>(`${API.BOUNTY_TIPS}${buildQuery(filters)}`);
}

/** Fetch a single bounty tip detail. */
export function fetchBountyTipDetail(id: number): Promise<ApiResponse<BountyTip>> {
  return apiGet<BountyTip>(API.bountyTip(id));
}

// ---------------------------------------------------------------------------
// Bounty Tips — Create / Review / Verify
// ---------------------------------------------------------------------------

/** Submit a new bounty tip (citizen). */
export function createBountyTip(
  data: BountyTipCreateRequest,
): Promise<ApiResponse<BountyTip>> {
  return apiPost<BountyTip>(API.BOUNTY_TIPS, data);
}

/** Officer reviews a bounty tip (accept / reject). */
export function reviewBountyTip(
  id: number,
  data: BountyTipReviewRequest,
): Promise<ApiResponse<BountyTip>> {
  return apiPost<BountyTip>(API.bountyTipReview(id), data);
}

/** Detective verifies a bounty tip (verify / reject). */
export function verifyBountyTip(
  id: number,
  data: BountyTipVerifyRequest,
): Promise<ApiResponse<BountyTip>> {
  return apiPost<BountyTip>(API.bountyTipVerify(id), data);
}

// ---------------------------------------------------------------------------
// Reward Lookup
// ---------------------------------------------------------------------------

/** Look up bounty reward by national ID + unique code. */
export function lookupReward(
  data: BountyVerifyLookupRequest,
): Promise<ApiResponse<BountyVerifyLookupResponse>> {
  return apiPost<BountyVerifyLookupResponse>(API.BOUNTY_REWARD_LOOKUP, data);
}

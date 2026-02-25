/**
 * Suspects & Bounty Tips API service.
 *
 * All suspect/bounty-related API calls — most wanted listing,
 * bounty tip CRUD, officer review, detective verification,
 * and reward lookup.
 */

import { apiGet, apiPost } from "./client";
import type { ApiResponse } from "./client";
import { API } from "./endpoints";
import type {
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
// Most Wanted
// ---------------------------------------------------------------------------

/** Fetch public most-wanted list (ranked by score). */
export function fetchMostWanted(): Promise<ApiResponse<MostWantedEntry[]>> {
  return apiGet<MostWantedEntry[]>(API.MOST_WANTED);
}

// ---------------------------------------------------------------------------
// Bounty Tips — List / Detail
// ---------------------------------------------------------------------------

export interface BountyTipFilters {
  status?: string;
  search?: string;
}

function buildQuery(filters: BountyTipFilters): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "" && value !== null) {
      params.set(key, String(value));
    }
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

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

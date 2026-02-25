/**
 * React Query hooks for Most Wanted & Bounty Tips.
 *
 * Provides:
 *   - useMostWanted       — fetch ranked most-wanted list
 *   - useBountyTips       — list bounty tips with filters
 *   - useBountyTipDetail  — single tip detail
 *   - useBountyTipActions — mutations for create, review, verify, lookup
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as suspectsApi from "../api/suspects";
import type { BountyTipFilters } from "../api/suspects";
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
// Query keys
// ---------------------------------------------------------------------------

export const MOST_WANTED_KEY = ["most-wanted"] as const;
export const BOUNTY_TIPS_KEY = ["bounty-tips"] as const;
export const bountyTipDetailKey = (id: number) => ["bounty-tips", id] as const;

// ---------------------------------------------------------------------------
// Most Wanted
// ---------------------------------------------------------------------------

export function useMostWanted() {
  return useQuery<MostWantedEntry[]>({
    queryKey: [...MOST_WANTED_KEY],
    queryFn: async () => {
      const res = await suspectsApi.fetchMostWanted();
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    staleTime: 60_000,
  });
}

// ---------------------------------------------------------------------------
// Bounty Tips — List
// ---------------------------------------------------------------------------

export function useBountyTips(filters: BountyTipFilters = {}) {
  return useQuery<BountyTipListItem[]>({
    queryKey: [...BOUNTY_TIPS_KEY, filters],
    queryFn: async () => {
      const res = await suspectsApi.fetchBountyTips(filters);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    staleTime: 30_000,
  });
}

// ---------------------------------------------------------------------------
// Bounty Tips — Detail
// ---------------------------------------------------------------------------

export function useBountyTipDetail(id: number | undefined) {
  return useQuery<BountyTip>({
    queryKey: bountyTipDetailKey(id!),
    queryFn: async () => {
      const res = await suspectsApi.fetchBountyTipDetail(id!);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    enabled: id !== undefined,
    staleTime: 15_000,
  });
}

// ---------------------------------------------------------------------------
// Bounty Tips — Mutations
// ---------------------------------------------------------------------------

export function useBountyTipActions() {
  const qc = useQueryClient();

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: BOUNTY_TIPS_KEY });
  };

  const createTip = useMutation<BountyTip, Error, BountyTipCreateRequest>({
    mutationFn: async (data) => {
      const res = await suspectsApi.createBountyTip(data);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: invalidate,
  });

  const reviewTip = useMutation<
    BountyTip,
    Error,
    { id: number; data: BountyTipReviewRequest }
  >({
    mutationFn: async ({ id, data }) => {
      const res = await suspectsApi.reviewBountyTip(id, data);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: invalidate,
  });

  const verifyTip = useMutation<
    BountyTip,
    Error,
    { id: number; data: BountyTipVerifyRequest }
  >({
    mutationFn: async ({ id, data }) => {
      const res = await suspectsApi.verifyBountyTip(id, data);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: invalidate,
  });

  const lookupReward = useMutation<
    BountyVerifyLookupResponse,
    Error,
    BountyVerifyLookupRequest
  >({
    mutationFn: async (data) => {
      const res = await suspectsApi.lookupReward(data);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
  });

  return { createTip, reviewTip, verifyTip, lookupReward };
}

/**
 * React Query hooks for Suspects, Interrogations, Trials, Bails,
 * Most Wanted & Bounty Tips.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as suspectsApi from "../api/suspects";
import type { SuspectFilters, BountyTipFilters } from "../api/suspects";
import type {
  Suspect,
  SuspectCreateRequest,
  Interrogation,
  Trial,
  Bail,
  MostWantedEntry,
  BountyTipListItem,
  BountyTip,
  BountyTipCreateRequest,
  BountyTipReviewRequest,
  BountyTipVerifyRequest,
  BountyVerifyLookupRequest,
  BountyVerifyLookupResponse,
} from "../types";
import { CASES_QUERY_KEY } from "./useCases";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const SUSPECTS_QUERY_KEY = ["suspects"] as const;
export const suspectDetailKey = (id: number) => ["suspects", id] as const;
export const suspectInterrogationsKey = (id: number) => ["suspects", id, "interrogations"] as const;
export const suspectTrialsKey = (id: number) => ["suspects", id, "trials"] as const;
export const suspectBailsKey = (id: number) => ["suspects", id, "bails"] as const;
export const MOST_WANTED_KEY = ["most-wanted"] as const;
export const BOUNTY_TIPS_KEY = ["bounty-tips"] as const;
export const bountyTipDetailKey = (id: number) => ["bounty-tips", id] as const;

// ---------------------------------------------------------------------------
// Suspects — List (per-case)
// ---------------------------------------------------------------------------

export function useCaseSuspects(caseId: number | undefined, extra: Omit<SuspectFilters, "case"> = {}) {
  return useQuery<Suspect[]>({
    queryKey: [...SUSPECTS_QUERY_KEY, { case: caseId, ...extra }],
    queryFn: async () => {
      const res = await suspectsApi.fetchSuspects({ case: caseId!, ...extra });
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    enabled: caseId !== undefined,
    staleTime: 15_000,
  });
}

// ---------------------------------------------------------------------------
// Suspects — Detail
// ---------------------------------------------------------------------------

export function useSuspectDetail(id: number | undefined) {
  return useQuery<Suspect>({
    queryKey: suspectDetailKey(id!),
    queryFn: async () => {
      const res = await suspectsApi.fetchSuspectDetail(id!);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    enabled: id !== undefined,
    staleTime: 15_000,
  });
}

// ---------------------------------------------------------------------------
// Interrogations — List
// ---------------------------------------------------------------------------

export function useSuspectInterrogations(suspectId: number | undefined) {
  return useQuery<Interrogation[]>({
    queryKey: suspectInterrogationsKey(suspectId!),
    queryFn: async () => {
      const res = await suspectsApi.fetchInterrogations(suspectId!);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    enabled: suspectId !== undefined,
    staleTime: 15_000,
  });
}

// ---------------------------------------------------------------------------
// Trials — List
// ---------------------------------------------------------------------------

export function useSuspectTrials(suspectId: number | undefined) {
  return useQuery<Trial[]>({
    queryKey: suspectTrialsKey(suspectId!),
    queryFn: async () => {
      const res = await suspectsApi.fetchTrials(suspectId!);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    enabled: suspectId !== undefined,
    staleTime: 15_000,
  });
}

// ---------------------------------------------------------------------------
// Bails — List
// ---------------------------------------------------------------------------

export function useSuspectBails(suspectId: number | undefined) {
  return useQuery<Bail[]>({
    queryKey: suspectBailsKey(suspectId!),
    queryFn: async () => {
      const res = await suspectsApi.fetchBails(suspectId!);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    enabled: suspectId !== undefined,
    staleTime: 15_000,
  });
}

// ---------------------------------------------------------------------------
// Create suspect
// ---------------------------------------------------------------------------

export function useCreateSuspect() {
  const qc = useQueryClient();
  return useMutation<Suspect, Error, SuspectCreateRequest | FormData>({
    mutationFn: async (data) => {
      const res = await suspectsApi.createSuspect(data);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: SUSPECTS_QUERY_KEY });
      qc.invalidateQueries({ queryKey: CASES_QUERY_KEY });
    },
  });
}

// ---------------------------------------------------------------------------
// Suspect workflow actions
// ---------------------------------------------------------------------------

export function useSuspectActions(suspectId: number, caseId?: number) {
  const qc = useQueryClient();

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: SUSPECTS_QUERY_KEY });
    qc.invalidateQueries({ queryKey: suspectDetailKey(suspectId) });
    if (caseId) qc.invalidateQueries({ queryKey: ["cases", caseId] });
    qc.invalidateQueries({ queryKey: CASES_QUERY_KEY });
  };

  const approve = useMutation({
    mutationFn: (data: suspectsApi.ApproveRequest) =>
      suspectsApi.approveSuspect(suspectId, data).then(throwOnErr),
    onSuccess: invalidate,
  });

  const arrest = useMutation({
    mutationFn: (data: suspectsApi.ArrestRequest) =>
      suspectsApi.arrestSuspect(suspectId, data).then(throwOnErr),
    onSuccess: invalidate,
  });

  const captainVerdict = useMutation({
    mutationFn: (data: suspectsApi.CaptainVerdictRequest) =>
      suspectsApi.submitCaptainVerdict(suspectId, data).then(throwOnErr),
    onSuccess: invalidate,
  });

  const chiefApproval = useMutation({
    mutationFn: (data: suspectsApi.ChiefApprovalRequest) =>
      suspectsApi.submitChiefApproval(suspectId, data).then(throwOnErr),
    onSuccess: invalidate,
  });

  const updateSuspect = useMutation({
    mutationFn: (data: Partial<SuspectCreateRequest>) =>
      suspectsApi.updateSuspect(suspectId, data).then(throwOnErr),
    onSuccess: invalidate,
  });

  const createInterrogation = useMutation({
    mutationFn: (data: { case: number; detective_guilt_score: number; sergeant_guilt_score: number; notes?: string }) =>
      suspectsApi.createInterrogation(suspectId, data).then(throwOnErr),
    onSuccess: () => {
      invalidate();
      qc.invalidateQueries({ queryKey: suspectInterrogationsKey(suspectId) });
    },
  });

  const createTrial = useMutation({
    mutationFn: (data: { case: number; verdict: "guilty" | "innocent"; punishment_title?: string; punishment_description?: string }) =>
      suspectsApi.createTrial(suspectId, data).then(throwOnErr),
    onSuccess: () => {
      invalidate();
      qc.invalidateQueries({ queryKey: suspectTrialsKey(suspectId) });
    },
  });

  const createBail = useMutation({
    mutationFn: (data: { case: number; amount: number; conditions?: string }) =>
      suspectsApi.createBail(suspectId, data).then(throwOnErr),
    onSuccess: () => {
      invalidate();
      qc.invalidateQueries({ queryKey: suspectBailsKey(suspectId) });
    },
  });

  return {
    approve,
    arrest,
    captainVerdict,
    chiefApproval,
    updateSuspect,
    createInterrogation,
    createTrial,
    createBail,
  };
}

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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function throwOnErr<T>(res: { ok: boolean; data?: T; error?: { message: string } }): T {
  if (!res.ok) {
    throw new Error((res as { error: { message: string } }).error.message);
  }
  return (res as { data: T }).data;
}

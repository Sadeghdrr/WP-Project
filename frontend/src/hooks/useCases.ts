/**
 * React Query hooks for cases.
 *
 * Provides:
 *   - useCases        — list cases with filters
 *   - useCaseDetail   — fetch single case detail
 *   - useCaseMutation — generic mutation helper for workflow actions
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { CaseFilters } from "../api/cases";
import * as casesApi from "../api/cases";
import type {
  CaseDetail,
  CaseListItem,
  CaseCreateComplaintRequest,
  CaseCreateCrimeSceneRequest,
  ReviewDecisionRequest,
  ResubmitComplaintRequest,
  CaseGenericTransitionRequest,
  AssignPersonnelRequest,
  CaseComplainant,
} from "../types";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const CASES_QUERY_KEY = ["cases"] as const;
export const caseDetailKey = (id: number) => ["cases", id] as const;

// ---------------------------------------------------------------------------
// List
// ---------------------------------------------------------------------------

export function useCases(filters: CaseFilters = {}) {
  return useQuery<CaseListItem[]>({
    queryKey: [...CASES_QUERY_KEY, filters],
    queryFn: async () => {
      const res = await casesApi.fetchCases(filters);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    staleTime: 30_000,
  });
}

// ---------------------------------------------------------------------------
// Detail
// ---------------------------------------------------------------------------

export function useCaseDetail(id: number | undefined) {
  return useQuery<CaseDetail>({
    queryKey: caseDetailKey(id!),
    queryFn: async () => {
      const res = await casesApi.fetchCaseDetail(id!);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    enabled: id !== undefined,
    staleTime: 15_000,
  });
}

// ---------------------------------------------------------------------------
// Create mutations
// ---------------------------------------------------------------------------

export function useCreateComplaintCase() {
  const qc = useQueryClient();
  return useMutation<CaseDetail, Error, CaseCreateComplaintRequest>({
    mutationFn: async (data) => {
      const res = await casesApi.createComplaintCase(data);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: CASES_QUERY_KEY });
    },
  });
}

export function useCreateCrimeSceneCase() {
  const qc = useQueryClient();
  return useMutation<CaseDetail, Error, CaseCreateCrimeSceneRequest>({
    mutationFn: async (data) => {
      const res = await casesApi.createCrimeSceneCase(data);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: CASES_QUERY_KEY });
    },
  });
}

// ---------------------------------------------------------------------------
// Workflow mutations
// ---------------------------------------------------------------------------

/**
 * Hook that returns mutation functions for every case workflow action.
 * After each successful mutation, invalidates both case list and detail queries.
 */
export function useCaseActions(caseId: number) {
  const qc = useQueryClient();

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: CASES_QUERY_KEY });
    qc.invalidateQueries({ queryKey: caseDetailKey(caseId) });
  };

  const submitForReview = useMutation({
    mutationFn: () => casesApi.submitForReview(caseId).then(throwOnError),
    onSuccess: invalidate,
  });

  const resubmitComplaint = useMutation({
    mutationFn: (data: ResubmitComplaintRequest) =>
      casesApi.resubmitComplaint(caseId, data).then(throwOnError),
    onSuccess: invalidate,
  });

  const cadetReview = useMutation({
    mutationFn: (data: ReviewDecisionRequest) =>
      casesApi.cadetReview(caseId, data).then(throwOnError),
    onSuccess: invalidate,
  });

  const officerReview = useMutation({
    mutationFn: (data: ReviewDecisionRequest) =>
      casesApi.officerReview(caseId, data).then(throwOnError),
    onSuccess: invalidate,
  });

  const approveCrimeScene = useMutation({
    mutationFn: () => casesApi.approveCrimeScene(caseId).then(throwOnError),
    onSuccess: invalidate,
  });

  const transitionCase = useMutation({
    mutationFn: (data: CaseGenericTransitionRequest) =>
      casesApi.transitionCase(caseId, data).then(throwOnError),
    onSuccess: invalidate,
  });

  const assignDetective = useMutation({
    mutationFn: (data: AssignPersonnelRequest) =>
      casesApi.assignDetective(caseId, data).then(throwOnError),
    onSuccess: invalidate,
  });

  const assignSergeant = useMutation({
    mutationFn: (data: AssignPersonnelRequest) =>
      casesApi.assignSergeant(caseId, data).then(throwOnError),
    onSuccess: invalidate,
  });

  const assignCaptain = useMutation({
    mutationFn: (data: AssignPersonnelRequest) =>
      casesApi.assignCaptain(caseId, data).then(throwOnError),
    onSuccess: invalidate,
  });

  const assignJudge = useMutation({
    mutationFn: (data: AssignPersonnelRequest) =>
      casesApi.assignJudge(caseId, data).then(throwOnError),
    onSuccess: invalidate,
  });

  return {
    submitForReview,
    resubmitComplaint,
    cadetReview,
    officerReview,
    approveCrimeScene,
    transitionCase,
    assignDetective,
    assignSergeant,
    assignCaptain,
    assignJudge,
  };
}

// ---------------------------------------------------------------------------
// Complainant mutations
// ---------------------------------------------------------------------------

export function useComplainantMutations(caseId: number) {
  const qc = useQueryClient();

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: caseDetailKey(caseId) });
  };

  const addComplainant = useMutation<CaseComplainant, Error, { user_id: number }>({
    mutationFn: async (data) => {
      const res = await casesApi.addComplainant(caseId, data);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: invalidate,
  });

  const reviewComplainant = useMutation<
    CaseComplainant,
    Error,
    { complainantId: number; decision: "approve" | "reject" }
  >({
    mutationFn: async ({ complainantId, decision }) => {
      const res = await casesApi.reviewComplainant(caseId, complainantId, { decision });
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: invalidate,
  });

  return { addComplainant, reviewComplainant };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function throwOnError<T>(res: { ok: boolean; data?: T; error?: { message: string } }): T {
  if (!res.ok) {
    throw new Error((res as { error: { message: string } }).error.message);
  }
  return (res as { data: T }).data;
}

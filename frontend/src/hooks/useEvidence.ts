/**
 * React Query hooks for evidence.
 *
 * Provides:
 *   - useEvidence        — list evidence with filters
 *   - useEvidenceDetail  — fetch single evidence detail
 *   - useEvidenceFiles   — files attached to an evidence item
 *   - useChainOfCustody  — chain-of-custody audit trail
 *   - useEvidenceActions — mutations for create/update/delete/verify/upload
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { EvidenceFilters } from "../api/evidence";
import * as evidenceApi from "../api/evidence";
import type {
  Evidence,
  EvidenceListItem,
  EvidenceCreateRequest,
  VerifyEvidenceRequest,
  EvidenceFile,
  EvidenceCustodyLog,
} from "../types";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const EVIDENCE_QUERY_KEY = ["evidence"] as const;
export const evidenceDetailKey = (id: number) => ["evidence", id] as const;
export const evidenceFilesKey = (id: number) => ["evidence", id, "files"] as const;
export const evidenceCustodyKey = (id: number) => ["evidence", id, "custody"] as const;

// ---------------------------------------------------------------------------
// List
// ---------------------------------------------------------------------------

export function useEvidence(filters: EvidenceFilters = {}) {
  return useQuery<EvidenceListItem[]>({
    queryKey: [...EVIDENCE_QUERY_KEY, filters],
    queryFn: async () => {
      const res = await evidenceApi.fetchEvidence(filters);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    staleTime: 30_000,
  });
}

// ---------------------------------------------------------------------------
// Detail
// ---------------------------------------------------------------------------

export function useEvidenceDetail(id: number | undefined) {
  return useQuery<Evidence>({
    queryKey: evidenceDetailKey(id!),
    queryFn: async () => {
      const res = await evidenceApi.fetchEvidenceDetail(id!);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    enabled: id !== undefined,
    staleTime: 15_000,
  });
}

// ---------------------------------------------------------------------------
// Files
// ---------------------------------------------------------------------------

export function useEvidenceFiles(evidenceId: number | undefined) {
  return useQuery<EvidenceFile[]>({
    queryKey: evidenceFilesKey(evidenceId!),
    queryFn: async () => {
      const res = await evidenceApi.fetchFiles(evidenceId!);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    enabled: evidenceId !== undefined,
    staleTime: 15_000,
  });
}

// ---------------------------------------------------------------------------
// Chain of custody
// ---------------------------------------------------------------------------

export function useChainOfCustody(evidenceId: number | undefined) {
  return useQuery<EvidenceCustodyLog[]>({
    queryKey: evidenceCustodyKey(evidenceId!),
    queryFn: async () => {
      const res = await evidenceApi.fetchChainOfCustody(evidenceId!);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    enabled: evidenceId !== undefined,
    staleTime: 30_000,
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function useEvidenceActions() {
  const qc = useQueryClient();

  const invalidateList = () => qc.invalidateQueries({ queryKey: EVIDENCE_QUERY_KEY });
  const invalidateDetail = (id: number) =>
    qc.invalidateQueries({ queryKey: evidenceDetailKey(id) });
  const invalidateFiles = (id: number) =>
    qc.invalidateQueries({ queryKey: evidenceFilesKey(id) });

  const createEvidence = useMutation<Evidence, Error, EvidenceCreateRequest>({
    mutationFn: async (data) => {
      const res = await evidenceApi.createEvidence(data);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => invalidateList(),
  });

  const updateEvidence = useMutation<
    Evidence,
    Error,
    { id: number; data: Partial<Record<string, unknown>> }
  >({
    mutationFn: async ({ id, data }) => {
      const res = await evidenceApi.updateEvidence(id, data);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: (_, vars) => {
      invalidateList();
      invalidateDetail(vars.id);
    },
  });

  const deleteEvidence = useMutation<void, Error, number>({
    mutationFn: async (id) => {
      const res = await evidenceApi.deleteEvidence(id);
      if (!res.ok) throw new Error(res.error.message);
    },
    onSuccess: () => invalidateList(),
  });

  const verifyEvidence = useMutation<
    Evidence,
    Error,
    { id: number; data: VerifyEvidenceRequest }
  >({
    mutationFn: async ({ id, data }) => {
      const res = await evidenceApi.verifyEvidence(id, data);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: (_, vars) => {
      invalidateList();
      invalidateDetail(vars.id);
    },
  });

  const uploadFile = useMutation<
    EvidenceFile,
    Error,
    { evidenceId: number; file: File; fileType: string; caption?: string }
  >({
    mutationFn: async ({ evidenceId, file, fileType, caption }) => {
      const res = await evidenceApi.uploadFile(evidenceId, file, fileType, caption);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: (_, vars) => {
      invalidateFiles(vars.evidenceId);
      invalidateDetail(vars.evidenceId);
    },
  });

  return {
    createEvidence,
    updateEvidence,
    deleteEvidence,
    verifyEvidence,
    uploadFile,
  };
}

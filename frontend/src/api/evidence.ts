/**
 * Evidence API service.
 *
 * All evidence-related API calls — list, detail, create, update, delete,
 * verification, file upload, chain-of-custody.
 */

import { apiGet, apiPost, apiPatch, apiDelete, apiPostForm } from "./client";
import type { ApiResponse } from "./client";
import { API } from "./endpoints";
import type {
  EvidenceListItem,
  Evidence,
  EvidenceCreateRequest,
  VerifyEvidenceRequest,
  LinkCaseRequest,
  UnlinkCaseRequest,
  EvidenceFile,
  EvidenceCustodyLog,
} from "../types";

// ---------------------------------------------------------------------------
// Query params helper
// ---------------------------------------------------------------------------

export interface EvidenceFilters {
  evidence_type?: string;
  case?: number;
  registered_by?: number;
  is_verified?: boolean;
  search?: string;
  created_after?: string;
  created_before?: string;
}

function buildQuery(filters: EvidenceFilters): string {
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
// List / Detail / CRUD
// ---------------------------------------------------------------------------

export function fetchEvidence(
  filters: EvidenceFilters = {},
): Promise<ApiResponse<EvidenceListItem[]>> {
  return apiGet<EvidenceListItem[]>(`${API.EVIDENCE}${buildQuery(filters)}`);
}

export function fetchEvidenceDetail(id: number): Promise<ApiResponse<Evidence>> {
  return apiGet<Evidence>(API.evidence(id));
}

export function createEvidence(
  data: EvidenceCreateRequest,
): Promise<ApiResponse<Evidence>> {
  return apiPost<Evidence>(API.EVIDENCE, data);
}

export function updateEvidence(
  id: number,
  data: Partial<Record<string, unknown>>,
): Promise<ApiResponse<Evidence>> {
  return apiPatch<Evidence>(API.evidence(id), data);
}

export function deleteEvidence(id: number): Promise<ApiResponse<void>> {
  return apiDelete<void>(API.evidence(id));
}

// ---------------------------------------------------------------------------
// Verification (Coroner workflow)
// ---------------------------------------------------------------------------

export function verifyEvidence(
  id: number,
  data: VerifyEvidenceRequest,
): Promise<ApiResponse<Evidence>> {
  return apiPost<Evidence>(API.EVIDENCE_VERIFY(id), data);
}

// ---------------------------------------------------------------------------
// Case linking
// ---------------------------------------------------------------------------

export function linkCase(
  id: number,
  data: LinkCaseRequest,
): Promise<ApiResponse<Evidence>> {
  return apiPost<Evidence>(API.EVIDENCE_LINK_CASE(id), data);
}

export function unlinkCase(
  id: number,
  data: UnlinkCaseRequest,
): Promise<ApiResponse<Evidence>> {
  return apiPost<Evidence>(API.EVIDENCE_UNLINK_CASE(id), data);
}

// ---------------------------------------------------------------------------
// File management
// ---------------------------------------------------------------------------

export function fetchFiles(evidenceId: number): Promise<ApiResponse<EvidenceFile[]>> {
  return apiGet<EvidenceFile[]>(API.EVIDENCE_FILES(evidenceId));
}

export function uploadFile(
  evidenceId: number,
  file: File,
  fileType: string,
  caption?: string,
): Promise<ApiResponse<EvidenceFile>> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("file_type", fileType);
  if (caption) formData.append("caption", caption);
  return apiPostForm<EvidenceFile>(API.EVIDENCE_FILES(evidenceId), formData);
}

// ---------------------------------------------------------------------------
// Chain of custody
// ---------------------------------------------------------------------------

export function fetchChainOfCustody(
  evidenceId: number,
): Promise<ApiResponse<EvidenceCustodyLog[]>> {
  return apiGet<EvidenceCustodyLog[]>(API.EVIDENCE_CHAIN_OF_CUSTODY(evidenceId));
}

/**
 * Cases API — mirrors backend cases app endpoints.
 * Base path: /api/cases/
 *
 * Endpoints from backend cases/urls.py and CaseViewSet.
 */

import { apiClient } from './api.client';
import type {
  Case,
  CaseListItem,
  CaseComplainant,
  CaseStatusLog,
  ComplaintCaseCreateRequest,
  ResubmitComplaintRequest,
  ReviewDecisionRequest,
  AddComplainantRequest,
  ComplainantReviewRequest,
} from '../../types/case.types';

type CaseFilterParams = {
  status?: string;
  crime_level?: number;
  detective?: number;
  creation_type?: string;
  created_after?: string;
  created_before?: string;
  search?: string;
};

/** Paginated response from DRF (when pagination is enabled) */
interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * GET /api/cases/
 * List cases visible to the authenticated user, with optional filters.
 */
export async function listCases(params?: CaseFilterParams): Promise<CaseListItem[]> {
  const { data } = await apiClient.get<CaseListItem[] | PaginatedResponse<CaseListItem>>(
    '/cases/',
    { params }
  );
  return Array.isArray(data) ? data : data.results;
}

/**
 * POST /api/cases/
 * Create a case via complaint path.
 * Request body must include creation_type: "complaint".
 */
export async function createComplaintCase(
  payload: ComplaintCaseCreateRequest
): Promise<Case> {
  const { data } = await apiClient.post<Case>('/cases/', {
    ...payload,
    creation_type: 'complaint',
  });
  return data;
}

/**
 * GET /api/cases/{id}/
 * Full case detail with nested complainants, witnesses, status log, calculations.
 */
export async function getCaseDetail(id: number): Promise<Case> {
  const { data } = await apiClient.get<Case>(`/cases/${id}/`);
  return data;
}

/**
 * PATCH /api/cases/{id}/
 * Partial update of mutable metadata fields.
 */
export async function updateCase(
  id: number,
  payload: Partial<ResubmitComplaintRequest>
): Promise<Case> {
  const { data } = await apiClient.patch<Case>(`/cases/${id}/`, payload);
  return data;
}

/**
 * POST /api/cases/{id}/submit/
 * Complainant submits draft for Cadet review.
 * COMPLAINT_REGISTERED → CADET_REVIEW
 */
export async function submitForReview(id: number): Promise<Case> {
  const { data } = await apiClient.post<Case>(`/cases/${id}/submit/`);

  return data;
}

/**
 * POST /api/cases/{id}/resubmit/
 * Complainant edits and re-submits a returned complaint.
 * RETURNED_TO_COMPLAINANT → CADET_REVIEW
 */
export async function resubmitComplaint(
  id: number,
  payload: ResubmitComplaintRequest
): Promise<Case> {
  const { data } = await apiClient.post<Case>(`/cases/${id}/resubmit/`, payload);
  return data;
}

/**
 * POST /api/cases/{id}/cadet-review/
 * Cadet approves or rejects a complaint case.
 */
export async function cadetReview(
  id: number,
  payload: ReviewDecisionRequest
): Promise<Case> {
  const { data } = await apiClient.post<Case>(`/cases/${id}/cadet-review/`, payload);
  return data;
}

/**
 * POST /api/cases/{id}/officer-review/
 * Officer approves or rejects a case forwarded by the Cadet.
 */
export async function officerReview(
  id: number,
  payload: ReviewDecisionRequest
): Promise<Case> {
  const { data } = await apiClient.post<Case>(`/cases/${id}/officer-review/`, payload);
  return data;
}

/**
 * GET /api/cases/{id}/complainants/
 * List all complainants on the case.
 */
export async function listComplainants(id: number): Promise<CaseComplainant[]> {
  const { data } = await apiClient.get<CaseComplainant[]>(`/cases/${id}/complainants/`);
  return data;
}

/**
 * POST /api/cases/{id}/complainants/
 * Add an additional complainant.
 */
export async function addComplainant(
  id: number,
  payload: AddComplainantRequest
): Promise<CaseComplainant> {
  const { data } = await apiClient.post<CaseComplainant>(
    `/cases/${id}/complainants/`,
    payload
  );
  return data;
}

/**
 * POST /api/cases/{id}/complainants/{complainant_pk}/review/
 * Cadet approves or rejects an individual complainant.
 */
export async function reviewComplainant(
  caseId: number,
  complainantId: number,
  payload: ComplainantReviewRequest
): Promise<CaseComplainant> {
  const { data } = await apiClient.post<CaseComplainant>(
    `/cases/${caseId}/complainants/${complainantId}/review/`,
    payload
  );
  return data;
}

/**
 * GET /api/cases/{id}/status-log/
 * Immutable audit trail of all status transitions.
 */
export async function getStatusLog(id: number): Promise<CaseStatusLog[]> {
  const { data } = await apiClient.get<CaseStatusLog[]>(`/cases/${id}/status-log/`);
  return data;
}

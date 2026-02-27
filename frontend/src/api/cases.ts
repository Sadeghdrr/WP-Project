/**
 * Cases API service.
 *
 * All case-related API calls — list, detail, workflow actions,
 * assignments, complainants, witnesses, status log.
 */

import { apiGet, apiPost, apiPatch, apiDelete } from "./client";
import type { ApiResponse } from "./client";
import { API } from "./endpoints";
import type {
  CaseListItem,
  CaseDetail,
  CaseReport,
  CaseCreateComplaintRequest,
  CaseCreateCrimeSceneRequest,
  ReviewDecisionRequest,
  ResubmitComplaintRequest,
  CaseGenericTransitionRequest,
  AssignPersonnelRequest,
  CaseStatusLog,
} from "../types";

// ---------------------------------------------------------------------------
// Query params helper
// ---------------------------------------------------------------------------

export interface CaseFilters {
  status?: string;
  crime_level?: number;
  creation_type?: string;
  detective?: number;
  created_after?: string;
  created_before?: string;
  search?: string;
}

function buildQuery(filters: CaseFilters): string {
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

export function fetchCases(filters: CaseFilters = {}): Promise<ApiResponse<CaseListItem[]>> {
  return apiGet<CaseListItem[]>(`${API.CASES}${buildQuery(filters)}`);
}

export function fetchCaseDetail(id: number): Promise<ApiResponse<CaseDetail>> {
  return apiGet<CaseDetail>(API.case(id));
}

export function createComplaintCase(
  data: CaseCreateComplaintRequest,
): Promise<ApiResponse<CaseDetail>> {
  return apiPost<CaseDetail>(API.CASES, {
    ...data,
    creation_type: "complaint",
  });
}

export function createCrimeSceneCase(
  data: CaseCreateCrimeSceneRequest,
): Promise<ApiResponse<CaseDetail>> {
  return apiPost<CaseDetail>(API.CASES, {
    ...data,
    creation_type: "crime_scene",
  });
}

export function updateCase(
  id: number,
  data: Partial<{ title: string; description: string; incident_date: string; location: string }>,
): Promise<ApiResponse<CaseDetail>> {
  return apiPatch<CaseDetail>(API.case(id), data);
}

export function deleteCase(id: number): Promise<ApiResponse<void>> {
  return apiDelete<void>(API.case(id));
}

// ---------------------------------------------------------------------------
// Workflow actions
// ---------------------------------------------------------------------------

/** Complainant submits draft for cadet review */
export function submitForReview(caseId: number): Promise<ApiResponse<CaseDetail>> {
  return apiPost<CaseDetail>(API.CASE_SUBMIT(caseId));
}

/** Complainant re-submits returned complaint */
export function resubmitComplaint(
  caseId: number,
  data: ResubmitComplaintRequest,
): Promise<ApiResponse<CaseDetail>> {
  return apiPost<CaseDetail>(API.CASE_RESUBMIT(caseId), data);
}

/** Cadet approves/rejects complaint */
export function cadetReview(
  caseId: number,
  data: ReviewDecisionRequest,
): Promise<ApiResponse<CaseDetail>> {
  return apiPost<CaseDetail>(API.CASE_CADET_REVIEW(caseId), data);
}

/** Officer approves/rejects case */
export function officerReview(
  caseId: number,
  data: ReviewDecisionRequest,
): Promise<ApiResponse<CaseDetail>> {
  return apiPost<CaseDetail>(API.CASE_OFFICER_REVIEW(caseId), data);
}

/** Superior approves crime-scene case */
export function approveCrimeScene(caseId: number): Promise<ApiResponse<CaseDetail>> {
  return apiPost<CaseDetail>(API.CASE_APPROVE_CRIME_SCENE(caseId));
}

/** Generic state transition */
export function transitionCase(
  caseId: number,
  data: CaseGenericTransitionRequest,
): Promise<ApiResponse<CaseDetail>> {
  return apiPost<CaseDetail>(API.CASE_TRANSITION(caseId), data);
}

// ---------------------------------------------------------------------------
// Assignments
// ---------------------------------------------------------------------------

export function assignDetective(
  caseId: number,
  data: AssignPersonnelRequest,
): Promise<ApiResponse<CaseDetail>> {
  return apiPost<CaseDetail>(API.CASE_ASSIGN_DETECTIVE(caseId), data);
}

export function unassignDetective(caseId: number): Promise<ApiResponse<CaseDetail>> {
  return apiDelete<CaseDetail>(API.CASE_UNASSIGN_DETECTIVE(caseId));
}

export function assignSergeant(
  caseId: number,
  data: AssignPersonnelRequest,
): Promise<ApiResponse<CaseDetail>> {
  return apiPost<CaseDetail>(API.CASE_ASSIGN_SERGEANT(caseId), data);
}

export function assignCaptain(
  caseId: number,
  data: AssignPersonnelRequest,
): Promise<ApiResponse<CaseDetail>> {
  return apiPost<CaseDetail>(API.CASE_ASSIGN_CAPTAIN(caseId), data);
}

export function assignJudge(
  caseId: number,
  data: AssignPersonnelRequest,
): Promise<ApiResponse<CaseDetail>> {
  return apiPost<CaseDetail>(API.CASE_ASSIGN_JUDGE(caseId), data);
}

// ---------------------------------------------------------------------------
// Sub-resources
// ---------------------------------------------------------------------------

export function fetchStatusLog(caseId: number): Promise<ApiResponse<CaseStatusLog[]>> {
  return apiGet<CaseStatusLog[]>(API.CASE_STATUS_LOG(caseId));
}

// ---------------------------------------------------------------------------
// Report
// ---------------------------------------------------------------------------

export function fetchCaseReport(caseId: number): Promise<ApiResponse<CaseReport>> {
  return apiGet<CaseReport>(API.CASE_REPORT(caseId));
}

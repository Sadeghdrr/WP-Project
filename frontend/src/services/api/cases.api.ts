/**
 * Cases API service.
 */
import api from './axios.instance';
import type { PaginatedResponse, ListParams } from '@/types/api.types';
import type {
  CaseListItem,
  CaseDetail,
  CaseCreateRequest,
  CaseUpdateRequest,
  CaseStatusLog,
  CaseComplainant,
  CaseWitness,
  ComplainantCreateRequest,
  ComplainantReviewRequest,
  WitnessCreateRequest,
  CaseFilterParams,
} from '@/types/case.types';

type CaseListParams = ListParams & CaseFilterParams;

export const casesApi = {
  /* ── CRUD ───────────────────────────────────────────────────────── */
  list: (params?: CaseListParams) =>
    api
      .get<PaginatedResponse<CaseListItem>>('/cases/', { params })
      .then((r) => r.data),

  detail: (id: number) =>
    api.get<CaseDetail>(`/cases/${id}/`).then((r) => r.data),

  create: (data: CaseCreateRequest) =>
    api.post<CaseDetail>('/cases/', data).then((r) => r.data),

  update: (id: number, data: CaseUpdateRequest) =>
    api.patch<CaseDetail>(`/cases/${id}/`, data).then((r) => r.data),

  delete: (id: number) =>
    api.delete(`/cases/${id}/`).then((r) => r.data),

  /* ── Workflow transitions ───────────────────────────────────────── */
  submit: (id: number) =>
    api.post<CaseDetail>(`/cases/${id}/submit/`).then((r) => r.data),

  resubmit: (id: number, data?: { title?: string; description?: string; incident_date?: string; location?: string }) =>
    api.post<CaseDetail>(`/cases/${id}/resubmit/`, data).then((r) => r.data),

  cadetReview: (id: number, data: { decision: string; message?: string }) =>
    api.post<CaseDetail>(`/cases/${id}/cadet-review/`, data).then((r) => r.data),

  officerReview: (id: number, data: { decision: string; message?: string }) =>
    api.post<CaseDetail>(`/cases/${id}/officer-review/`, data).then((r) => r.data),

  approveCrimeScene: (id: number) =>
    api.post<CaseDetail>(`/cases/${id}/approve-crime-scene/`).then((r) => r.data),

  sergeantReview: (id: number, data: { decision: string; message?: string }) =>
    api.post<CaseDetail>(`/cases/${id}/sergeant-review/`, data).then((r) => r.data),

  declareSuspects: (id: number, data: { suspect_ids: number[] }) =>
    api.post<CaseDetail>(`/cases/${id}/declare-suspects/`, data).then((r) => r.data),

  forwardJudiciary: (id: number) =>
    api.post<CaseDetail>(`/cases/${id}/forward-judiciary/`).then((r) => r.data),

  transition: (id: number, data: { target_status: string; message?: string }) =>
    api.post<CaseDetail>(`/cases/${id}/transition/`, data).then((r) => r.data),

  /* ── Assignments ────────────────────────────────────────────────── */
  assignDetective: (id: number, data: { user_id: number }) =>
    api.post(`/cases/${id}/assign-detective/`, data).then((r) => r.data),

  unassignDetective: (id: number) =>
    api.delete(`/cases/${id}/unassign-detective/`).then((r) => r.data),

  assignSergeant: (id: number, data: { user_id: number }) =>
    api.post(`/cases/${id}/assign-sergeant/`, data).then((r) => r.data),

  assignCaptain: (id: number, data: { user_id: number }) =>
    api.post(`/cases/${id}/assign-captain/`, data).then((r) => r.data),

  assignJudge: (id: number, data: { user_id: number }) =>
    api.post(`/cases/${id}/assign-judge/`, data).then((r) => r.data),

  /* ── Sub-resources ──────────────────────────────────────────────── */
  statusLog: (id: number) =>
    api.get<CaseStatusLog[]>(`/cases/${id}/status-log/`).then((r) => r.data),

  report: (id: number) =>
    api.get(`/cases/${id}/report/`).then((r) => r.data),

  calculations: (id: number) =>
    api.get(`/cases/${id}/calculations/`).then((r) => r.data),

  complainants: (id: number) =>
    api.get<CaseComplainant[]>(`/cases/${id}/complainants/`).then((r) => r.data),

  addComplainant: (id: number, data: ComplainantCreateRequest) =>
    api.post<CaseComplainant>(`/cases/${id}/complainants/`, data).then((r) => r.data),

  reviewComplainant: (
    caseId: number,
    complainantId: number,
    data: ComplainantReviewRequest,
  ) =>
    api
      .post(`/cases/${caseId}/complainants/${complainantId}/review/`, data)
      .then((r) => r.data),

  witnesses: (id: number) =>
    api.get<CaseWitness[]>(`/cases/${id}/witnesses/`).then((r) => r.data),

  addWitness: (id: number, data: WitnessCreateRequest) =>
    api.post<CaseWitness>(`/cases/${id}/witnesses/`, data).then((r) => r.data),
};

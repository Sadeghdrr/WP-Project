/**
 * Evidence API service.
 */
import api from './axios.instance';
import type { PaginatedResponse, ListParams } from '@/types/api.types';
import type {
  EvidenceListItem,
  EvidenceDetail,
  EvidenceCreateRequest,
  EvidenceUpdateRequest,
  EvidenceVerifyRequest,
  EvidenceFile,
  EvidenceCustodyLog,
  EvidenceFilterParams,
} from '@/types/evidence.types';

type EvidenceListParams = ListParams & EvidenceFilterParams;

export const evidenceApi = {
  list: (params?: EvidenceListParams) =>
    api
      .get<PaginatedResponse<EvidenceListItem>>('/evidence/', { params })
      .then((r) => r.data),

  detail: (id: number) =>
    api.get<EvidenceDetail>(`/evidence/${id}/`).then((r) => r.data),

  create: (data: EvidenceCreateRequest) =>
    api.post<EvidenceDetail>('/evidence/', data).then((r) => r.data),

  update: (id: number, data: EvidenceUpdateRequest) =>
    api.patch<EvidenceDetail>(`/evidence/${id}/`, data).then((r) => r.data),

  delete: (id: number) =>
    api.delete(`/evidence/${id}/`).then((r) => r.data),

  /** Coroner verification */
  verify: (id: number, data: EvidenceVerifyRequest) =>
    api.post<EvidenceDetail>(`/evidence/${id}/verify/`, data).then((r) => r.data),

  /** File management */
  listFiles: (id: number) =>
    api.get<EvidenceFile[]>(`/evidence/${id}/files/`).then((r) => r.data),

  uploadFile: (id: number, formData: FormData) =>
    api
      .post<EvidenceFile>(`/evidence/${id}/files/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data),

  /** Chain of custody */
  chainOfCustody: (id: number) =>
    api
      .get<EvidenceCustodyLog[]>(`/evidence/${id}/chain-of-custody/`)
      .then((r) => r.data),

  /** Link / unlink to case */
  linkCase: (id: number, data: { case_id: number }) =>
    api.post(`/evidence/${id}/link-case/`, data).then((r) => r.data),

  unlinkCase: (id: number, data: { case_id: number }) =>
    api.post(`/evidence/${id}/unlink-case/`, data).then((r) => r.data),
};

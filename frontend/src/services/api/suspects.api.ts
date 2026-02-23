/**
 * Suspects, Interrogations, Trials, Bails & Bounty-Tips API service.
 */
import api from './axios.instance';
import type { PaginatedResponse, ListParams } from '@/types/api.types';
import type {
  SuspectListItem,
  SuspectDetail,
  SuspectCreateRequest,
  SuspectUpdateRequest,
  SuspectFilterParams,
  InterrogationListItem,
  InterrogationDetail,
  InterrogationCreateRequest,
  TrialListItem,
  TrialDetail,
  TrialCreateRequest,
  BailListItem,
  BailDetail,
  BailCreateRequest,
  BountyTipListItem,
  BountyTipDetail,
  BountyTipCreateRequest,
  BountyTipReviewRequest,
  BountyRewardLookupRequest,
} from '@/types/suspect.types';

type SuspectListParams = ListParams & SuspectFilterParams;

const BASE = '/suspects';

/* ── Suspects ────────────────────────────────────────────────────── */

export const suspectsApi = {
  list: (params?: SuspectListParams) =>
    api
      .get<PaginatedResponse<SuspectListItem>>(`${BASE}/suspects/`, { params })
      .then((r) => r.data),

  detail: (id: number) =>
    api.get<SuspectDetail>(`${BASE}/suspects/${id}/`).then((r) => r.data),

  create: (data: SuspectCreateRequest | FormData) =>
    api
      .post<SuspectDetail>(`${BASE}/suspects/`, data, {
        headers:
          data instanceof FormData
            ? { 'Content-Type': 'multipart/form-data' }
            : undefined,
      })
      .then((r) => r.data),

  update: (id: number, data: SuspectUpdateRequest | FormData) =>
    api
      .patch<SuspectDetail>(`${BASE}/suspects/${id}/`, data, {
        headers:
          data instanceof FormData
            ? { 'Content-Type': 'multipart/form-data' }
            : undefined,
      })
      .then((r) => r.data),

  /** Workflow actions */
  approve: (id: number) =>
    api.post(`${BASE}/suspects/${id}/approve/`).then((r) => r.data),

  arrest: (id: number, data?: { arrest_location?: string }) =>
    api.post(`${BASE}/suspects/${id}/arrest/`, data).then((r) => r.data),

  issueWarrant: (id: number, data: { reason: string; priority?: string }) =>
    api.post(`${BASE}/suspects/${id}/issue-warrant/`, data).then((r) => r.data),

  captainVerdict: (id: number, data: { verdict: string; notes?: string }) =>
    api.post(`${BASE}/suspects/${id}/captain-verdict/`, data).then((r) => r.data),

  chiefApproval: (id: number, data: { action: string }) =>
    api.post(`${BASE}/suspects/${id}/chief-approval/`, data).then((r) => r.data),

  transitionStatus: (id: number, data: { status: string }) =>
    api.post(`${BASE}/suspects/${id}/transition-status/`, data).then((r) => r.data),

  /** Most wanted list (public) */
  mostWanted: () =>
    api.get<SuspectListItem[]>(`${BASE}/suspects/most-wanted/`).then((r) => r.data),
};

/* ── Interrogations ──────────────────────────────────────────────── */

export const interrogationsApi = {
  list: (suspectId: number) =>
    api
      .get<InterrogationListItem[]>(
        `${BASE}/suspects/${suspectId}/interrogations/`,
      )
      .then((r) => r.data),

  detail: (suspectId: number, id: number) =>
    api
      .get<InterrogationDetail>(
        `${BASE}/suspects/${suspectId}/interrogations/${id}/`,
      )
      .then((r) => r.data),

  create: (suspectId: number, data: InterrogationCreateRequest) =>
    api
      .post<InterrogationDetail>(
        `${BASE}/suspects/${suspectId}/interrogations/`,
        data,
      )
      .then((r) => r.data),
};

/* ── Trials ──────────────────────────────────────────────────────── */

export const trialsApi = {
  list: (suspectId: number) =>
    api
      .get<TrialListItem[]>(`${BASE}/suspects/${suspectId}/trials/`)
      .then((r) => r.data),

  detail: (suspectId: number, id: number) =>
    api
      .get<TrialDetail>(`${BASE}/suspects/${suspectId}/trials/${id}/`)
      .then((r) => r.data),

  create: (suspectId: number, data: TrialCreateRequest) =>
    api
      .post<TrialDetail>(`${BASE}/suspects/${suspectId}/trials/`, data)
      .then((r) => r.data),
};

/* ── Bails ───────────────────────────────────────────────────────── */

export const bailsApi = {
  list: (suspectId: number) =>
    api
      .get<BailListItem[]>(`${BASE}/suspects/${suspectId}/bails/`)
      .then((r) => r.data),

  detail: (suspectId: number, id: number) =>
    api
      .get<BailDetail>(`${BASE}/suspects/${suspectId}/bails/${id}/`)
      .then((r) => r.data),

  create: (suspectId: number, data: BailCreateRequest) =>
    api
      .post<BailDetail>(`${BASE}/suspects/${suspectId}/bails/`, data)
      .then((r) => r.data),

  pay: (suspectId: number, bailId: number) =>
    api
      .post(`${BASE}/suspects/${suspectId}/bails/${bailId}/pay/`)
      .then((r) => r.data),
};

/* ── Bounty Tips ─────────────────────────────────────────────────── */

export const bountyTipsApi = {
  list: (params?: ListParams) =>
    api
      .get<PaginatedResponse<BountyTipListItem>>(`${BASE}/bounty-tips/`, {
        params,
      })
      .then((r) => r.data),

  detail: (id: number) =>
    api.get<BountyTipDetail>(`${BASE}/bounty-tips/${id}/`).then((r) => r.data),

  create: (data: BountyTipCreateRequest) =>
    api
      .post<BountyTipDetail>(`${BASE}/bounty-tips/`, data)
      .then((r) => r.data),

  review: (id: number, data: BountyTipReviewRequest) =>
    api
      .post<BountyTipDetail>(`${BASE}/bounty-tips/${id}/review/`, data)
      .then((r) => r.data),

  verify: (id: number) =>
    api
      .post<BountyTipDetail>(`${BASE}/bounty-tips/${id}/verify/`)
      .then((r) => r.data),

  lookupReward: (data: BountyRewardLookupRequest) =>
    api
      .post(`${BASE}/bounty-tips/lookup-reward/`, data)
      .then((r) => r.data),
};

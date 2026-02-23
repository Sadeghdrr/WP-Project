/**
 * Core API service — dashboard stats, notifications, search, constants.
 */
import api from './axios.instance';
import type { PaginatedResponse, ListParams } from '@/types/api.types';
import type {
  DashboardStats,
  Notification,
  GlobalSearchResponse,
  SystemConstants,
} from '@/types/notification.types';

export const coreApi = {
  /* ── Dashboard ──────────────────────────────────────────────────── */
  dashboardStats: () =>
    api.get<DashboardStats>('/core/dashboard/').then((r) => r.data),

  /* ── Notifications ──────────────────────────────────────────────── */
  notifications: (params?: ListParams) =>
    api
      .get<PaginatedResponse<Notification>>('/core/notifications/', { params })
      .then((r) => r.data),

  markRead: (id: number) =>
    api.post(`/core/notifications/${id}/read/`).then((r) => r.data),

  /* ── Global search ──────────────────────────────────────────────── */
  search: (query: string) =>
    api
      .get<GlobalSearchResponse>('/core/search/', { params: { search: query } })
      .then((r) => r.data),

  /* ── System constants ───────────────────────────────────────────── */
  constants: () =>
    api.get<SystemConstants>('/core/constants/').then((r) => r.data),
};

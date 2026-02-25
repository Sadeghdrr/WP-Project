/**
 * Centralised API endpoint paths.
 *
 * All backend URLs in one place — no hardcoded paths in components.
 * Paths are relative to VITE_API_BASE_URL (prepended by apiFetch).
 */

export const API = {
  // Auth
  LOGIN: "/accounts/token/",
  TOKEN_REFRESH: "/accounts/token/refresh/",
  REGISTER: "/accounts/register/",
  ME: "/accounts/me/",

  // Users & Roles (admin)
  USERS: "/accounts/users/",
  user: (id: number) => `/accounts/users/${id}/`,
  ROLES: "/accounts/roles/",
  role: (id: number) => `/accounts/roles/${id}/`,
  PERMISSIONS: "/accounts/permissions/",

  // Cases
  CASES: "/cases/cases/",
  case: (id: number) => `/cases/cases/${id}/`,
  CASE_STATUS_LOG: (caseId: number) => `/cases/cases/${caseId}/status-log/`,
  COMPLAINANTS: (caseId: number) => `/cases/cases/${caseId}/complainants/`,
  WITNESSES: (caseId: number) => `/cases/cases/${caseId}/witnesses/`,

  // Evidence
  EVIDENCE: "/evidence/evidence/",
  evidence: (id: number) => `/evidence/evidence/${id}/`,

  // Suspects (note: double-prefix bug in backend URL config)
  SUSPECTS: "/suspects/suspects/",
  suspect: (id: number) => `/suspects/suspects/${id}/`,
  INTERROGATIONS: "/suspects/interrogations/",
  TRIALS: "/suspects/trials/",
  BOUNTY_TIPS: "/suspects/bounty-tips/",
  BAIL: "/suspects/bail/",
  MOST_WANTED: "/suspects/most-wanted/",

  // Board
  BOARDS: "/board/boards/",
  board: (id: number) => `/board/boards/${id}/`,

  // Core
  DASHBOARD_STATS: "/core/stats/",
  SYSTEM_CONSTANTS: "/core/constants/",
  NOTIFICATIONS: "/core/notifications/",
} as const;

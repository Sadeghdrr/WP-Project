/**
 * Centralised API endpoint paths.
 *
 * All backend URLs in one place — no hardcoded paths in components.
 * Paths are relative to VITE_API_BASE_URL (prepended by apiFetch).
 */

export const API = {
  // Auth
  LOGIN: "/accounts/auth/login/",
  TOKEN_REFRESH: "/accounts/auth/token/refresh/",
  REGISTER: "/accounts/auth/register/",
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
  CASE_CALCULATIONS: (caseId: number) => `/cases/cases/${caseId}/calculations/`,
  CASE_REPORT: (caseId: number) => `/cases/cases/${caseId}/report/`,
  COMPLAINANTS: (caseId: number) => `/cases/cases/${caseId}/complainants/`,
  COMPLAINANT_REVIEW: (caseId: number, complainantId: number) =>
    `/cases/cases/${caseId}/complainants/${complainantId}/review/`,
  WITNESSES: (caseId: number) => `/cases/cases/${caseId}/witnesses/`,

  // Case workflow actions
  CASE_SUBMIT: (caseId: number) => `/cases/cases/${caseId}/submit/`,
  CASE_RESUBMIT: (caseId: number) => `/cases/cases/${caseId}/resubmit/`,
  CASE_CADET_REVIEW: (caseId: number) => `/cases/cases/${caseId}/cadet-review/`,
  CASE_OFFICER_REVIEW: (caseId: number) => `/cases/cases/${caseId}/officer-review/`,
  CASE_APPROVE_CRIME_SCENE: (caseId: number) => `/cases/cases/${caseId}/approve-crime-scene/`,
  CASE_DECLARE_SUSPECTS: (caseId: number) => `/cases/cases/${caseId}/declare-suspects/`,
  CASE_SERGEANT_REVIEW: (caseId: number) => `/cases/cases/${caseId}/sergeant-review/`,
  CASE_FORWARD_JUDICIARY: (caseId: number) => `/cases/cases/${caseId}/forward-judiciary/`,
  CASE_TRANSITION: (caseId: number) => `/cases/cases/${caseId}/transition/`,

  // Case assignment
  CASE_ASSIGN_DETECTIVE: (caseId: number) => `/cases/cases/${caseId}/assign-detective/`,
  CASE_UNASSIGN_DETECTIVE: (caseId: number) => `/cases/cases/${caseId}/unassign-detective/`,
  CASE_ASSIGN_SERGEANT: (caseId: number) => `/cases/cases/${caseId}/assign-sergeant/`,
  CASE_ASSIGN_CAPTAIN: (caseId: number) => `/cases/cases/${caseId}/assign-captain/`,
  CASE_ASSIGN_JUDGE: (caseId: number) => `/cases/cases/${caseId}/assign-judge/`,

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
  boardFull: (id: number) => `/board/boards/${id}/full/`,
  boardItems: (boardId: number) => `/board/boards/${boardId}/items/`,
  boardItem: (boardId: number, itemId: number) =>
    `/board/boards/${boardId}/items/${itemId}/`,
  boardItemsBatchCoordinates: (boardId: number) =>
    `/board/boards/${boardId}/items/batch-coordinates/`,
  boardConnections: (boardId: number) =>
    `/board/boards/${boardId}/connections/`,
  boardConnection: (boardId: number, connId: number) =>
    `/board/boards/${boardId}/connections/${connId}/`,
  boardNotes: (boardId: number) => `/board/boards/${boardId}/notes/`,
  boardNote: (boardId: number, noteId: number) =>
    `/board/boards/${boardId}/notes/${noteId}/`,

  // Core
  DASHBOARD_STATS: "/core/dashboard/",
  SYSTEM_CONSTANTS: "/core/constants/",
  GLOBAL_SEARCH: "/core/search/",
  NOTIFICATIONS: "/core/notifications/",
} as const;

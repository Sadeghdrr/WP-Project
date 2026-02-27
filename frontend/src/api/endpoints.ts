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

  // Cases — backend mounts at api/ + router prefix "cases" → /api/cases/
  CASES: "/cases/",
  case: (id: number) => `/cases/${id}/`,
  CASE_STATUS_LOG: (caseId: number) => `/cases/${caseId}/status-log/`,
  CASE_CALCULATIONS: (caseId: number) => `/cases/${caseId}/calculations/`,
  CASE_REPORT: (caseId: number) => `/cases/${caseId}/report/`,
  COMPLAINANTS: (caseId: number) => `/cases/${caseId}/complainants/`,
  COMPLAINANT_REVIEW: (caseId: number, complainantId: number) =>
    `/cases/${caseId}/complainants/${complainantId}/review/`,
  WITNESSES: (caseId: number) => `/cases/${caseId}/witnesses/`,

  // Case workflow actions
  CASE_SUBMIT: (caseId: number) => `/cases/${caseId}/submit/`,
  CASE_RESUBMIT: (caseId: number) => `/cases/${caseId}/resubmit/`,
  CASE_CADET_REVIEW: (caseId: number) => `/cases/${caseId}/cadet-review/`,
  CASE_OFFICER_REVIEW: (caseId: number) => `/cases/${caseId}/officer-review/`,
  CASE_APPROVE_CRIME_SCENE: (caseId: number) => `/cases/${caseId}/approve-crime-scene/`,
  CASE_TRANSITION: (caseId: number) => `/cases/${caseId}/transition/`,

  // Case assignment
  CASE_ASSIGN_DETECTIVE: (caseId: number) => `/cases/${caseId}/assign-detective/`,
  CASE_UNASSIGN_DETECTIVE: (caseId: number) => `/cases/${caseId}/unassign-detective/`,
  CASE_ASSIGN_SERGEANT: (caseId: number) => `/cases/${caseId}/assign-sergeant/`,
  CASE_ASSIGN_CAPTAIN: (caseId: number) => `/cases/${caseId}/assign-captain/`,
  CASE_ASSIGN_JUDGE: (caseId: number) => `/cases/${caseId}/assign-judge/`,

  // Evidence — backend mounts at api/ + router prefix "evidence" → /api/evidence/
  EVIDENCE: "/evidence/",
  evidence: (id: number) => `/evidence/${id}/`,
  EVIDENCE_VERIFY: (id: number) => `/evidence/${id}/verify/`,
  EVIDENCE_LINK_CASE: (id: number) => `/evidence/${id}/link-case/`,
  EVIDENCE_UNLINK_CASE: (id: number) => `/evidence/${id}/unlink-case/`,
  EVIDENCE_FILES: (id: number) => `/evidence/${id}/files/`,
  EVIDENCE_CHAIN_OF_CUSTODY: (id: number) => `/evidence/${id}/chain-of-custody/`,

  // Suspects
  SUSPECTS: "/suspects/",
  suspect: (id: number) => `/suspects/${id}/`,
  SUSPECT_APPROVE: (id: number) => `/suspects/${id}/approve/`,
  SUSPECT_ARREST: (id: number) => `/suspects/${id}/arrest/`,
  SUSPECT_TRANSITION: (id: number) => `/suspects/${id}/transition-status/`,
  SUSPECT_CAPTAIN_VERDICT: (id: number) => `/suspects/${id}/captain-verdict/`,
  SUSPECT_CHIEF_APPROVAL: (id: number) => `/suspects/${id}/chief-approval/`,
  suspectInterrogations: (suspectId: number) => `/suspects/${suspectId}/interrogations/`,
  suspectInterrogation: (suspectId: number, id: number) => `/suspects/${suspectId}/interrogations/${id}/`,
  suspectTrials: (suspectId: number) => `/suspects/${suspectId}/trials/`,
  suspectTrial: (suspectId: number, id: number) => `/suspects/${suspectId}/trials/${id}/`,
  suspectBails: (suspectId: number) => `/suspects/${suspectId}/bails/`,
  suspectBail: (suspectId: number, id: number) => `/suspects/${suspectId}/bails/${id}/`,
  MOST_WANTED: "/suspects/most-wanted/",

  // Bounty Tips — mounted at /api/bounty-tips/ (not under /suspects/)
  BOUNTY_TIPS: "/bounty-tips/",
  bountyTip: (id: number) => `/bounty-tips/${id}/`,
  bountyTipReview: (id: number) => `/bounty-tips/${id}/review/`,
  bountyTipVerify: (id: number) => `/bounty-tips/${id}/verify/`,
  BOUNTY_REWARD_LOOKUP: "/bounty-tips/lookup-reward/",

  // Board
  BOARDS: "/boards/",
  board: (id: number) => `/boards/${id}/`,
  boardFull: (id: number) => `/boards/${id}/full/`,
  boardItems: (boardId: number) => `/boards/${boardId}/items/`,
  boardItem: (boardId: number, itemId: number) =>
    `/boards/${boardId}/items/${itemId}/`,
  boardItemsBatchCoordinates: (boardId: number) =>
    `/boards/${boardId}/items/batch-coordinates/`,
  boardConnections: (boardId: number) =>
    `/boards/${boardId}/connections/`,
  boardConnection: (boardId: number, connId: number) =>
    `/boards/${boardId}/connections/${connId}/`,
  boardNotes: (boardId: number) => `/boards/${boardId}/notes/`,
  boardNote: (boardId: number, noteId: number) =>
    `/boards/${boardId}/notes/${noteId}/`,

  // Core
  DASHBOARD_STATS: "/core/dashboard/",
  SYSTEM_CONSTANTS: "/core/constants/",
  GLOBAL_SEARCH: "/core/search/",
  NOTIFICATIONS: "/core/notifications/",
  NOTIFICATION_READ: (id: number) => `/core/notifications/${id}/read/`,
} as const;

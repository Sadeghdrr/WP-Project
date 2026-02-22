// TODO: Mirror backend RBAC permission codenames (from core.permissions_constants)
// These strings must match the backend codenames exactly so the frontend can
// check user permissions returned by the JWT / user-detail endpoint.

// ── Accounts Permissions ──────────────────────────────────────────
export const AccountsPerms = {
  VIEW_ROLE: 'view_role',
  ADD_ROLE: 'add_role',
  CHANGE_ROLE: 'change_role',
  DELETE_ROLE: 'delete_role',
  VIEW_USER: 'view_user',
  ADD_USER: 'add_user',
  CHANGE_USER: 'change_user',
  DELETE_USER: 'delete_user',
} as const;

// ── Cases Permissions ─────────────────────────────────────────────
export const CasesPerms = {
  VIEW_CASE: 'view_case',
  ADD_CASE: 'add_case',
  CHANGE_CASE: 'change_case',
  DELETE_CASE: 'delete_case',
  CAN_REVIEW_COMPLAINT: 'can_review_complaint',
  CAN_APPROVE_CASE: 'can_approve_case',
  CAN_ASSIGN_DETECTIVE: 'can_assign_detective',
  CAN_CHANGE_CASE_STATUS: 'can_change_case_status',
  CAN_FORWARD_TO_JUDICIARY: 'can_forward_to_judiciary',
  CAN_APPROVE_CRITICAL_CASE: 'can_approve_critical_case',
} as const;

// ── Evidence Permissions ──────────────────────────────────────────
export const EvidencePerms = {
  VIEW_EVIDENCE: 'view_evidence',
  ADD_EVIDENCE: 'add_evidence',
  CHANGE_EVIDENCE: 'change_evidence',
  DELETE_EVIDENCE: 'delete_evidence',
  CAN_VERIFY_EVIDENCE: 'can_verify_evidence',
  CAN_REGISTER_FORENSIC_RESULT: 'can_register_forensic_result',
} as const;

// ── Suspects Permissions ──────────────────────────────────────────
export const SuspectsPerms = {
  VIEW_SUSPECT: 'view_suspect',
  ADD_SUSPECT: 'add_suspect',
  CHANGE_SUSPECT: 'change_suspect',
  DELETE_SUSPECT: 'delete_suspect',
  CAN_IDENTIFY_SUSPECT: 'can_identify_suspect',
  CAN_APPROVE_SUSPECT: 'can_approve_suspect',
  CAN_ISSUE_ARREST_WARRANT: 'can_issue_arrest_warrant',
  CAN_CONDUCT_INTERROGATION: 'can_conduct_interrogation',
  CAN_SCORE_GUILT: 'can_score_guilt',
  CAN_RENDER_VERDICT: 'can_render_verdict',
  CAN_JUDGE_TRIAL: 'can_judge_trial',
  CAN_REVIEW_BOUNTY_TIP: 'can_review_bounty_tip',
  CAN_VERIFY_BOUNTY_TIP: 'can_verify_bounty_tip',
  CAN_SET_BAIL_AMOUNT: 'can_set_bail_amount',
} as const;

// ── Board Permissions ─────────────────────────────────────────────
export const BoardPerms = {
  VIEW_DETECTIVEBOARD: 'view_detectiveboard',
  ADD_DETECTIVEBOARD: 'add_detectiveboard',
  CHANGE_DETECTIVEBOARD: 'change_detectiveboard',
  DELETE_DETECTIVEBOARD: 'delete_detectiveboard',
  CAN_EXPORT_BOARD: 'can_export_board',
} as const;

// ── Core Permissions ──────────────────────────────────────────────
export const CorePerms = {
  VIEW_NOTIFICATION: 'view_notification',
} as const;

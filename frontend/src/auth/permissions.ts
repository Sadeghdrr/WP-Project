/**
 * Centralized permission string constants.
 *
 * Format: "app_label.codename" — matches the backend's permission format
 * as returned in JWT `permissions_list` claim and `GET /api/accounts/me/`.
 *
 * Usage:
 *   import { P } from "@/auth/permissions";
 *   can(P.CASES.VIEW_CASE);
 *
 * These mirror backend/core/permissions_constants.py but use the full
 * "app_label.codename" format that the API actually returns.
 */

// ---------------------------------------------------------------------------
// Accounts
// ---------------------------------------------------------------------------
export const ACCOUNTS = {
  VIEW_ROLE: "accounts.view_role",
  ADD_ROLE: "accounts.add_role",
  CHANGE_ROLE: "accounts.change_role",
  DELETE_ROLE: "accounts.delete_role",
  VIEW_USER: "accounts.view_user",
  ADD_USER: "accounts.add_user",
  CHANGE_USER: "accounts.change_user",
  DELETE_USER: "accounts.delete_user",
} as const;

// ---------------------------------------------------------------------------
// Cases
// ---------------------------------------------------------------------------
export const CASES = {
  // CRUD
  VIEW_CASE: "cases.view_case",
  ADD_CASE: "cases.add_case",
  CHANGE_CASE: "cases.change_case",
  DELETE_CASE: "cases.delete_case",
  VIEW_CASECOMPLAINANT: "cases.view_casecomplainant",
  ADD_CASECOMPLAINANT: "cases.add_casecomplainant",
  CHANGE_CASECOMPLAINANT: "cases.change_casecomplainant",
  DELETE_CASECOMPLAINANT: "cases.delete_casecomplainant",
  VIEW_CASEWITNESS: "cases.view_casewitness",
  ADD_CASEWITNESS: "cases.add_casewitness",
  CHANGE_CASEWITNESS: "cases.change_casewitness",
  DELETE_CASEWITNESS: "cases.delete_casewitness",
  VIEW_CASESTATUSLOG: "cases.view_casestatuslog",
  ADD_CASESTATUSLOG: "cases.add_casestatuslog",
  CHANGE_CASESTATUSLOG: "cases.change_casestatuslog",
  DELETE_CASESTATUSLOG: "cases.delete_casestatuslog",
  // Workflow
  CAN_REVIEW_COMPLAINT: "cases.can_review_complaint",
  CAN_APPROVE_CASE: "cases.can_approve_case",
  CAN_ASSIGN_DETECTIVE: "cases.can_assign_detective",
  CAN_CHANGE_CASE_STATUS: "cases.can_change_case_status",
  CAN_FORWARD_TO_JUDICIARY: "cases.can_forward_to_judiciary",
  CAN_APPROVE_CRITICAL_CASE: "cases.can_approve_critical_case",
} as const;

// ---------------------------------------------------------------------------
// Evidence
// ---------------------------------------------------------------------------
export const EVIDENCE = {
  // CRUD — base
  VIEW_EVIDENCE: "evidence.view_evidence",
  ADD_EVIDENCE: "evidence.add_evidence",
  CHANGE_EVIDENCE: "evidence.change_evidence",
  DELETE_EVIDENCE: "evidence.delete_evidence",
  // CRUD — subtypes
  VIEW_TESTIMONYEVIDENCE: "evidence.view_testimonyevidence",
  ADD_TESTIMONYEVIDENCE: "evidence.add_testimonyevidence",
  CHANGE_TESTIMONYEVIDENCE: "evidence.change_testimonyevidence",
  DELETE_TESTIMONYEVIDENCE: "evidence.delete_testimonyevidence",
  VIEW_BIOLOGICALEVIDENCE: "evidence.view_biologicalevidence",
  ADD_BIOLOGICALEVIDENCE: "evidence.add_biologicalevidence",
  CHANGE_BIOLOGICALEVIDENCE: "evidence.change_biologicalevidence",
  DELETE_BIOLOGICALEVIDENCE: "evidence.delete_biologicalevidence",
  VIEW_VEHICLEEVIDENCE: "evidence.view_vehicleevidence",
  ADD_VEHICLEEVIDENCE: "evidence.add_vehicleevidence",
  CHANGE_VEHICLEEVIDENCE: "evidence.change_vehicleevidence",
  DELETE_VEHICLEEVIDENCE: "evidence.delete_vehicleevidence",
  VIEW_IDENTITYEVIDENCE: "evidence.view_identityevidence",
  ADD_IDENTITYEVIDENCE: "evidence.add_identityevidence",
  CHANGE_IDENTITYEVIDENCE: "evidence.change_identityevidence",
  DELETE_IDENTITYEVIDENCE: "evidence.delete_identityevidence",
  // Files
  VIEW_EVIDENCEFILE: "evidence.view_evidencefile",
  ADD_EVIDENCEFILE: "evidence.add_evidencefile",
  CHANGE_EVIDENCEFILE: "evidence.change_evidencefile",
  DELETE_EVIDENCEFILE: "evidence.delete_evidencefile",
  // Workflow
  CAN_VERIFY_EVIDENCE: "evidence.can_verify_evidence",
  CAN_REGISTER_FORENSIC_RESULT: "evidence.can_register_forensic_result",
} as const;

// ---------------------------------------------------------------------------
// Suspects
// ---------------------------------------------------------------------------
export const SUSPECTS = {
  // CRUD
  VIEW_SUSPECT: "suspects.view_suspect",
  ADD_SUSPECT: "suspects.add_suspect",
  CHANGE_SUSPECT: "suspects.change_suspect",
  DELETE_SUSPECT: "suspects.delete_suspect",
  VIEW_INTERROGATION: "suspects.view_interrogation",
  ADD_INTERROGATION: "suspects.add_interrogation",
  CHANGE_INTERROGATION: "suspects.change_interrogation",
  DELETE_INTERROGATION: "suspects.delete_interrogation",
  VIEW_TRIAL: "suspects.view_trial",
  ADD_TRIAL: "suspects.add_trial",
  CHANGE_TRIAL: "suspects.change_trial",
  DELETE_TRIAL: "suspects.delete_trial",
  VIEW_BOUNTYTIP: "suspects.view_bountytip",
  ADD_BOUNTYTIP: "suspects.add_bountytip",
  CHANGE_BOUNTYTIP: "suspects.change_bountytip",
  DELETE_BOUNTYTIP: "suspects.delete_bountytip",
  VIEW_BAIL: "suspects.view_bail",
  ADD_BAIL: "suspects.add_bail",
  CHANGE_BAIL: "suspects.change_bail",
  DELETE_BAIL: "suspects.delete_bail",
  // Workflow
  CAN_IDENTIFY_SUSPECT: "suspects.can_identify_suspect",
  CAN_APPROVE_SUSPECT: "suspects.can_approve_suspect",
  CAN_ISSUE_ARREST_WARRANT: "suspects.can_issue_arrest_warrant",
  CAN_CONDUCT_INTERROGATION: "suspects.can_conduct_interrogation",
  CAN_SCORE_GUILT: "suspects.can_score_guilt",
  CAN_RENDER_VERDICT: "suspects.can_render_verdict",
  CAN_JUDGE_TRIAL: "suspects.can_judge_trial",
  CAN_REVIEW_BOUNTY_TIP: "suspects.can_review_bounty_tip",
  CAN_VERIFY_BOUNTY_TIP: "suspects.can_verify_bounty_tip",
  CAN_SET_BAIL_AMOUNT: "suspects.can_set_bail_amount",
} as const;

// ---------------------------------------------------------------------------
// Board
// ---------------------------------------------------------------------------
export const BOARD = {
  VIEW_DETECTIVEBOARD: "board.view_detectiveboard",
  ADD_DETECTIVEBOARD: "board.add_detectiveboard",
  CHANGE_DETECTIVEBOARD: "board.change_detectiveboard",
  DELETE_DETECTIVEBOARD: "board.delete_detectiveboard",
  VIEW_BOARDNOTE: "board.view_boardnote",
  ADD_BOARDNOTE: "board.add_boardnote",
  CHANGE_BOARDNOTE: "board.change_boardnote",
  DELETE_BOARDNOTE: "board.delete_boardnote",
  VIEW_BOARDITEM: "board.view_boarditem",
  ADD_BOARDITEM: "board.add_boarditem",
  CHANGE_BOARDITEM: "board.change_boarditem",
  DELETE_BOARDITEM: "board.delete_boarditem",
  VIEW_BOARDCONNECTION: "board.view_boardconnection",
  ADD_BOARDCONNECTION: "board.add_boardconnection",
  CHANGE_BOARDCONNECTION: "board.change_boardconnection",
  DELETE_BOARDCONNECTION: "board.delete_boardconnection",
  CAN_EXPORT_BOARD: "board.can_export_board",
} as const;

// ---------------------------------------------------------------------------
// Core
// ---------------------------------------------------------------------------
export const CORE = {
  VIEW_NOTIFICATION: "core.view_notification",
  ADD_NOTIFICATION: "core.add_notification",
  CHANGE_NOTIFICATION: "core.change_notification",
  DELETE_NOTIFICATION: "core.delete_notification",
} as const;

// ---------------------------------------------------------------------------
// Convenience namespace
// ---------------------------------------------------------------------------

/** Grouped permission constants — use as `P.CASES.VIEW_CASE` */
export const P = {
  ACCOUNTS,
  CASES,
  EVIDENCE,
  SUSPECTS,
  BOARD,
  CORE,
} as const;

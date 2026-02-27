/**
 * Suspect status labels, colours, and workflow helpers.
 *
 * Mirrors backend SuspectStatus choices and the per-suspect workflow.
 */

import type { SuspectStatus, SergeantApprovalStatus } from "../types";

// ---------------------------------------------------------------------------
// Status display metadata
// ---------------------------------------------------------------------------

export const SUSPECT_STATUS_LABELS: Record<SuspectStatus, string> = {
  wanted: "Wanted",
  arrested: "Arrested",
  under_interrogation: "Under Interrogation",
  pending_captain_verdict: "Pending Captain Verdict",
  pending_chief_approval: "Pending Chief Approval",
  under_trial: "Under Trial",
  convicted: "Convicted",
  acquitted: "Acquitted",
  released: "Released",
};

export type StatusColor =
  | "gray"
  | "blue"
  | "yellow"
  | "orange"
  | "green"
  | "red"
  | "purple";

export const SUSPECT_STATUS_COLORS: Record<SuspectStatus, StatusColor> = {
  wanted: "orange",
  arrested: "red",
  under_interrogation: "blue",
  pending_captain_verdict: "yellow",
  pending_chief_approval: "yellow",
  under_trial: "purple",
  convicted: "red",
  acquitted: "green",
  released: "green",
};

export const APPROVAL_STATUS_LABELS: Record<SergeantApprovalStatus, string> = {
  pending: "Pending Approval",
  approved: "Approved",
  rejected: "Rejected",
};

export const APPROVAL_STATUS_COLORS: Record<SergeantApprovalStatus, StatusColor> = {
  pending: "yellow",
  approved: "green",
  rejected: "red",
};

// ---------------------------------------------------------------------------
// Per-suspect workflow actions
// ---------------------------------------------------------------------------

export interface SuspectWorkflowAction {
  key: string;
  label: string;
  variant: "primary" | "danger" | "default";
  needsForm?: boolean;
  requiredPermissions: string[];
}

/**
 * Get the available workflow actions for a suspect based on its current
 * status & sergeant approval status.
 */
export function getSuspectActions(
  status: SuspectStatus,
  approvalStatus: SergeantApprovalStatus,
  userPermissions: ReadonlySet<string>,
): SuspectWorkflowAction[] {
  const all = getActionsForState(status, approvalStatus);
  return all.filter((a) =>
    a.requiredPermissions.some((p) => userPermissions.has(p)),
  );
}

function getActionsForState(
  status: SuspectStatus,
  approvalStatus: SergeantApprovalStatus,
): SuspectWorkflowAction[] {
  // Wanted + pending → sergeant can approve/reject
  if (status === "wanted" && approvalStatus === "pending") {
    return [
      {
        key: "approve",
        label: "Approve Suspect",
        variant: "primary",
        requiredPermissions: ["suspects.can_approve_suspect"],
      },
      {
        key: "reject",
        label: "Reject Suspect",
        variant: "danger",
        needsForm: true,
        requiredPermissions: ["suspects.can_approve_suspect"],
      },
    ];
  }

  // Wanted + rejected → detective can update and resubmit
  if (status === "wanted" && approvalStatus === "rejected") {
    return [
      {
        key: "update_resubmit",
        label: "Update & Resubmit for Approval",
        variant: "primary",
        needsForm: true,
        requiredPermissions: ["suspects.can_identify_suspect"],
      },
    ];
  }

  // Wanted + approved → can be arrested
  if (status === "wanted" && approvalStatus === "approved") {
    return [
      {
        key: "arrest",
        label: "Execute Arrest",
        variant: "primary",
        needsForm: true,
        requiredPermissions: ["suspects.can_issue_arrest_warrant"],
      },
    ];
  }

  // Arrested → begin interrogation
  if (status === "arrested") {
    return [
      {
        key: "begin_interrogation",
        label: "Begin Interrogation",
        variant: "primary",
        requiredPermissions: ["suspects.can_conduct_interrogation"],
      },
    ];
  }

  // Under interrogation → create interrogation records, then send to captain
  if (status === "under_interrogation") {
    return [
      {
        key: "create_interrogation",
        label: "Record Interrogation",
        variant: "primary",
        needsForm: true,
        requiredPermissions: ["suspects.can_conduct_interrogation"],
      },
      {
        key: "send_to_captain",
        label: "Send to Captain Review",
        variant: "default",
        requiredPermissions: ["suspects.can_conduct_interrogation"],
      },
    ];
  }

  // Pending captain verdict
  if (status === "pending_captain_verdict") {
    return [
      {
        key: "captain_guilty",
        label: "Verdict: Guilty",
        variant: "danger",
        needsForm: true,
        requiredPermissions: ["suspects.can_render_verdict"],
      },
      {
        key: "captain_innocent",
        label: "Verdict: Innocent",
        variant: "primary",
        needsForm: true,
        requiredPermissions: ["suspects.can_render_verdict"],
      },
    ];
  }

  // Pending chief approval
  if (status === "pending_chief_approval") {
    return [
      {
        key: "chief_approve",
        label: "Approve for Trial",
        variant: "primary",
        requiredPermissions: ["suspects.can_render_verdict"],
      },
      {
        key: "chief_reject",
        label: "Reject (Return to Captain)",
        variant: "danger",
        needsForm: true,
        requiredPermissions: ["suspects.can_render_verdict"],
      },
    ];
  }

  // Under trial → judge creates trial record
  if (status === "under_trial") {
    return [
      {
        key: "create_trial",
        label: "Record Trial Verdict",
        variant: "primary",
        needsForm: true,
        requiredPermissions: ["suspects.can_judge_trial"],
      },
      {
        key: "create_bail",
        label: "Set Bail",
        variant: "default",
        needsForm: true,
        requiredPermissions: ["suspects.can_set_bail_amount"],
      },
    ];
  }

  return [];
}

/**
 * Check if a suspect status is terminal.
 */
export function isTerminalSuspectStatus(status: SuspectStatus): boolean {
  return status === "convicted" || status === "acquitted" || status === "released";
}

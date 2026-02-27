/**
 * Case status labels, colours, and workflow action mapping.
 *
 * Mirrors backend CaseStatus choices and ALLOWED_TRANSITIONS map.
 * Only exposes actions that the backend actually supports.
 */

import type { CaseStatus } from "../types";

// ---------------------------------------------------------------------------
// Status display metadata
// ---------------------------------------------------------------------------

export const STATUS_LABELS: Record<CaseStatus, string> = {
  complaint_registered: "Complaint Registered",
  cadet_review: "Under Cadet Review",
  returned_to_complainant: "Returned to Complainant",
  officer_review: "Under Officer Review",
  returned_to_cadet: "Returned to Cadet",
  voided: "Voided",
  pending_approval: "Pending Approval",
  open: "Open",
  investigation: "Under Investigation",
  judiciary: "Referred to Judiciary",
  closed: "Closed",
};

export type StatusColor =
  | "gray"
  | "blue"
  | "yellow"
  | "orange"
  | "green"
  | "red"
  | "purple";

export const STATUS_COLORS: Record<CaseStatus, StatusColor> = {
  complaint_registered: "gray",
  cadet_review: "blue",
  returned_to_complainant: "orange",
  officer_review: "blue",
  returned_to_cadet: "orange",
  voided: "red",
  pending_approval: "yellow",
  open: "green",
  investigation: "blue",
  judiciary: "purple",
  closed: "gray",
};

// ---------------------------------------------------------------------------
// Crime level display
// ---------------------------------------------------------------------------

export const CRIME_LEVEL_LABELS: Record<number, string> = {
  1: "Level 3 (Minor)",
  2: "Level 2 (Medium)",
  3: "Level 1 (Major)",
  4: "Critical",
};

export const CRIME_LEVEL_COLORS: Record<number, StatusColor> = {
  1: "green",
  2: "yellow",
  3: "orange",
  4: "red",
};

// ---------------------------------------------------------------------------
// Workflow actions — mapped per status
//
// Each action specifies:
//   - key: unique identifier
//   - label: display text
//   - variant: "primary" | "danger" | "default"
//   - needsMessage: whether a text message is required (rejection)
//   - requiredPermission: permission codename(s) that enable this action
// ---------------------------------------------------------------------------

export interface WorkflowAction {
  key: string;
  label: string;
  variant: "primary" | "danger" | "default";
  needsMessage?: boolean;
  /** One of these permissions enables the action (OR logic). */
  requiredPermissions: string[];
}

/**
 * Actions available for each case status. Only includes actions
 * that the backend explicitly supports.
 */
export const STATUS_ACTIONS: Partial<Record<CaseStatus, WorkflowAction[]>> = {
  complaint_registered: [
    {
      key: "submit",
      label: "Submit for Review",
      variant: "primary",
      requiredPermissions: ["cases.add_case"],
    },
  ],
  cadet_review: [
    {
      key: "cadet_approve",
      label: "Approve",
      variant: "primary",
      requiredPermissions: ["cases.can_review_complaint"],
    },
    {
      key: "cadet_reject",
      label: "Reject",
      variant: "danger",
      needsMessage: true,
      requiredPermissions: ["cases.can_review_complaint"],
    },
  ],
  returned_to_complainant: [
    {
      key: "resubmit",
      label: "Edit & Resubmit",
      variant: "primary",
      requiredPermissions: ["cases.add_case"],
    },
  ],
  officer_review: [
    {
      key: "officer_approve",
      label: "Approve",
      variant: "primary",
      requiredPermissions: ["cases.can_approve_case"],
    },
    {
      key: "officer_reject",
      label: "Return to Cadet",
      variant: "danger",
      needsMessage: true,
      requiredPermissions: ["cases.can_approve_case"],
    },
  ],
  returned_to_cadet: [
    {
      key: "cadet_reforward",
      label: "Re-forward to Officer",
      variant: "primary",
      requiredPermissions: ["cases.can_review_complaint"],
    },
  ],
  pending_approval: [
    {
      key: "approve_crime_scene",
      label: "Approve Crime Scene",
      variant: "primary",
      requiredPermissions: ["cases.can_approve_case"],
    },
  ],
  open: [
    {
      key: "assign_detective",
      label: "Assign Detective",
      variant: "primary",
      requiredPermissions: ["cases.can_assign_detective"],
    },
    {
      key: "assign_sergeant",
      label: "Assign Sergeant",
      variant: "primary",
      requiredPermissions: ["cases.can_assign_detective"],
    },
    {
      key: "assign_captain",
      label: "Assign Captain",
      variant: "primary",
      requiredPermissions: ["cases.can_assign_detective"],
    },
    {
      key: "assign_judge",
      label: "Assign Judge",
      variant: "primary",
      requiredPermissions: ["cases.can_forward_to_judiciary"],
    },
  ],
  investigation: [
    {
      key: "assign_sergeant",
      label: "Assign Sergeant",
      variant: "primary",
      requiredPermissions: ["cases.can_assign_detective"],
    },
    {
      key: "assign_captain",
      label: "Assign Captain",
      variant: "primary",
      requiredPermissions: ["cases.can_assign_detective"],
    },
    {
      key: "assign_judge",
      label: "Assign Judge",
      variant: "primary",
      requiredPermissions: ["cases.can_forward_to_judiciary"],
    },
  ],
  judiciary: [
    {
      key: "assign_sergeant",
      label: "Assign Sergeant",
      variant: "primary",
      requiredPermissions: ["cases.can_assign_detective"],
    },
    {
      key: "assign_captain",
      label: "Assign Captain",
      variant: "primary",
      requiredPermissions: ["cases.can_assign_detective"],
    },
    {
      key: "assign_judge",
      label: "Assign Judge",
      variant: "primary",
      requiredPermissions: ["cases.can_forward_to_judiciary"],
    },
    {
      key: "close_case",
      label: "Close Case",
      variant: "primary",
      requiredPermissions: ["cases.can_change_case_status"],
    },
  ],
};

/**
 * Filter available actions based on user's permission set.
 */
export function getAvailableActions(
  status: CaseStatus,
  userPermissions: ReadonlySet<string>,
): WorkflowAction[] {
  const actions = STATUS_ACTIONS[status] ?? [];
  return actions.filter((action) =>
    action.requiredPermissions.some((p) => userPermissions.has(p)),
  );
}

/**
 * Check if a status is terminal (no further transitions possible).
 */
export function isTerminalStatus(status: CaseStatus): boolean {
  return status === "voided" || status === "closed";
}

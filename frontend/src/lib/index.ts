/**
 * Lib module barrel export.
 *
 * Shared utilities that are not React components or hooks.
 */
export {
  getFieldError,
  getFieldErrors,
  hasFieldErrors,
  getErrorMessage,
  flattenErrors,
} from "./errors";

export {
  STATUS_LABELS,
  STATUS_COLORS,
  CRIME_LEVEL_LABELS,
  CRIME_LEVEL_COLORS,
  STATUS_ACTIONS,
  getAvailableActions,
  isTerminalStatus,
} from "./caseWorkflow";
export type { WorkflowAction, StatusColor } from "./caseWorkflow";

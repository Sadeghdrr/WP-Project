/**
 * Auth module barrel export.
 *
 * Usage:
 *   import { P, can, canAll, checkAccess, buildPermissionSet } from "@/auth";
 */

// Permission constants
export { P, ACCOUNTS, CASES, EVIDENCE, SUSPECTS, BOARD, CORE } from "./permissions";

// Permission check utilities
export {
  can,
  canAll,
  canAny,
  hasMinHierarchy,
  checkAccess,
  buildPermissionSet,
} from "./can";

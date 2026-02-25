/**
 * Auth module barrel export.
 *
 * Usage:
 *   import { useAuth, AuthProvider, P, can } from "../auth";
 */

// Auth context & hook
export { AuthProvider } from "./AuthContext";
export { AuthContext } from "./AuthContext";
export type { AuthContextValue, AuthStatus } from "./AuthContext";
export { useAuth } from "./useAuth";

// Token storage
export {
  getStoredRefreshToken,
  storeRefreshToken,
  clearStoredRefreshToken,
} from "./tokenStorage";

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

/**
 * Permission-checking utilities.
 *
 * Pure functions that operate on a permission set. These are used by:
 *   - AuthContext (React context provider)
 *   - <Can> component (declarative guard)
 *   - <ProtectedRoute> component (route guard)
 *   - Imperative checks in event handlers
 *
 * No React dependency — these are plain TS functions.
 */

// ---------------------------------------------------------------------------
// Core check functions
// ---------------------------------------------------------------------------

/**
 * Check if the user has a specific permission.
 *
 * @param userPermissions - Set of "app_label.codename" strings from JWT/me
 * @param permission - Single permission string to check
 */
export function can(
  userPermissions: ReadonlySet<string>,
  permission: string,
): boolean {
  return userPermissions.has(permission);
}

/**
 * Check if the user has ALL of the specified permissions (AND logic).
 *
 * @param userPermissions - Set of "app_label.codename" strings
 * @param permissions - Array of permission strings; ALL must be present
 */
export function canAll(
  userPermissions: ReadonlySet<string>,
  permissions: readonly string[],
): boolean {
  return permissions.every((p) => userPermissions.has(p));
}

/**
 * Check if the user has ANY of the specified permissions (OR logic).
 *
 * @param userPermissions - Set of "app_label.codename" strings
 * @param permissions - Array of permission strings; at least ONE must be present
 */
export function canAny(
  userPermissions: ReadonlySet<string>,
  permissions: readonly string[],
): boolean {
  return permissions.some((p) => userPermissions.has(p));
}

/**
 * Check if the user's hierarchy level meets the minimum threshold.
 *
 * @param userHierarchy - The user's hierarchy_level (from JWT or /me)
 * @param minLevel - Minimum hierarchy level required
 */
export function hasMinHierarchy(
  userHierarchy: number,
  minLevel: number,
): boolean {
  return userHierarchy >= minLevel;
}

// ---------------------------------------------------------------------------
// Compound check
// ---------------------------------------------------------------------------

/**
 * Combined guard check: all permissions AND minimum hierarchy.
 * Used by route guards and the <ProtectedRoute> component.
 *
 * @param userPermissions - Set of permission strings
 * @param userHierarchy - User's hierarchy_level
 * @param requirements - Guard requirements
 * @returns true if all requirements are met
 */
export function checkAccess(
  userPermissions: ReadonlySet<string>,
  userHierarchy: number,
  requirements: {
    permissions?: readonly string[];
    minHierarchy?: number;
  },
): boolean {
  const { permissions, minHierarchy: minLevel } = requirements;

  if (permissions && permissions.length > 0 && !canAll(userPermissions, permissions)) {
    return false;
  }

  if (minLevel !== undefined && !hasMinHierarchy(userHierarchy, minLevel)) {
    return false;
  }

  return true;
}

// ---------------------------------------------------------------------------
// Permission set factory
// ---------------------------------------------------------------------------

/**
 * Build a Set from the permissions_list array (from JWT or /me response).
 * The Set provides O(1) lookups for permission checks.
 *
 * @param permissionsList - Array of "app_label.codename" strings
 */
export function buildPermissionSet(
  permissionsList: readonly string[],
): ReadonlySet<string> {
  return new Set(permissionsList);
}

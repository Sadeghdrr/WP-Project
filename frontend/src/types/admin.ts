/**
 * Admin-panel-specific types.
 *
 * Maps to backend serializers:
 *   - UserListSerializer  → UserListItem
 *   - PermissionSerializer → PermissionItem
 *   - RoleDetailSerializer → RoleDetailFull
 */

// ---------------------------------------------------------------------------
// User list item (returned by GET /api/accounts/users/)
// ---------------------------------------------------------------------------

export interface UserListItem {
  id: number;
  username: string;
  email: string;
  national_id: string;
  phone_number: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  /** Role FK (PK), nullable if unassigned */
  role: number | null;
  role_name: string | null;
  hierarchy_level: number;
}

// ---------------------------------------------------------------------------
// Permission item (returned by GET /api/accounts/permissions/)
// ---------------------------------------------------------------------------

export interface PermissionItem {
  id: number;
  name: string;
  codename: string;
  /** "app_label.codename" */
  full_codename: string;
}

// ---------------------------------------------------------------------------
// Role detail with permission IDs (returned by GET /api/accounts/roles/:id/)
// ---------------------------------------------------------------------------

export interface RoleDetailFull {
  id: number;
  name: string;
  description: string;
  hierarchy_level: number;
  /** Permission PKs (writable) */
  permissions: number[];
  /** Read-only "app_label.codename" list */
  permissions_display: string[];
}

// ---------------------------------------------------------------------------
// Role list item (returned by GET /api/accounts/roles/)
// ---------------------------------------------------------------------------

export interface RoleListItem {
  id: number;
  name: string;
  description: string;
  hierarchy_level: number;
}

// ---------------------------------------------------------------------------
// Request DTOs
// ---------------------------------------------------------------------------

export interface AssignRoleRequest {
  role_id: number;
}

export interface AssignPermissionsRequest {
  permission_ids: number[];
}

export interface RoleCreatePayload {
  name: string;
  description?: string;
  hierarchy_level: number;
  permissions?: number[];
}

export interface RoleUpdatePayload {
  name?: string;
  description?: string;
  hierarchy_level?: number;
  permissions?: number[];
}

// ---------------------------------------------------------------------------
// Filter params for user list
// ---------------------------------------------------------------------------

export interface UserFilters {
  search?: string;
  role?: number;
  is_active?: boolean;
  hierarchy_level?: number;
}

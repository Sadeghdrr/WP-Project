/**
 * User & Role types — mirrors backend accounts.models.
 */

/* ── Permission ──────────────────────────────────────────────────── */

export interface Permission {
  id: number;
  name: string;
  codename: string;
  content_type?: number;
}

/* ── Role ─────────────────────────────────────────────────────────── */

export interface RoleListItem {
  id: number;
  name: string;
  hierarchy_level: number;
}

export interface Role extends RoleListItem {
  description: string;
  permissions: Permission[];
}

export interface RoleCreateRequest {
  name: string;
  description?: string;
  hierarchy_level?: number;
}

export type RoleUpdateRequest = Partial<RoleCreateRequest>;

export interface AssignPermissionsRequest {
  permissions: number[];
}

/* ── User ─────────────────────────────────────────────────────────── */

export interface UserListItem {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  role: RoleListItem | null;
}

export interface User extends UserListItem {
  national_id: string;
  phone_number: string;
  permissions: string[];
  date_joined: string;
}

/** Shape returned by /api/accounts/me/ */
export type MeUser = User;

export interface MeUpdateRequest {
  email?: string;
  phone_number?: string;
  first_name?: string;
  last_name?: string;
}

export interface AssignRoleRequest {
  role_id: number;
}

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

/* ── Raw API response shapes (before normalisation) ──────────────── */

/**
 * Raw shape returned by /api/accounts/me/ and the `user` field in login.
 * Backend sends `role` as an integer FK and `role_detail` as a nested object.
 */
export interface RawUserDetail {
  id: number;
  username: string;
  email: string;
  national_id: string;
  phone_number: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  date_joined: string;
  role: number | null;
  role_detail: RoleListItem | null;
  permissions: string[];
}

/**
 * Raw shape returned by /api/accounts/users/ list endpoint.
 * Backend sends `role` as integer FK, `role_name` and `hierarchy_level` as flat fields.
 */
export interface RawUserListItem {
  id: number;
  username: string;
  email: string;
  national_id?: string;
  phone_number?: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  role: number | null;
  role_name: string;
  hierarchy_level: number;
  date_joined?: string;
  permissions?: string[];
}

/* ── Normalisers ─────────────────────────────────────────────────── */

/** Normalise a /me/ or login user response into the internal User shape. */
export function normalizeUser(raw: RawUserDetail): User {
  return {
    id: raw.id,
    username: raw.username,
    email: raw.email,
    national_id: raw.national_id,
    phone_number: raw.phone_number,
    first_name: raw.first_name,
    last_name: raw.last_name,
    is_active: raw.is_active,
    date_joined: raw.date_joined,
    permissions: raw.permissions ?? [],
    role: raw.role_detail ?? null,
  };
}

/** Normalise a user list item from /accounts/users/ into UserListItem. */
export function normalizeUserListItem(raw: RawUserListItem): UserListItem {
  return {
    id: raw.id,
    username: raw.username,
    email: raw.email,
    first_name: raw.first_name,
    last_name: raw.last_name,
    is_active: raw.is_active,
    role:
      raw.role != null
        ? { id: raw.role, name: raw.role_name ?? '', hierarchy_level: raw.hierarchy_level ?? 0 }
        : null,
  };
}

/** Normalise a full user detail (returned by assign-role, activate, etc.) */
export function normalizeUserDetail(raw: RawUserListItem & { national_id: string; phone_number: string; date_joined: string; permissions: string[] }): User {
  return {
    ...normalizeUserListItem(raw),
    national_id: raw.national_id,
    phone_number: raw.phone_number,
    date_joined: raw.date_joined,
    permissions: raw.permissions ?? [],
  };
}

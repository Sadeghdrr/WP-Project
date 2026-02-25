/**
 * Auth, User, Role, and Permission types.
 * Maps to: accounts app models + JWT token structure.
 */

import type { EntityId, ISODateTime, TimeStamped } from "./common";

// ---------------------------------------------------------------------------
// Permissions (Django auth.Permission)
// ---------------------------------------------------------------------------

export interface Permission {
  id: number;
  codename: string;
  name: string;
  content_type: number;
}

// ---------------------------------------------------------------------------
// Role
// ---------------------------------------------------------------------------

export interface Role extends Pick<TimeStamped, "created_at" | "updated_at"> {
  id: number;
  name: string;
  description: string;
  hierarchy_level: number;
  permissions: Permission[];
}

/** Lightweight role detail (nested inside User via role_detail) */
export interface RoleDetail {
  id: number;
  name: string;
  description: string;
  hierarchy_level: number;
}

/** Lightweight role reference (used when nested inside User) */
export interface RoleRef {
  id: number;
  name: string;
  hierarchy_level: number;
}

// ---------------------------------------------------------------------------
// User
// ---------------------------------------------------------------------------

/**
 * User shape returned by backend UserDetailSerializer.
 *
 * - `role` is a string (role name) from StringRelatedField
 * - `role_detail` is the nested RoleDetail object (nullable)
 * - `permissions` is a flat list of "app_label.codename" strings
 */
export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  national_id: string;
  phone_number: string;
  role: string | null;
  role_detail: RoleDetail | null;
  permissions: string[];
  is_active: boolean;
  date_joined: ISODateTime;
}

/** Minimal user reference (for FK fields in other entities) */
export interface UserRef {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
}

// ---------------------------------------------------------------------------
// Auth Requests / Responses
// ---------------------------------------------------------------------------

/**
 * Login accepts one "identifier" field (username, email, phone, or national_id)
 * plus password.
 */
export interface LoginRequest {
  identifier: string;
  password: string;
}

export interface TokenPair {
  access: string;
  refresh: string;
}

/**
 * Backend login returns flat {access, refresh, user} — NOT nested tokens.
 */
export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

export interface RegisterRequest {
  username: string;
  email: string;
  phone_number: string;
  national_id: string;
  first_name: string;
  last_name: string;
  password: string;
  password_confirm: string;
}

/**
 * Backend registration returns UserDetailSerializer only — no tokens.
 * Frontend must follow up with a login call.
 */
export type RegisterResponse = User;

export interface TokenRefreshRequest {
  refresh: string;
}

export interface TokenRefreshResponse {
  access: string;
}

// ---------------------------------------------------------------------------
// JWT Custom Claims (decoded from access token)
// ---------------------------------------------------------------------------

export interface JwtPayload {
  user_id: number;
  role: string;
  hierarchy_level: number;
  permissions_list: string[];
  exp: number;
  iat: number;
  jti: string;
  token_type: "access" | "refresh";
}

// ---------------------------------------------------------------------------
// Role management DTOs
// ---------------------------------------------------------------------------

export interface RoleCreateRequest {
  name: string;
  description?: string;
  hierarchy_level: number;
  permissions: EntityId[];
}

export interface RoleUpdateRequest extends Partial<RoleCreateRequest> {}

export interface UserUpdateRoleRequest {
  role: EntityId | null;
}

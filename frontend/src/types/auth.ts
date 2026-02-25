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

/** Lightweight role reference (used when nested inside User) */
export interface RoleRef {
  id: number;
  name: string;
  hierarchy_level: number;
}

// ---------------------------------------------------------------------------
// User
// ---------------------------------------------------------------------------

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  national_id: string;
  phone_number: string;
  role: RoleRef | null;
  is_active: boolean;
  is_staff: boolean;
  date_joined: ISODateTime;
  last_login: ISODateTime | null;
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

export interface LoginResponse {
  tokens: TokenPair;
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

export interface RegisterResponse {
  user: User;
  tokens: TokenPair;
}

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

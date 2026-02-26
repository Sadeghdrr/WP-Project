/**
 * Admin API service — users, roles, and permissions management.
 *
 * Endpoints:
 *   Users:       GET /api/accounts/users/
 *                GET /api/accounts/users/:id/
 *                PATCH /api/accounts/users/:id/assign-role/
 *                PATCH /api/accounts/users/:id/activate/
 *                PATCH /api/accounts/users/:id/deactivate/
 *   Roles:       GET /api/accounts/roles/
 *                POST /api/accounts/roles/
 *                GET /api/accounts/roles/:id/
 *                PUT /api/accounts/roles/:id/
 *                PATCH /api/accounts/roles/:id/
 *                DELETE /api/accounts/roles/:id/
 *                POST /api/accounts/roles/:id/assign-permissions/
 *   Permissions: GET /api/accounts/permissions/
 */

import { apiGet, apiPost, apiPut, apiPatch, apiDelete } from "./client";
import type { ApiResponse } from "./client";
import { API } from "./endpoints";
import type {
  UserListItem,
  UserFilters,
  RoleListItem,
  RoleDetailFull,
  RoleCreatePayload,
  RoleUpdatePayload,
  AssignRoleRequest,
  AssignPermissionsRequest,
  PermissionItem,
} from "../types/admin";
import type { User } from "../types/auth";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildQuery(params: Record<string, unknown>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") {
      sp.set(k, String(v));
    }
  }
  const qs = sp.toString();
  return qs ? `?${qs}` : "";
}

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

/** GET /api/accounts/users/ */
export function listUsers(
  filters?: UserFilters,
): Promise<ApiResponse<UserListItem[]>> {
  const qs = filters ? buildQuery(filters as Record<string, unknown>) : "";
  return apiGet<UserListItem[]>(API.USERS + qs);
}

/** GET /api/accounts/users/:id/ */
export function getUser(id: number): Promise<ApiResponse<User>> {
  return apiGet<User>(API.user(id));
}

/** PATCH /api/accounts/users/:id/assign-role/ */
export function assignRole(
  userId: number,
  payload: AssignRoleRequest,
): Promise<ApiResponse<User>> {
  return apiPatch<User>(`${API.user(userId)}assign-role/`, payload);
}

/** PATCH /api/accounts/users/:id/activate/ */
export function activateUser(userId: number): Promise<ApiResponse<User>> {
  return apiPatch<User>(`${API.user(userId)}activate/`);
}

/** PATCH /api/accounts/users/:id/deactivate/ */
export function deactivateUser(userId: number): Promise<ApiResponse<User>> {
  return apiPatch<User>(`${API.user(userId)}deactivate/`);
}

// ---------------------------------------------------------------------------
// Roles
// ---------------------------------------------------------------------------

/** GET /api/accounts/roles/ */
export function listRoles(): Promise<ApiResponse<RoleListItem[]>> {
  return apiGet<RoleListItem[]>(API.ROLES);
}

/** GET /api/accounts/roles/:id/ */
export function getRole(id: number): Promise<ApiResponse<RoleDetailFull>> {
  return apiGet<RoleDetailFull>(API.role(id));
}

/** POST /api/accounts/roles/ */
export function createRole(
  payload: RoleCreatePayload,
): Promise<ApiResponse<RoleDetailFull>> {
  return apiPost<RoleDetailFull>(API.ROLES, payload);
}

/** PUT /api/accounts/roles/:id/ (full update) */
export function updateRole(
  id: number,
  payload: RoleUpdatePayload,
): Promise<ApiResponse<RoleDetailFull>> {
  return apiPut<RoleDetailFull>(API.role(id), payload);
}

/** PATCH /api/accounts/roles/:id/ (partial update) */
export function patchRole(
  id: number,
  payload: RoleUpdatePayload,
): Promise<ApiResponse<RoleDetailFull>> {
  return apiPatch<RoleDetailFull>(API.role(id), payload);
}

/** DELETE /api/accounts/roles/:id/ */
export function deleteRole(id: number): Promise<ApiResponse<void>> {
  return apiDelete<void>(API.role(id));
}

/** POST /api/accounts/roles/:id/assign-permissions/ */
export function assignPermissions(
  roleId: number,
  payload: AssignPermissionsRequest,
): Promise<ApiResponse<RoleDetailFull>> {
  return apiPost<RoleDetailFull>(
    `${API.role(roleId)}assign-permissions/`,
    payload,
  );
}

// ---------------------------------------------------------------------------
// Permissions
// ---------------------------------------------------------------------------

/** GET /api/accounts/permissions/ */
export function listPermissions(): Promise<ApiResponse<PermissionItem[]>> {
  return apiGet<PermissionItem[]>(API.PERMISSIONS);
}

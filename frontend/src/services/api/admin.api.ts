/**
 * Admin API service — roles & user management.
 *
 * Raw backend responses are normalised so the rest of the app always
 * receives `role` as a `RoleListItem | null` object (not a bare integer FK).
 */
import api from './axios.instance';
import type { PaginatedResponse, ListParams } from '@/types/api.types';
import type {
  Role,
  RoleListItem,
  RoleCreateRequest,
  RoleUpdateRequest,
  AssignPermissionsRequest,
  UserListItem,
  User,
  AssignRoleRequest,
  Permission,
  RawUserListItem,
  RawUserDetail,
} from '@/types/user.types';
import { normalizeUserListItem, normalizeUser } from '@/types/user.types';

/* ── Roles ───────────────────────────────────────────────────────── */

export const rolesApi = {
  list: () =>
    api.get<RoleListItem[]>('/accounts/roles/').then((r) => r.data),

  detail: (id: number) =>
    api.get<Role>(`/accounts/roles/${id}/`).then((r) => r.data),

  create: (data: RoleCreateRequest) =>
    api.post<Role>('/accounts/roles/', data).then((r) => r.data),

  update: (id: number, data: RoleUpdateRequest) =>
    api.patch<Role>(`/accounts/roles/${id}/`, data).then((r) => r.data),

  delete: (id: number) =>
    api.delete(`/accounts/roles/${id}/`).then((r) => r.data),

  assignPermissions: (id: number, data: AssignPermissionsRequest) =>
    api
      .post<Role>(`/accounts/roles/${id}/assign-permissions/`, data)
      .then((r) => r.data),
};

/* ── Users ───────────────────────────────────────────────────────── */

export const usersApi = {
  list: (params?: ListParams) =>
    api
      .get<PaginatedResponse<RawUserListItem>>('/accounts/users/', { params })
      .then((r) => ({
        ...r.data,
        results: r.data.results.map(normalizeUserListItem),
      })),

  detail: (id: number) =>
    api
      .get<RawUserDetail>(`/accounts/users/${id}/`)
      .then((r) => normalizeUser(r.data)),

  assignRole: (id: number, data: AssignRoleRequest) =>
    api
      .patch<RawUserDetail>(`/accounts/users/${id}/assign-role/`, data)
      .then((r) => normalizeUser(r.data)),

  activate: (id: number) =>
    api
      .patch<RawUserDetail>(`/accounts/users/${id}/activate/`)
      .then((r) => normalizeUser(r.data)),

  deactivate: (id: number) =>
    api
      .patch<RawUserDetail>(`/accounts/users/${id}/deactivate/`)
      .then((r) => normalizeUser(r.data)),
};

/* ── Permissions ─────────────────────────────────────────────────── */

export const permissionsApi = {
  list: () =>
    api.get<Permission[]>('/accounts/permissions/').then((r) => r.data),
};

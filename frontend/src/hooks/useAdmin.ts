/**
 * React Query hooks for Admin Panel functionality.
 *
 * Provides:
 *   - useUsers          — list users with filters
 *   - useUserDetail     — single user detail
 *   - useUserActions    — activate/deactivate/assign-role mutations
 *   - useRoles          — list roles
 *   - useRoleDetail     — single role with permissions
 *   - useRoleActions    — create/update/delete role + assign permissions
 *   - usePermissions    — list all available permissions
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as adminApi from "../api/admin";
import type { UserFilters, RoleCreatePayload, RoleUpdatePayload } from "../types/admin";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const ADMIN_USERS_KEY = ["admin", "users"] as const;
export const ADMIN_USER_KEY = (id: number) => ["admin", "users", id] as const;
export const ADMIN_ROLES_KEY = ["admin", "roles"] as const;
export const ADMIN_ROLE_KEY = (id: number) => ["admin", "roles", id] as const;
export const ADMIN_PERMISSIONS_KEY = ["admin", "permissions"] as const;

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export function useUsers(filters?: UserFilters) {
  return useQuery({
    queryKey: [...ADMIN_USERS_KEY, filters],
    queryFn: async () => {
      const res = await adminApi.listUsers(filters);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
  });
}

export function useUserDetail(id: number | null) {
  return useQuery({
    queryKey: ADMIN_USER_KEY(id ?? 0),
    queryFn: async () => {
      if (id === null) throw new Error("No user selected");
      const res = await adminApi.getUser(id);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    enabled: id !== null,
  });
}

export function useUserActions() {
  const qc = useQueryClient();

  const assignRole = useMutation({
    mutationFn: ({ userId, roleId }: { userId: number; roleId: number }) =>
      adminApi.assignRole(userId, { role_id: roleId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_USERS_KEY });
    },
  });

  const activate = useMutation({
    mutationFn: (userId: number) => adminApi.activateUser(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_USERS_KEY });
    },
  });

  const deactivate = useMutation({
    mutationFn: (userId: number) => adminApi.deactivateUser(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_USERS_KEY });
    },
  });

  return { assignRole, activate, deactivate };
}

// ---------------------------------------------------------------------------
// Roles
// ---------------------------------------------------------------------------

export function useRoles() {
  return useQuery({
    queryKey: ADMIN_ROLES_KEY,
    queryFn: async () => {
      const res = await adminApi.listRoles();
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
  });
}

export function useRoleDetail(id: number | null) {
  return useQuery({
    queryKey: ADMIN_ROLE_KEY(id ?? 0),
    queryFn: async () => {
      if (id === null) throw new Error("No role selected");
      const res = await adminApi.getRole(id);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    enabled: id !== null,
  });
}

export function useRoleActions() {
  const qc = useQueryClient();

  const create = useMutation({
    mutationFn: (payload: RoleCreatePayload) => adminApi.createRole(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_ROLES_KEY });
    },
  });

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: RoleUpdatePayload }) =>
      adminApi.updateRole(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_ROLES_KEY });
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => adminApi.deleteRole(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_ROLES_KEY });
    },
  });

  const assignPerms = useMutation({
    mutationFn: ({
      roleId,
      permissionIds,
    }: {
      roleId: number;
      permissionIds: number[];
    }) => adminApi.assignPermissions(roleId, { permission_ids: permissionIds }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_ROLES_KEY });
    },
  });

  return { create, update, remove, assignPerms };
}

// ---------------------------------------------------------------------------
// Permissions
// ---------------------------------------------------------------------------

export function usePermissions() {
  return useQuery({
    queryKey: ADMIN_PERMISSIONS_KEY,
    queryFn: async () => {
      const res = await adminApi.listPermissions();
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    staleTime: 5 * 60 * 1000, // permissions rarely change
  });
}

import { useState, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import { LoadingSpinner, ErrorState, EmptyState, Skeleton } from "../../components/ui";
import { useAuth } from "../../auth";
import { useUsers, useUserDetail, useUserActions, useRoles } from "../../hooks/useAdmin";
import { useDebounce } from "../../hooks/useDebounce";
import type { UserListItem, UserFilters } from "../../types/admin";
import type { User } from "../../types/auth";
import type { RoleListItem } from "../../types/admin";
import css from "./UserManagementPage.module.css";

/**
 * User management sub-page for admin panel.
 *
 * Features:
 *   - Search / filter users
 *   - View user details (slide panel)
 *   - Assign role to user
 *   - Activate / deactivate user
 */
export default function UserManagementPage() {
  const { hierarchyLevel } = useAuth();

  if (hierarchyLevel < 100) {
    return (
      <div className={css.container}>
        <h1>Access Denied</h1>
        <p>Only System Administrators can manage users.</p>
      </div>
    );
  }

  return <UserManagementContent />;
}

// ---------------------------------------------------------------------------
// Content
// ---------------------------------------------------------------------------

function UserManagementContent() {
  // Filters
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<number | undefined>(undefined);
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(undefined);
  const debouncedSearch = useDebounce(search, 300);

  const filters: UserFilters = {
    search: debouncedSearch || undefined,
    role: roleFilter,
    is_active: activeFilter,
  };

  const { data: users, isLoading, error, refetch } = useUsers(filters);
  const { data: roles } = useRoles();

  // Detail panel
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);

  // Toast
  const [toast, setToast] = useState<{ message: string; isError?: boolean } | null>(null);

  const showToast = useCallback((message: string, isError = false) => {
    setToast({ message, isError });
    setTimeout(() => setToast(null), 3000);
  }, []);

  const clearFilters = useCallback(() => {
    setSearch("");
    setRoleFilter(undefined);
    setActiveFilter(undefined);
  }, []);

  return (
    <div className={css.container}>
      {/* Header */}
      <div className={css.header}>
        <div>
          <Link to="/admin" className={css.backLink}>
            ← Admin Panel
          </Link>
          <h1>User Management</h1>
        </div>
      </div>

      {/* Toolbar */}
      <div className={css.toolbar}>
        <input
          className={css.searchInput}
          type="text"
          placeholder="Search by name, email, username…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className={css.filterSelect}
          value={roleFilter ?? ""}
          onChange={(e) =>
            setRoleFilter(e.target.value ? Number(e.target.value) : undefined)
          }
        >
          <option value="">All Roles</option>
          {roles?.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
        <select
          className={css.filterSelect}
          value={activeFilter === undefined ? "" : String(activeFilter)}
          onChange={(e) =>
            setActiveFilter(
              e.target.value === "" ? undefined : e.target.value === "true",
            )
          }
        >
          <option value="">All Status</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
        <button className={css.clearBtn} onClick={clearFilters} type="button">
          Clear
        </button>
      </div>

      {/* Count */}
      {users && (
        <p className={css.count}>
          Showing {users.length} user{users.length !== 1 ? "s" : ""}
        </p>
      )}

      {/* Table */}
      {isLoading ? (
        <div>
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} height={42} />
          ))}
        </div>
      ) : error ? (
        <ErrorState
          message="Failed to load users."
          onRetry={() => { refetch(); }}
        />
      ) : !users || users.length === 0 ? (
        <EmptyState
          title="No users found"
          description="Try adjusting your search or filters."
          icon="👤"
          action={{ label: "Clear filters", onClick: clearFilters }}
        />
      ) : (
        <div className={css.tableWrapper}>
          <table className={css.table}>
            <thead>
              <tr>
                <th>Username</th>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <UserRow
                  key={u.id}
                  user={u}
                  onSelect={() => setSelectedUserId(u.id)}
                  onToast={showToast}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail panel */}
      {selectedUserId !== null && (
        <>
          <div
            className={css.detailOverlay}
            onClick={() => setSelectedUserId(null)}
          />
          <UserDetailPanel
            userId={selectedUserId}
            roles={roles ?? []}
            onClose={() => setSelectedUserId(null)}
            onToast={showToast}
          />
        </>
      )}

      {/* Toast */}
      {toast && (
        <div className={toast.isError ? css.toastError : css.toast}>
          {toast.message}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// User row
// ---------------------------------------------------------------------------

function UserRow({
  user,
  onSelect,
  onToast,
}: {
  user: UserListItem;
  onSelect: () => void;
  onToast: (msg: string, isError?: boolean) => void;
}) {
  const { activate, deactivate } = useUserActions();

  const handleToggleActive = async () => {
    if (user.is_active) {
      const res = await deactivate.mutateAsync(user.id);
      if (res.ok) {
        onToast(`${user.username} deactivated`);
      } else {
        onToast(res.error.message, true);
      }
    } else {
      const res = await activate.mutateAsync(user.id);
      if (res.ok) {
        onToast(`${user.username} activated`);
      } else {
        onToast(res.error.message, true);
      }
    }
  };

  return (
    <tr>
      <td>
        <button
          onClick={onSelect}
          style={{
            background: "none",
            border: "none",
            color: "#3498db",
            cursor: "pointer",
            fontSize: "0.9rem",
            padding: 0,
            textAlign: "left",
          }}
        >
          {user.username}
        </button>
      </td>
      <td>
        {user.first_name} {user.last_name}
      </td>
      <td>{user.email}</td>
      <td>
        {user.role_name ? (
          <span className={css.roleBadge}>{user.role_name}</span>
        ) : (
          <span style={{ color: "#999" }}>—</span>
        )}
      </td>
      <td>
        <span className={user.is_active ? css.badgeActive : css.badgeInactive}>
          {user.is_active ? "Active" : "Inactive"}
        </span>
      </td>
      <td>
        <div className={css.actions}>
          <button
            className={css.actionBtn}
            onClick={onSelect}
            type="button"
          >
            View
          </button>
          <button
            className={user.is_active ? css.deactivateBtn : css.activateBtn}
            onClick={handleToggleActive}
            disabled={activate.isPending || deactivate.isPending}
            type="button"
          >
            {user.is_active ? "Deactivate" : "Activate"}
          </button>
        </div>
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// User detail panel (slide-in)
// ---------------------------------------------------------------------------

function UserDetailPanel({
  userId,
  roles,
  onClose,
  onToast,
}: {
  userId: number;
  roles: RoleListItem[];
  onClose: () => void;
  onToast: (msg: string, isError?: boolean) => void;
}) {
  const { data: user, isLoading, error } = useUserDetail(userId);
  const { assignRole, activate, deactivate } = useUserActions();

  // Derive initial role selection from user data (avoids setState-in-effect)
  const initialRoleId = useMemo<number | "">(
    () => (user?.role_detail ? user.role_detail.id : ""),
    [user],
  );
  const [selectedRoleId, setSelectedRoleId] = useState<number | "">(initialRoleId);

  // Sync when user data changes (different user selected)
  const userRoleId = user?.role_detail?.id ?? "";
  if (selectedRoleId !== userRoleId && userRoleId !== "") {
    setSelectedRoleId(userRoleId);
  }

  const handleAssignRole = async () => {
    if (selectedRoleId === "") return;
    const res = await assignRole.mutateAsync({
      userId,
      roleId: Number(selectedRoleId),
    });
    if (res.ok) {
      onToast("Role assigned successfully");
    } else {
      onToast(res.error.message, true);
    }
  };

  const handleToggleActive = async (u: User) => {
    if (u.is_active) {
      const res = await deactivate.mutateAsync(u.id);
      if (res.ok) onToast(`${u.username} deactivated`);
      else onToast(res.error.message, true);
    } else {
      const res = await activate.mutateAsync(u.id);
      if (res.ok) onToast(`${u.username} activated`);
      else onToast(res.error.message, true);
    }
  };

  return (
    <div className={css.detailPanel}>
      <div className={css.detailHeader}>
        <h2>User Details</h2>
        <button className={css.closeBtn} onClick={onClose} type="button">
          ×
        </button>
      </div>

      {isLoading ? (
        <LoadingSpinner label="Loading user…" />
      ) : error ? (
        <ErrorState message="Failed to load user details." />
      ) : user ? (
        <>
          <div className={css.detailRow}>
            <span className={css.detailLabel}>Username</span>
            <span className={css.detailValue}>{user.username}</span>
          </div>
          <div className={css.detailRow}>
            <span className={css.detailLabel}>Full Name</span>
            <span className={css.detailValue}>
              {user.first_name} {user.last_name}
            </span>
          </div>
          <div className={css.detailRow}>
            <span className={css.detailLabel}>Email</span>
            <span className={css.detailValue}>{user.email}</span>
          </div>
          <div className={css.detailRow}>
            <span className={css.detailLabel}>Phone</span>
            <span className={css.detailValue}>{user.phone_number}</span>
          </div>
          <div className={css.detailRow}>
            <span className={css.detailLabel}>National ID</span>
            <span className={css.detailValue}>{user.national_id}</span>
          </div>
          <div className={css.detailRow}>
            <span className={css.detailLabel}>Role</span>
            <span className={css.detailValue}>
              {user.role_detail ? (
                <span className={css.roleBadge}>{user.role_detail.name}</span>
              ) : (
                "Unassigned"
              )}
            </span>
          </div>
          <div className={css.detailRow}>
            <span className={css.detailLabel}>Status</span>
            <span className={css.detailValue}>
              <span
                className={user.is_active ? css.badgeActive : css.badgeInactive}
              >
                {user.is_active ? "Active" : "Inactive"}
              </span>
            </span>
          </div>
          <div className={css.detailRow}>
            <span className={css.detailLabel}>Joined</span>
            <span className={css.detailValue}>
              {new Date(user.date_joined).toLocaleDateString()}
            </span>
          </div>
          <div className={css.detailRow}>
            <span className={css.detailLabel}>Permissions</span>
            <span className={css.detailValue}>
              {user.permissions.length > 0
                ? `${user.permissions.length} permission(s)`
                : "None"}
            </span>
          </div>

          {/* Quick actions */}
          <div style={{ marginTop: "1rem" }}>
            <button
              className={user.is_active ? css.deactivateBtn : css.activateBtn}
              onClick={() => handleToggleActive(user)}
              disabled={activate.isPending || deactivate.isPending}
              type="button"
            >
              {user.is_active ? "Deactivate User" : "Activate User"}
            </button>
          </div>

          {/* Role assignment */}
          <div className={css.roleAssign}>
            <h3>Assign Role</h3>
            <div className={css.roleAssignRow}>
              <select
                className={css.roleSelect}
                value={selectedRoleId}
                onChange={(e) =>
                  setSelectedRoleId(
                    e.target.value ? Number(e.target.value) : "",
                  )
                }
              >
                <option value="">Select role…</option>
                {roles.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} (Level {r.hierarchy_level})
                  </option>
                ))}
              </select>
              <button
                className={css.assignBtn}
                onClick={handleAssignRole}
                disabled={selectedRoleId === "" || assignRole.isPending}
                type="button"
              >
                {assignRole.isPending ? "Saving…" : "Assign"}
              </button>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}

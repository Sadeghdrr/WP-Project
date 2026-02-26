import { useState, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import { LoadingSpinner, ErrorState, EmptyState, Skeleton } from "../../components/ui";
import { useAuth } from "../../auth";
import {
  useRoles,
  useRoleDetail,
  useRoleActions,
  usePermissions,
} from "../../hooks/useAdmin";
import type {
  RoleListItem,
  RoleCreatePayload,
  PermissionItem,
} from "../../types/admin";
import css from "./RoleManagementPage.module.css";

/**
 * Role management sub-page for admin panel.
 *
 * Features:
 *   - List all roles with hierarchy badge
 *   - Create new role
 *   - Edit existing role (name, description, hierarchy level)
 *   - Delete role (only if no users assigned)
 *   - Assign permissions to role
 */
export default function RoleManagementPage() {
  const { hierarchyLevel } = useAuth();

  if (hierarchyLevel < 100) {
    return (
      <div className={css.container}>
        <h1>Access Denied</h1>
        <p>Only System Administrators can manage roles.</p>
      </div>
    );
  }

  return <RoleManagementContent />;
}

// ---------------------------------------------------------------------------
// Content
// ---------------------------------------------------------------------------

function RoleManagementContent() {
  const { data: roles, isLoading, error, refetch } = useRoles();
  const { create, update, remove } = useRoleActions();

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editRoleId, setEditRoleId] = useState<number | null>(null);
  const [permsRoleId, setPermsRoleId] = useState<number | null>(null);
  const [deleteRoleId, setDeleteRoleId] = useState<number | null>(null);

  // Toast
  const [toast, setToast] = useState<{ message: string; isError?: boolean } | null>(null);
  const showToast = useCallback((message: string, isError = false) => {
    setToast({ message, isError });
    setTimeout(() => setToast(null), 3000);
  }, []);

  const handleCreate = async (payload: RoleCreatePayload) => {
    const res = await create.mutateAsync(payload);
    if (res.ok) {
      showToast(`Role "${payload.name}" created`);
      setShowCreateModal(false);
    } else {
      showToast(res.error.message, true);
    }
  };

  const handleUpdate = async (id: number, payload: RoleCreatePayload) => {
    const res = await update.mutateAsync({ id, payload });
    if (res.ok) {
      showToast("Role updated");
      setEditRoleId(null);
    } else {
      showToast(res.error.message, true);
    }
  };

  const handleDelete = async () => {
    if (deleteRoleId === null) return;
    const res = await remove.mutateAsync(deleteRoleId);
    if (res.ok) {
      showToast("Role deleted");
      setDeleteRoleId(null);
    } else {
      showToast(res.error.message, true);
    }
  };

  const deletingRole = roles?.find((r) => r.id === deleteRoleId);

  return (
    <div className={css.container}>
      {/* Header */}
      <div className={css.header}>
        <div>
          <Link to="/admin" className={css.backLink}>
            ← Admin Panel
          </Link>
          <h1>Role Management</h1>
        </div>
        <button
          className={css.createBtn}
          onClick={() => setShowCreateModal(true)}
          type="button"
        >
          + New Role
        </button>
      </div>

      {/* List */}
      {isLoading ? (
        <div className={css.roleGrid}>
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} height={140} />
          ))}
        </div>
      ) : error ? (
        <ErrorState message="Failed to load roles." onRetry={() => { refetch(); }} />
      ) : !roles || roles.length === 0 ? (
        <EmptyState
          title="No roles"
          description="Create a role to get started."
          icon="🛡️"
        />
      ) : (
        <div className={css.roleGrid}>
          {roles.map((role) => (
            <RoleCard
              key={role.id}
              role={role}
              onEdit={() => setEditRoleId(role.id)}
              onPerms={() => setPermsRoleId(role.id)}
              onDelete={() => setDeleteRoleId(role.id)}
            />
          ))}
        </div>
      )}

      {/* Create modal */}
      {showCreateModal && (
        <RoleFormModal
          title="Create Role"
          onSubmit={handleCreate}
          onClose={() => setShowCreateModal(false)}
          isPending={create.isPending}
        />
      )}

      {/* Edit modal */}
      {editRoleId !== null && (
        <EditRoleModal
          roleId={editRoleId}
          onSubmit={(payload) => handleUpdate(editRoleId, payload)}
          onClose={() => setEditRoleId(null)}
          isPending={update.isPending}
        />
      )}

      {/* Permissions modal */}
      {permsRoleId !== null && (
        <PermissionsModal
          roleId={permsRoleId}
          onClose={() => setPermsRoleId(null)}
          onToast={showToast}
        />
      )}

      {/* Delete confirm */}
      {deleteRoleId !== null && (
        <div
          className={css.modalOverlay}
          onClick={() => setDeleteRoleId(null)}
        >
          <div className={css.modal} onClick={(e) => e.stopPropagation()}>
            <div className={css.modalHeader}>
              <h2>Delete Role</h2>
              <button
                className={css.closeBtn}
                onClick={() => setDeleteRoleId(null)}
                type="button"
              >
                ×
              </button>
            </div>
            <p className={css.confirmText}>
              Are you sure you want to delete the role{" "}
              <strong>{deletingRole?.name}</strong>? This action cannot be
              undone. The role must not have any assigned users.
            </p>
            <div className={css.formActions}>
              <button
                className={css.cancelBtn}
                onClick={() => setDeleteRoleId(null)}
                type="button"
              >
                Cancel
              </button>
              <button
                className={css.dangerBtn}
                onClick={handleDelete}
                disabled={remove.isPending}
                type="button"
              >
                {remove.isPending ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
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
// Role card
// ---------------------------------------------------------------------------

function RoleCard({
  role,
  onEdit,
  onPerms,
  onDelete,
}: {
  role: RoleListItem;
  onEdit: () => void;
  onPerms: () => void;
  onDelete: () => void;
}) {
  return (
    <div className={css.roleCard}>
      <div className={css.roleCardHeader}>
        <h3 className={css.roleName}>{role.name}</h3>
        <span className={css.hierarchyBadge}>
          Level {role.hierarchy_level}
        </span>
      </div>
      {role.description && (
        <p className={css.roleDescription}>{role.description}</p>
      )}
      <div className={css.roleActions}>
        <button className={css.editBtn} onClick={onEdit} type="button">
          Edit
        </button>
        <button className={css.permsBtn} onClick={onPerms} type="button">
          Permissions
        </button>
        <button className={css.deleteBtn} onClick={onDelete} type="button">
          Delete
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Role form modal (create / edit shared)
// ---------------------------------------------------------------------------

function RoleFormModal({
  title,
  initial,
  onSubmit,
  onClose,
  isPending,
}: {
  title: string;
  initial?: { name: string; description: string; hierarchy_level: number };
  onSubmit: (payload: RoleCreatePayload) => void;
  onClose: () => void;
  isPending: boolean;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [hierarchy, setHierarchy] = useState(
    initial?.hierarchy_level ?? 0,
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      name: name.trim(),
      description: description.trim(),
      hierarchy_level: hierarchy,
    });
  };

  return (
    <div className={css.modalOverlay} onClick={onClose}>
      <form
        className={css.modal}
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <div className={css.modalHeader}>
          <h2>{title}</h2>
          <button className={css.closeBtn} onClick={onClose} type="button">
            ×
          </button>
        </div>

        <div className={css.field}>
          <label htmlFor="role-name">Role Name</label>
          <input
            id="role-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="e.g. Detective"
          />
        </div>

        <div className={css.field}>
          <label htmlFor="role-desc">Description</label>
          <textarea
            id="role-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional role description"
          />
        </div>

        <div className={css.field}>
          <label htmlFor="role-hierarchy">Hierarchy Level</label>
          <input
            id="role-hierarchy"
            type="number"
            min={0}
            value={hierarchy}
            onChange={(e) => setHierarchy(Number(e.target.value))}
            required
          />
        </div>

        <div className={css.formActions}>
          <button className={css.cancelBtn} onClick={onClose} type="button">
            Cancel
          </button>
          <button
            className={css.submitBtn}
            type="submit"
            disabled={!name.trim() || isPending}
          >
            {isPending ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Edit role modal (fetches detail first)
// ---------------------------------------------------------------------------

function EditRoleModal({
  roleId,
  onSubmit,
  onClose,
  isPending,
}: {
  roleId: number;
  onSubmit: (payload: RoleCreatePayload) => void;
  onClose: () => void;
  isPending: boolean;
}) {
  const { data: role, isLoading } = useRoleDetail(roleId);

  if (isLoading || !role) {
    return (
      <div className={css.modalOverlay} onClick={onClose}>
        <div className={css.modal} onClick={(e) => e.stopPropagation()}>
          <LoadingSpinner label="Loading role…" />
        </div>
      </div>
    );
  }

  return (
    <RoleFormModal
      title="Edit Role"
      initial={{
        name: role.name,
        description: role.description,
        hierarchy_level: role.hierarchy_level,
      }}
      onSubmit={onSubmit}
      onClose={onClose}
      isPending={isPending}
    />
  );
}

// ---------------------------------------------------------------------------
// Permissions assignment modal
// ---------------------------------------------------------------------------

function PermissionsModal({
  roleId,
  onClose,
  onToast,
}: {
  roleId: number;
  onClose: () => void;
  onToast: (msg: string, isError?: boolean) => void;
}) {
  const { data: role, isLoading: roleLoading } = useRoleDetail(roleId);
  const { data: allPerms, isLoading: permsLoading } = usePermissions();
  const { assignPerms } = useRoleActions();

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [initialized, setInitialized] = useState(false);
  const [permSearch, setPermSearch] = useState("");

  // Initialize selection from role's current permissions
  if (role && !initialized) {
    setSelected(new Set(role.permissions));
    setInitialized(true);
  }

  // Group permissions by app_label
  const grouped = useMemo(() => {
    if (!allPerms) return {};
    const groups: Record<string, PermissionItem[]> = {};
    const filter = permSearch.toLowerCase();
    for (const p of allPerms) {
      if (filter && !p.full_codename.toLowerCase().includes(filter) && !p.name.toLowerCase().includes(filter)) {
        continue;
      }
      const app = p.full_codename.split(".")[0] ?? "other";
      if (!groups[app]) groups[app] = [];
      groups[app].push(p);
    }
    return groups;
  }, [allPerms, permSearch]);

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (!allPerms) return;
    setSelected(new Set(allPerms.map((p) => p.id)));
  };

  const deselectAll = () => {
    setSelected(new Set());
  };

  const handleSave = async () => {
    const res = await assignPerms.mutateAsync({
      roleId,
      permissionIds: Array.from(selected),
    });
    if (res.ok) {
      onToast("Permissions updated");
      onClose();
    } else {
      onToast(res.error.message, true);
    }
  };

  const isLoading = roleLoading || permsLoading;

  return (
    <div className={css.modalOverlay} onClick={onClose}>
      <div className={css.modalWide} onClick={(e) => e.stopPropagation()}>
        <div className={css.modalHeader}>
          <h2>
            Permissions — {role?.name ?? "Loading…"}
          </h2>
          <button className={css.closeBtn} onClick={onClose} type="button">
            ×
          </button>
        </div>

        {isLoading ? (
          <LoadingSpinner label="Loading permissions…" />
        ) : (
          <div className={css.permSection}>
            <div className={css.selectAllRow}>
              <input
                className={css.permSearch}
                type="text"
                placeholder="Filter permissions…"
                value={permSearch}
                onChange={(e) => setPermSearch(e.target.value)}
              />
              <button
                className={css.selectAllBtn}
                onClick={selectAll}
                type="button"
              >
                Select All
              </button>
              <button
                className={css.selectAllBtn}
                onClick={deselectAll}
                type="button"
              >
                Deselect All
              </button>
            </div>

            {Object.entries(grouped)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([app, perms]) => (
                <div key={app} className={css.permGroup}>
                  <h4 className={css.permGroupTitle}>{app}</h4>
                  <div className={css.permList}>
                    {perms.map((p) => (
                      <label key={p.id} className={css.permItem}>
                        <input
                          type="checkbox"
                          checked={selected.has(p.id)}
                          onChange={() => toggle(p.id)}
                        />
                        <span className={css.permItemLabel}>
                          {p.codename}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}

            <div className={css.formActions}>
              <span style={{ fontSize: "0.85rem", color: "#888", flex: 1 }}>
                {selected.size} permission{selected.size !== 1 ? "s" : ""}{" "}
                selected
              </span>
              <button
                className={css.cancelBtn}
                onClick={onClose}
                type="button"
              >
                Cancel
              </button>
              <button
                className={css.submitBtn}
                onClick={handleSave}
                disabled={assignPerms.isPending}
                type="button"
              >
                {assignPerms.isPending ? "Saving…" : "Save Permissions"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

import { Link } from "react-router-dom";
import { LoadingSpinner, ErrorState } from "../../components/ui";
import { useAuth } from "../../auth";
import { useUsers, useRoles } from "../../hooks/useAdmin";
import css from "./AdminPage.module.css";

/**
 * Admin Panel overview page.
 * Requirement (§7 CP2): Non-Django admin with similar functionality (200 pts).
 *
 * Accessible only to users with the `accounts.can_manage_users` permission.
 * Shows quick stats and navigation to Users / Roles sub-pages.
 */
export default function AdminPage() {
  const { user, permissionSet } = useAuth();

  // Guard: users without admin permission see a denial message
  if (!permissionSet.has("accounts.can_manage_users")) {
    return (
      <div className={css.accessDenied}>
        <h2>Access Denied</h2>
        <p>
          You do not have permission to access the Admin Panel.
          Only System Administrators can manage users and roles.
        </p>
      </div>
    );
  }

  return <AdminOverview currentUser={user?.username ?? "Admin"} />;
}

// ---------------------------------------------------------------------------
// Inner component — only rendered for admins
// ---------------------------------------------------------------------------

function AdminOverview({ currentUser }: { currentUser: string }) {
  const { data: users, isLoading: usersLoading, error: usersErr, refetch: refetchUsers } = useUsers();
  const { data: roles, isLoading: rolesLoading, error: rolesErr, refetch: refetchRoles } = useRoles();

  const isLoading = usersLoading || rolesLoading;
  const error = usersErr || rolesErr;

  return (
    <div className={css.container}>
      <div className={css.header}>
        <h1>Admin Panel</h1>
        <p className={css.subtitle}>
          Welcome, {currentUser}. Manage users, roles, and permissions.
        </p>
      </div>

      {/* Quick stats */}
      {isLoading ? (
        <LoadingSpinner label="Loading stats…" />
      ) : error ? (
        <ErrorState message="Failed to load admin overview data." onRetry={() => { refetchUsers(); refetchRoles(); }} />
      ) : (
        <>
          <div className={css.statsRow}>
            <div className={css.statCard}>
              <p className={css.statValue}>{users?.length ?? 0}</p>
              <p className={css.statLabel}>Total Users</p>
            </div>
            <div className={css.statCard}>
              <p className={css.statValue}>
                {users?.filter((u) => u.is_active).length ?? 0}
              </p>
              <p className={css.statLabel}>Active Users</p>
            </div>
            <div className={css.statCard}>
              <p className={css.statValue}>
                {users?.filter((u) => !u.is_active).length ?? 0}
              </p>
              <p className={css.statLabel}>Inactive Users</p>
            </div>
            <div className={css.statCard}>
              <p className={css.statValue}>{roles?.length ?? 0}</p>
              <p className={css.statLabel}>Roles</p>
            </div>
          </div>

          {/* Navigation cards */}
          <div className={css.navGrid}>
            <Link to="/admin/users" className={css.navCard}>
              <div className={css.navIcon}>👥</div>
              <h3>User Management</h3>
              <p>
                List, search, and filter users. Activate or deactivate accounts
                and assign roles.
              </p>
            </Link>

            <Link to="/admin/roles" className={css.navCard}>
              <div className={css.navIcon}>🛡️</div>
              <h3>Role Management</h3>
              <p>
                Create, modify, and delete roles. Assign permissions to control
                access across the system.
              </p>
            </Link>
          </div>
        </>
      )}
    </div>
  );
}

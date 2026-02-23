/**
 * Sidebar — dynamic navigation built from a permission-driven config.
 *
 * Each nav item declares which permission codename(s) it requires.
 * Items the user cannot access are silently hidden.
 * The configuration lives here so adding a new module is a one-liner.
 */
import { NavLink } from 'react-router-dom';
import { usePermissions } from '@/hooks/usePermissions';
import { useAuth } from '@/hooks/useAuth';

/* ── Navigation config (permission-driven, no hardcoded role names) ─ */

export interface NavItem {
  label: string;
  to: string;
  /** If empty, visible to all authenticated users. */
  permissions: string[];
  /** If true, ALL permissions are required (default: any). */
  requireAll?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', to: '/dashboard', permissions: [] },
  { label: 'Cases', to: '/cases', permissions: ['view_case'] },
  { label: 'Evidence', to: '/evidence', permissions: ['view_evidence'] },
  { label: 'Suspects', to: '/suspects', permissions: ['view_suspect'] },
  { label: 'Board', to: '/boards', permissions: ['view_detectiveboard'] },
  { label: 'Reports', to: '/reports', permissions: ['can_forward_to_judiciary'] },
  { label: 'Bounty Tips', to: '/bounty', permissions: [] },
  { label: 'Most Wanted', to: '/most-wanted', permissions: [] },
  { label: 'Admin', to: '/admin', permissions: ['add_role', 'change_role'] },
];

/* ── Component ───────────────────────────────────────────────────── */

interface SidebarProps {
  collapsed?: boolean;
}

export const Sidebar = ({ collapsed = false }: SidebarProps) => {
  const { hasAnyPermission, hasAllPermissions } = usePermissions();
  const { user } = useAuth();

  const visible = NAV_ITEMS.filter((item) => {
    if (item.permissions.length === 0) return true;
    return item.requireAll
      ? hasAllPermissions(item.permissions)
      : hasAnyPermission(item.permissions);
  });

  return (
    <aside className={`sidebar ${collapsed ? 'sidebar--collapsed' : ''}`}>
      <div className="sidebar__brand">
        {!collapsed && <span>LAPD System</span>}
      </div>

      <nav className="sidebar__nav">
        {visible.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `sidebar__link ${isActive ? 'sidebar__link--active' : ''}`
            }
          >
            <span className="sidebar__label">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {user && (
        <div className="sidebar__footer">
          <span className="sidebar__user">
            {user.first_name} {user.last_name}
          </span>
          {user.role && (
            <span className="sidebar__role">{user.role.name}</span>
          )}
        </div>
      )}
    </aside>
  );
};

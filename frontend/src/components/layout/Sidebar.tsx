/**
 * Sidebar — dynamic navigation driven by the centralised module registry.
 *
 * Navigation items are derived from dashboardModules.ts via
 * useDashboardModules. The "Dashboard" link is always shown as the
 * first item; the remaining items come from the filtered registry.
 *
 * Adding a new module to the registry automatically adds it to the
 * sidebar (unless showInSidebar is set to false).
 */
import { NavLink } from 'react-router-dom';
import { useDashboardModules } from '@/hooks/useDashboardModules';
import { useAuth } from '@/hooks/useAuth';

/* ── Component ───────────────────────────────────────────────────── */

interface SidebarProps {
  collapsed?: boolean;
}

export const Sidebar = ({ collapsed = false }: SidebarProps) => {
  const { sidebarItems } = useDashboardModules();
  const { user } = useAuth();

  return (
    <aside className={`sidebar ${collapsed ? 'sidebar--collapsed' : ''}`}>
      <div className="sidebar__brand">
        {!collapsed && <span>LAPD System</span>}
      </div>

      <nav className="sidebar__nav">
        {/* Dashboard link — always visible to authenticated users */}
        <NavLink
          to="/dashboard"
          className={({ isActive }) =>
            `sidebar__link ${isActive ? 'sidebar__link--active' : ''}`
          }
        >
          <span className="sidebar__label">Dashboard</span>
        </NavLink>

        {/* Registry-driven module links */}
        {sidebarItems.map((mod) => (
          <NavLink
            key={mod.id}
            to={mod.route}
            className={({ isActive }) =>
              `sidebar__link ${isActive ? 'sidebar__link--active' : ''}`
            }
          >
            <span className="sidebar__label">{mod.title}</span>
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

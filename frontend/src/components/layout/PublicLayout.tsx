/**
 * PublicLayout — the single app shell for all pages.
 *
 * Unauthenticated: brand + Most Wanted / Sign In / Register
 * Authenticated:   brand + all permission-visible module links + Logout
 *
 * Replaces DashboardLayout (sidebar) — the top-nav header is the sole
 * chrome for every route, keeping the UI consistent everywhere.
 */
import { NavLink, Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/Button';
import { useDashboardModules } from '@/hooks/useDashboardModules';

export const PublicLayout = () => {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const { sidebarItems } = useDashboardModules();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `public-layout__nav-link${isActive ? ' public-layout__nav-link--active' : ''}`;

  return (
    <div className="public-layout">
      <header className="public-layout__header">
        <Link to={isAuthenticated ? '/dashboard' : '/'} className="public-layout__brand">
          LAPD System
        </Link>

        <nav className="public-layout__nav">
          {isAuthenticated ? (
            <>
              <NavLink to="/dashboard" className={navClass} end>Dashboard</NavLink>
              {sidebarItems.map((mod) => (
                <NavLink key={mod.id} to={mod.route} className={navClass}>
                  {mod.title}
                </NavLink>
              ))}
              <Button variant="outline" size="sm" onClick={handleLogout}>Logout</Button>
            </>
          ) : (
            <>
              <Link to="/most-wanted">Most Wanted</Link>
              <Link to="/login">Sign In</Link>
              <Link to="/register">Register</Link>
            </>
          )}
        </nav>
      </header>

      <main className="public-layout__content">
        <Outlet />
      </main>
    </div>
  );
};

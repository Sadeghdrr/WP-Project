/**
 * PublicLayout — layout for unauthenticated public pages (Home, Most Wanted).
 * Minimal chrome: a simple header + content area. No sidebar.
 */
import { Link, Outlet } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

export const PublicLayout = () => {
  const { isAuthenticated } = useAuth();

  return (
    <div className="public-layout">
      <header className="public-layout__header">
        <Link to="/" className="public-layout__brand">
          LAPD System
        </Link>

        <nav className="public-layout__nav">
          <Link to="/most-wanted">Most Wanted</Link>
          {isAuthenticated ? (
            <Link to="/dashboard">Dashboard</Link>
          ) : (
            <>
              <Link to="/login">Login</Link>
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

/**
 * Topbar — top navigation bar with user info, notification bell,
 * logout action, and mobile sidebar toggle.
 */
import { useAuth } from '@/hooks/useAuth';
import { useNavigate } from 'react-router-dom';

interface TopbarProps {
  onToggleSidebar?: () => void;
}

export const Topbar = ({ onToggleSidebar }: TopbarProps) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <header className="topbar">
      <button
        className="topbar__menu-toggle"
        onClick={onToggleSidebar}
        aria-label="Toggle sidebar"
      >
        ☰
      </button>

      <div className="topbar__spacer" />

      {/* Notification bell — placeholder for future implementation */}
      <button className="topbar__notifications" aria-label="Notifications">
        🔔
      </button>

      {user && (
        <span className="topbar__user">
          {user.first_name} {user.last_name}
          {user.role && <small> ({user.role.name})</small>}
        </span>
      )}

      <button className="topbar__logout" onClick={handleLogout}>
        Logout
      </button>
    </header>
  );
};

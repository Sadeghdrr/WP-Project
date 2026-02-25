import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/useAuth";
import styles from "./Header.module.css";

interface HeaderProps {
  onMenuToggle?: () => void;
}

export default function Header({ onMenuToggle }: HeaderProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <header className={styles.header}>
      <Link to="/" className={styles.brand}>
        LAPD System
      </Link>

      <button
        className={styles.menuButton}
        onClick={onMenuToggle}
        aria-label="Toggle navigation"
      >
        ☰
      </button>

      <nav className={styles.nav}>
        <NavLink
          to="/dashboard"
          className={({ isActive }) =>
            `${styles.navLink} ${isActive ? styles.navLinkActive : ""}`
          }
        >
          Dashboard
        </NavLink>
        <NavLink
          to="/cases"
          className={({ isActive }) =>
            `${styles.navLink} ${isActive ? styles.navLinkActive : ""}`
          }
        >
          Cases
        </NavLink>
        <NavLink
          to="/most-wanted"
          className={({ isActive }) =>
            `${styles.navLink} ${isActive ? styles.navLinkActive : ""}`
          }
        >
          Most Wanted
        </NavLink>

        {user && (
          <>
            <span className={styles.navLink} style={{ opacity: 0.7, cursor: "default" }}>
              {user.username}
            </span>
            <button
              className={styles.navLink}
              onClick={handleLogout}
              style={{ cursor: "pointer" }}
            >
              Logout
            </button>
          </>
        )}
      </nav>
    </header>
  );
}

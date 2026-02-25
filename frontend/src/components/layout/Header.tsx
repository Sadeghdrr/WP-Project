import { Link, NavLink } from "react-router-dom";
import styles from "./Header.module.css";

interface HeaderProps {
  onMenuToggle?: () => void;
}

export default function Header({ onMenuToggle }: HeaderProps) {
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
          to="/"
          className={({ isActive }) =>
            `${styles.navLink} ${isActive ? styles.navLinkActive : ""}`
          }
          end
        >
          Home
        </NavLink>
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
      </nav>
    </header>
  );
}

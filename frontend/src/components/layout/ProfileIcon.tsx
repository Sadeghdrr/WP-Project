import { useNavigate } from "react-router-dom";
import styles from "./ProfileIcon.module.css";

/**
 * Profile icon for the top bar — navigates to /profile on click.
 *
 * Uses an inline SVG user-circle icon to avoid adding an icon library.
 * Style mirrors the NotificationBell pattern.
 */
export default function ProfileIcon() {
  const navigate = useNavigate();

  return (
    <div className={styles.profileWrapper}>
      <button
        className={styles.profileButton}
        onClick={() => navigate("/profile")}
        aria-label="My Profile"
        title="My Profile"
      >
        {/* Simple user/person SVG icon */}
        <svg
          className={styles.profileIcon}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      </button>
    </div>
  );
}

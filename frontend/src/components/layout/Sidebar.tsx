import { NavLink } from "react-router-dom";
import styles from "./Sidebar.module.css";

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

const NAV_SECTIONS = [
  {
    title: "Main",
    links: [
      { to: "/dashboard", label: "Dashboard" },
      { to: "/cases", label: "Cases" },
      { to: "/most-wanted", label: "Most Wanted" },
    ],
  },
  {
    title: "Investigation",
    links: [
      { to: "/reports", label: "Reporting" },
      { to: "/bounty-tips", label: "Bounty Tips" },
    ],
  },
  {
    title: "System",
    links: [
      { to: "/admin", label: "Admin Panel" },
      { to: "/profile", label: "Profile" },
      { to: "/notifications", label: "Notifications" },
    ],
  },
] as const;

export default function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {open && (
        <div
          className={styles.overlay}
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`${styles.sidebar} ${open ? styles.sidebarOpen : ""}`}
      >
        {NAV_SECTIONS.map((section) => (
          <div key={section.title} className={styles.section}>
            <div className={styles.sectionTitle}>{section.title}</div>
            {section.links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `${styles.link} ${isActive ? styles.linkActive : ""}`
                }
                onClick={onClose}
              >
                {link.label}
              </NavLink>
            ))}
          </div>
        ))}
      </aside>
    </>
  );
}

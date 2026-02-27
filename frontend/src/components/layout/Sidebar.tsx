import { NavLink as RouterNavLink } from "react-router-dom";
import { useAuth, canAny, P } from "../../auth";
import styles from "./Sidebar.module.css";

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

interface NavLinkItem {
  to: string;
  label: string;
  /** If set, link is only rendered when the user holds at least one of these permissions */
  permissions?: readonly string[];
}

interface NavSection {
  title: string;
  links: readonly NavLinkItem[];
}

const NAV_SECTIONS: readonly NavSection[] = [
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
      {
        to: "/admin",
        label: "Admin Panel",
        permissions: [
          P.ACCOUNTS.VIEW_USER,
          P.ACCOUNTS.VIEW_ROLE,
          P.ACCOUNTS.CHANGE_USER,
          P.ACCOUNTS.CHANGE_ROLE,
        ],
      },
      { to: "/profile", label: "Profile" },
    ],
  },
];

export default function Sidebar({ open, onClose }: SidebarProps) {
  const { permissionSet } = useAuth();

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
            {section.links.map((link) => {
              // Skip links that require permissions the user doesn't have
              if (
                link.permissions &&
                !canAny(permissionSet, [...link.permissions])
              ) {
                return null;
              }

              return (
                <RouterNavLink
                  key={link.to}
                  to={link.to}
                  className={({ isActive }: { isActive: boolean }) =>
                    `${styles.link} ${isActive ? styles.linkActive : ""}`
                  }
                  onClick={onClose}
                >
                  {link.label}
                </RouterNavLink>
              );
            })}
          </div>
        ))}
      </aside>
    </>
  );
}

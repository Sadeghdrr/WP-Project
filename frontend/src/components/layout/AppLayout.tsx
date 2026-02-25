import { useState } from "react";
import { Outlet } from "react-router-dom";
import Header from "./Header";
import Sidebar from "./Sidebar";
import styles from "./AppLayout.module.css";

/**
 * Application shell layout.
 *
 * Renders the persistent chrome (header + sidebar) and an <Outlet />
 * for the active route's page component.
 */
export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className={styles.layout}>
      <Header onMenuToggle={() => setSidebarOpen((prev) => !prev)} />

      <div className={styles.body}>
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        <main className={styles.main}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}

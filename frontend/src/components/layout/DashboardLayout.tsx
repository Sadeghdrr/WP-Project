/**
 * DashboardLayout — the authenticated shell.
 * Composes Sidebar + Topbar + scrollable main content area (<Outlet />).
 * The sidebar is collapsible on mobile via state toggle.
 */
import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

export const DashboardLayout = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className={`dashboard-layout ${sidebarCollapsed ? 'dashboard-layout--collapsed' : ''}`}>
      <Sidebar collapsed={sidebarCollapsed} />

      <div className="dashboard-layout__main">
        <Topbar onToggleSidebar={() => setSidebarCollapsed((p) => !p)} />

        <main className="dashboard-layout__content">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

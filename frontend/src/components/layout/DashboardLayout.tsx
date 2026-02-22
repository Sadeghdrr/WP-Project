import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';

/**
 * Layout for authenticated pages (Dashboard, Cases, etc.)
 * Composes: Sidebar + Topbar + main content area (<Outlet />)
 */
export const DashboardLayout: React.FC = () => {
  return (
    <div className="flex min-h-screen bg-slate-900">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <header className="h-14 border-b border-slate-700 bg-slate-800/50" />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

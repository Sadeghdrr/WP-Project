import React from 'react';
import { Outlet } from 'react-router-dom';

/**
 * Layout for unauthenticated pages (Login, Register).
 * Centered card layout, no sidebar, minimal chrome.
 */
export const AuthLayout: React.FC = () => {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-900 px-4 py-8">
      <div className="w-full max-w-md">
        <Outlet />
      </div>
    </div>
  );
};

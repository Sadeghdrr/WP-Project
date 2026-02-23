import React from 'react';
import { useAuth } from '../../hooks/useAuth';

export const OverviewPage: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold text-slate-100">داشبورد</h1>
      <p className="mb-4 text-slate-400">
        خوش آمدید، {user?.first_name ?? user?.username ?? 'کاربر'}
      </p>
      <button
        onClick={logout}
        className="rounded-lg bg-slate-600 px-4 py-2 text-sm text-white hover:bg-slate-700"
      >
        خروج
      </button>
    </div>
  );
};

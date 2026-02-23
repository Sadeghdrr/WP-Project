import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { usePermissions } from '../../hooks/usePermissions';
import { CasesPerms } from '../../config/permissions';

const CRIME_SCENE_CREATOR_ROLES = [
  'System Admin',
  'Police Chief',
  'Captain',
  'Police Officer',
  'Patrol Officer',
];

export const Sidebar: React.FC = () => {
  const { user } = useAuth();
  const { hasPermission } = usePermissions();
  const canViewCases = hasPermission(CasesPerms.VIEW_CASE);
  const canAddCase = hasPermission(CasesPerms.ADD_CASE);
  const roleName = user?.role_detail?.name ?? '';
  const canCreateCrimeScene =
    canAddCase && CRIME_SCENE_CREATOR_ROLES.includes(roleName);

  return (
    <aside className="flex w-56 flex-col border-l border-slate-700 bg-slate-800/50">
      <nav className="flex flex-col gap-1 p-4">
        <NavLink
          to="/dashboard"
          className={({ isActive }) =>
            `rounded-lg px-4 py-2 text-right text-sm font-medium transition-colors ${
              isActive ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-700'
            }`
          }
        >
          داشبورد
        </NavLink>
        {canViewCases && (
          <>
            <NavLink
              to="/cases"
              className={({ isActive }) =>
                `rounded-lg px-4 py-2 text-right text-sm font-medium transition-colors ${
                  isActive ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-700'
                }`
              }
            >
              پرونده‌ها
            </NavLink>
            {canAddCase && (
              <>
                <NavLink
                  to="/cases/new"
                  className={({ isActive }) =>
                    `rounded-lg px-4 py-2 text-right text-sm font-medium transition-colors ${
                      isActive ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-700'
                    }`
                  }
                >
                  ثبت شکایت
                </NavLink>
                {canCreateCrimeScene && (
                  <NavLink
                    to="/cases/crime-scene"
                    className={({ isActive }) =>
                      `rounded-lg px-4 py-2 text-right text-sm font-medium transition-colors ${
                        isActive ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-700'
                      }`
                    }
                  >
                    ثبت صحنه جرم
                  </NavLink>
                )}
              </>
            )}
          </>
        )}
      </nav>
    </aside>
  );
};

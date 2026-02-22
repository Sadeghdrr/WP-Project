import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

export const HomePage: React.FC = () => {
  const { isAuthenticated } = useAuth();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-900 px-4">
      <h1 className="mb-6 text-right text-3xl font-bold text-slate-100">
        L.A. Noire Police Department
      </h1>
      <p className="mb-8 text-right text-slate-400">
        سیستم مدیریت اداره پلیس
      </p>
      <div className="flex gap-4">
        {isAuthenticated ? (
          <Link
            to="/dashboard"
            className="rounded-lg bg-blue-600 px-6 py-2 font-medium text-white hover:bg-blue-700"
          >
            داشبورد
          </Link>
        ) : (
          <>
            <Link
              to="/login"
              className="rounded-lg bg-blue-600 px-6 py-2 font-medium text-white hover:bg-blue-700"
            >
              ورود
            </Link>
            <Link
              to="/register"
              className="rounded-lg border border-slate-600 px-6 py-2 font-medium text-slate-300 hover:bg-slate-800"
            >
              ثبت‌نام
            </Link>
          </>
        )}
      </div>
    </div>
  );
};

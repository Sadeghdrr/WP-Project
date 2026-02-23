/**
 * Application routes — React Router v6.
 * Auth routes use AuthLayout; protected routes use ProtectedRoute + DashboardLayout.
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthLayout } from '../components/layout/AuthLayout';
import { ProtectedRoute } from '../components/layout/ProtectedRoute';
import { DashboardLayout } from '../components/layout/DashboardLayout';
import { LoginPage } from '../pages/auth/LoginPage';
import { RegisterPage } from '../pages/auth/RegisterPage';
import { HomePage } from '../pages/home/HomePage';
import { OverviewPage } from '../pages/dashboard/OverviewPage';
import { MostWantedPage } from '../pages/suspects/MostWantedPage';

export const AppRouter: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/most-wanted" element={<MostWantedPage />} />

        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        <Route
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard" element={<OverviewPage />} />
          <Route path="/cases" element={<div className="p-6">Cases (placeholder)</div>} />
          <Route path="/cases/new" element={<div className="p-6">New Case (placeholder)</div>} />
          <Route path="/cases/:id" element={<div className="p-6">Case Details (placeholder)</div>} />
          <Route path="/board/:caseId" element={<div className="p-6">Board (placeholder)</div>} />
          <Route path="/evidence" element={<div className="p-6">Evidence (placeholder)</div>} />
          <Route path="/evidence/new" element={<div className="p-6">New Evidence (placeholder)</div>} />
          <Route path="/evidence/:id" element={<div className="p-6">Evidence Detail (placeholder)</div>} />
          <Route path="/suspects" element={<div className="p-6">Suspects (placeholder)</div>} />
          <Route path="/suspects/:id" element={<div className="p-6">Suspect Detail (placeholder)</div>} />
          <Route path="/bounty" element={<div className="p-6">Bounty (placeholder)</div>} />
          <Route path="/reports" element={<div className="p-6">Reports (placeholder)</div>} />
          <Route path="/admin" element={<div className="p-6">Admin (placeholder)</div>} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

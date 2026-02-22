// TODO: Define all application routes using React Router v6
//
// Route structure:
//
// /                          → HomePage (public)
// /most-wanted               → MostWantedPage (public)
//
// <AuthLayout>
//   /login                   → LoginPage
//   /register                → RegisterPage
//
// <DashboardLayout> (wrapped in ProtectedRoute)
//   /dashboard               → OverviewPage
//   /cases                   → CasesListPage
//   /cases/new               → CaseCreatePage
//   /cases/:id               → CaseDetailsPage
//   /board/:caseId           → KanbanBoardPage
//   /evidence                → EvidenceVaultPage
//   /evidence/new            → EvidenceCreatePage
//   /evidence/:id            → EvidenceDetailPage
//   /suspects                → SuspectsListPage
//   /suspects/:id            → SuspectDetailPage
//   /bounty                  → BountyTipPage
//   /reports                 → ReportsPage (permission-gated: Judge, Captain, Chief)
//   /admin                   → AdminPanelPage (permission-gated: System Admin)

import React from 'react';

export const AppRouter: React.FC = () => {
  // TODO: Implement with createBrowserRouter or <BrowserRouter> + <Routes>
  return <div>{/* TODO: Implement Router */}</div>;
};

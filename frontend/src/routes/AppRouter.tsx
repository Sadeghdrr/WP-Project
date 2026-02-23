/**
 * AppRouter — centralised route definition.
 *
 * Structure:
 *  ╭─ PublicLayout (no auth required)
 *  │   /                 → HomePage
 *  │   /most-wanted      → MostWantedPage
 *  │
 *  ╭─ AuthLayout (redirects if already logged in)
 *  │   /login            → LoginPage
 *  │   /register         → RegisterPage
 *  │
 *  ╭─ ProtectedRoute → DashboardLayout
 *  │   /dashboard        → OverviewPage
 *  │   /cases            → CasesListPage
 *  │   /cases/new        → CaseCreatePage
 *  │   /cases/:id        → CaseDetailsPage
 *  │   /boards           → (future) BoardsListPage
 *  │   /boards/:id       → KanbanBoardPage
 *  │   /evidence         → EvidenceVaultPage
 *  │   /evidence/new     → EvidenceCreatePage
 *  │   /evidence/:id     → EvidenceDetailPage
 *  │   /suspects         → SuspectsListPage
 *  │   /suspects/:id     → SuspectDetailPage
 *  │   /bounty           → BountyTipPage
 *  │   /reports          → ReportsPage      (permission-gated)
 *  │   /admin            → AdminPanelPage   (permission-gated)
 *
 * Pages are lazy-loaded to keep the initial bundle small.
 * Role/permission checks are handled by ProtectedRoute (route-level)
 * and PermissionGate (component-level).
 */
import { lazy, Suspense } from 'react';
import {
  createBrowserRouter,
  RouterProvider,
} from 'react-router-dom';
import { PublicLayout } from '@/components/layout/PublicLayout';
import { AuthLayout } from '@/components/layout/AuthLayout';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { Loader } from '@/components/ui/Loader';

/* ── Lazy page imports ───────────────────────────────────────────── */

const HomePage = lazy(() =>
  import('@/pages/home/HomePage').then((m) => ({ default: m.HomePage })),
);
const MostWantedPage = lazy(() =>
  import('@/pages/suspects/MostWantedPage').then((m) => ({
    default: m.MostWantedPage,
  })),
);
const LoginPage = lazy(() =>
  import('@/pages/auth/LoginPage').then((m) => ({ default: m.LoginPage })),
);
const RegisterPage = lazy(() =>
  import('@/pages/auth/RegisterPage').then((m) => ({
    default: m.RegisterPage,
  })),
);
const OverviewPage = lazy(() =>
  import('@/pages/dashboard/OverviewPage').then((m) => ({
    default: m.OverviewPage,
  })),
);
const CasesListPage = lazy(() =>
  import('@/pages/cases/CasesListPage').then((m) => ({
    default: m.CasesListPage,
  })),
);
const CaseCreatePage = lazy(() =>
  import('@/pages/cases/CaseCreatePage').then((m) => ({
    default: m.CaseCreatePage,
  })),
);
const CaseDetailsPage = lazy(() =>
  import('@/pages/cases/CaseDetailsPage').then((m) => ({
    default: m.CaseDetailsPage,
  })),
);
const KanbanBoardPage = lazy(() =>
  import('@/pages/board/KanbanBoardPage').then((m) => ({
    default: m.KanbanBoardPage,
  })),
);
const EvidenceVaultPage = lazy(() =>
  import('@/pages/evidence/EvidenceVaultPage').then((m) => ({
    default: m.EvidenceVaultPage,
  })),
);
const EvidenceCreatePage = lazy(() =>
  import('@/pages/evidence/EvidenceCreatePage').then((m) => ({
    default: m.EvidenceCreatePage,
  })),
);
const EvidenceDetailPage = lazy(() =>
  import('@/pages/evidence/EvidenceDetailPage').then((m) => ({
    default: m.EvidenceDetailPage,
  })),
);
const SuspectsListPage = lazy(() =>
  import('@/pages/suspects/SuspectsListPage').then((m) => ({
    default: m.SuspectsListPage,
  })),
);
const SuspectDetailPage = lazy(() =>
  import('@/pages/suspects/SuspectDetailPage').then((m) => ({
    default: m.SuspectDetailPage,
  })),
);
const BountyTipPage = lazy(() =>
  import('@/pages/suspects/BountyTipPage').then((m) => ({
    default: m.BountyTipPage,
  })),
);
const ReportsPage = lazy(() =>
  import('@/pages/reports/ReportsPage').then((m) => ({
    default: m.ReportsPage,
  })),
);
const AdminPanelPage = lazy(() =>
  import('@/pages/admin/AdminPanelPage').then((m) => ({
    default: m.AdminPanelPage,
  })),
);

/* ── Loading fallback ────────────────────────────────────────────── */

const PageLoader = () => <Loader fullScreen label="Loading page…" />;

/* ── Router definition ───────────────────────────────────────────── */

const router = createBrowserRouter([
  /* ── Public routes ──────────────────────────────────────────────── */
  {
    element: <PublicLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'most-wanted', element: <MostWantedPage /> },
    ],
  },

  /* ── Auth routes (login / register) ─────────────────────────────── */
  {
    element: <AuthLayout />,
    children: [
      { path: 'login', element: <LoginPage /> },
      { path: 'register', element: <RegisterPage /> },
    ],
  },

  /* ── Protected routes (dashboard shell) ─────────────────────────── */
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <DashboardLayout />,
        children: [
          { path: 'dashboard', element: <OverviewPage /> },

          /* Cases */
          { path: 'cases', element: <CasesListPage /> },
          { path: 'cases/new', element: <CaseCreatePage /> },
          { path: 'cases/:id', element: <CaseDetailsPage /> },

          /* Detective board */
          { path: 'boards/:id', element: <KanbanBoardPage /> },

          /* Evidence */
          { path: 'evidence', element: <EvidenceVaultPage /> },
          { path: 'evidence/new', element: <EvidenceCreatePage /> },
          { path: 'evidence/:id', element: <EvidenceDetailPage /> },

          /* Suspects */
          { path: 'suspects', element: <SuspectsListPage /> },
          { path: 'suspects/:id', element: <SuspectDetailPage /> },

          /* Bounty tips */
          { path: 'bounty', element: <BountyTipPage /> },

          /* Reports (permission-gated at component-level) */
          { path: 'reports', element: <ReportsPage /> },

          /* Admin (permission-gated at component-level) */
          { path: 'admin', element: <AdminPanelPage /> },
        ],
      },
    ],
  },
]);

/* ── Exported component ──────────────────────────────────────────── */

export const AppRouter = () => (
  <Suspense fallback={<PageLoader />}>
    <RouterProvider router={router} />
  </Suspense>
);

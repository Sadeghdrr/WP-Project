/**
 * AppRouter — centralised route definition.
 *
 * All pages share a single PublicLayout (top-nav header, no sidebar).
 *
 * Structure:
 *  ╭─ PublicLayout (app shell for every route)
 *  │   /                 → HomePage
 *  │   /most-wanted      → MostWantedPage
 *  │
 *  │   ╭─ ProtectedRoute (redirects to /login if unauthenticated)
 *  │   │   /dashboard        → OverviewPage
 *  │   │   /cases            → CasesListPage
 *  │   │   /cases/new        → CaseCreatePage
 *  │   │   /cases/:id        → CaseDetailsPage
 *  │   │   /boards/:id       → KanbanBoardPage
 *  │   │   /evidence         → EvidenceVaultPage
 *  │   │   /evidence/new     → EvidenceCreatePage
 *  │   │   /evidence/:id     → EvidenceDetailPage
 *  │   │   /suspects         → SuspectsListPage
 *  │   │   /suspects/:id     → SuspectDetailPage
 *  │   │   /bounty           → BountyTipPage
 *  │   │   /reports          → ReportsPage      (permission-gated)
 *  │   │   /admin            → AdminPanelPage   (permission-gated)
 *  │
 *  ╭─ AuthLayout (login / register — own chrome)
 *  │   /login            → LoginPage
 *  │   /register         → RegisterPage
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
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { Loader } from '@/components/ui/Loader';
import { AccountsPerms, CasesPerms, EvidencePerms, BoardPerms } from '@/config/permissions';

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
const UnauthorizedPage = lazy(() =>
  import('@/pages/errors/UnauthorizedPage').then((m) => ({
    default: m.UnauthorizedPage,
  })),
);
const NotFoundPage = lazy(() =>
  import('@/pages/errors/NotFoundPage').then((m) => ({
    default: m.NotFoundPage,
  })),
);

/* ── Loading fallback ────────────────────────────────────────────── */

const PageLoader = () => <Loader fullScreen label="Loading page…" />;

/* ── Router definition ───────────────────────────────────────────── */

const router = createBrowserRouter([
  /* ── Primary shell: PublicLayout wraps everything ───────────────── */
  {
    element: <PublicLayout />,
    children: [
      /* Public (no auth needed) */
      { index: true, element: <HomePage /> },
      { path: 'most-wanted', element: <MostWantedPage /> },

      /* Protected (redirects to /login if unauthenticated) */
      {
        element: <ProtectedRoute />,
        children: [
          { path: 'dashboard', element: <OverviewPage /> },

          /* Cases — view requires view_case */
          {
            element: <ProtectedRoute requiredPermissions={[CasesPerms.VIEW_CASE]} />,
            children: [
              { path: 'cases', element: <CasesListPage /> },
              { path: 'cases/:id', element: <CaseDetailsPage /> },
            ],
          },
          /* Case creation requires add_case */
          {
            element: <ProtectedRoute requiredPermissions={[CasesPerms.ADD_CASE]} />,
            children: [
              { path: 'cases/new', element: <CaseCreatePage /> },
            ],
          },

          /* Detective board — requires view_detectiveboard */
          {
            element: <ProtectedRoute requiredPermissions={[BoardPerms.VIEW_DETECTIVEBOARD]} />,
            children: [
              { path: 'boards/:id', element: <KanbanBoardPage /> },
            ],
          },

          /* Evidence — view requires view_evidence */
          {
            element: <ProtectedRoute requiredPermissions={[EvidencePerms.VIEW_EVIDENCE]} />,
            children: [
              { path: 'evidence', element: <EvidenceVaultPage /> },
              { path: 'evidence/:id', element: <EvidenceDetailPage /> },
            ],
          },
          /* Evidence creation requires add_evidence */
          {
            element: <ProtectedRoute requiredPermissions={[EvidencePerms.ADD_EVIDENCE]} />,
            children: [
              { path: 'evidence/new', element: <EvidenceCreatePage /> },
            ],
          },

          /* Suspects — view accessible to users with view_suspect */
          { path: 'suspects', element: <SuspectsListPage /> },
          { path: 'suspects/:id', element: <SuspectDetailPage /> },

          /* Bounty tips — accessible to all authenticated users */
          { path: 'bounty', element: <BountyTipPage /> },

          /* Reports — requires can_forward_to_judiciary (Captain, Police Chief) */
          {
            element: <ProtectedRoute requiredPermissions={[CasesPerms.CAN_FORWARD_TO_JUDICIARY]} />,
            children: [
              { path: 'reports', element: <ReportsPage /> },
            ],
          },

          /* Admin — requires role management permissions */
          {
            element: <ProtectedRoute requiredPermissions={[AccountsPerms.ADD_ROLE, AccountsPerms.CHANGE_ROLE]} />,
            children: [
              { path: 'admin', element: <AdminPanelPage /> },
            ],
          },
        ],
      },
    ],
  },

  /* ── Auth routes — own chrome (login / register) ─────────────────── */
  {
    element: <AuthLayout />,
    children: [
      { path: 'login', element: <LoginPage /> },
      { path: 'register', element: <RegisterPage /> },
    ],
  },

  /* ── Error / utility routes ─────────────────────────────────────── */
  { path: 'unauthorized', element: <UnauthorizedPage /> },
  { path: '*', element: <NotFoundPage /> },
]);

/* ── Exported component ──────────────────────────────────────────── */

export const AppRouter = () => (
  <Suspense fallback={<PageLoader />}>
    <RouterProvider router={router} />
  </Suspense>
);

import { lazy, Suspense } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppLayout } from "../components/layout";
import { ProtectedRoute, GuestRoute } from "../components/auth";

// ---------------------------------------------------------------------------
// Lazy-loaded pages
// ---------------------------------------------------------------------------

const HomePage = lazy(() => import("../pages/Home/HomePage"));
const LoginPage = lazy(() => import("../pages/Login/LoginPage"));
const RegisterPage = lazy(() => import("../pages/Register/RegisterPage"));

const DashboardPage = lazy(() => import("../pages/Dashboard/DashboardPage"));
const ProfilePage = lazy(() => import("../pages/Profile/ProfilePage"));
const NotificationsPage = lazy(
  () => import("../pages/Notifications/NotificationsPage"),
);

const CaseListPage = lazy(() => import("../pages/Cases/CaseListPage"));
const CaseDetailPage = lazy(() => import("../pages/Cases/CaseDetailPage"));
const FileComplaintPage = lazy(
  () => import("../pages/Cases/FileComplaintPage"),
);
const CrimeScenePage = lazy(() => import("../pages/Cases/CrimeScenePage"));

const EvidenceListPage = lazy(
  () => import("../pages/Evidence/EvidenceListPage"),
);
const AddEvidencePage = lazy(
  () => import("../pages/Evidence/AddEvidencePage"),
);

const SuspectsPage = lazy(() => import("../pages/Suspects/SuspectsPage"));
const SuspectDetailPage = lazy(
  () => import("../pages/Suspects/SuspectDetailPage"),
);
const InterrogationsPage = lazy(
  () => import("../pages/Suspects/InterrogationsPage"),
);
const TrialPage = lazy(() => import("../pages/Suspects/TrialPage"));

const DetectiveBoardPage = lazy(
  () => import("../pages/DetectiveBoard/DetectiveBoardPage"),
);
const MostWantedPage = lazy(
  () => import("../pages/MostWanted/MostWantedPage"),
);
const ReportingPage = lazy(
  () => import("../pages/Reporting/ReportingPage"),
);

const BountyTipsPage = lazy(
  () => import("../pages/BountyTips/BountyTipsPage"),
);
const SubmitTipPage = lazy(
  () => import("../pages/BountyTips/SubmitTipPage"),
);
const VerifyRewardPage = lazy(
  () => import("../pages/BountyTips/VerifyRewardPage"),
);

const AdminPage = lazy(() => import("../pages/Admin/AdminPage"));
const UserManagementPage = lazy(
  () => import("../pages/Admin/UserManagementPage"),
);
const RoleManagementPage = lazy(
  () => import("../pages/Admin/RoleManagementPage"),
);

const NotFoundPage = lazy(() => import("../pages/NotFound/NotFoundPage"));
const ForbiddenPage = lazy(() => import("../pages/Forbidden/ForbiddenPage"));

// ---------------------------------------------------------------------------
// Fallback shown while a lazy chunk is loading
// ---------------------------------------------------------------------------

function PageLoader() {
  return (
    <div style={{ padding: "2rem", textAlign: "center" }}>Loading…</div>
  );
}

/** Wrap a lazy component in Suspense */
function s(Component: React.LazyExoticComponent<React.ComponentType>) {
  return (
    <Suspense fallback={<PageLoader />}>
      <Component />
    </Suspense>
  );
}

// ---------------------------------------------------------------------------
// Router definition
// ---------------------------------------------------------------------------

/**
 * Route tree mirrors routes.ts declarations.
 *
 * Auth guards:
 *   - GuestRoute: /login, /register → redirects to /dashboard if authenticated
 *   - ProtectedRoute: all dashboard/feature routes → redirects to /login if not
 *
 * Structure:
 *   (guest only — no shell)
 *     /login              → LoginPage
 *     /register           → RegisterPage
 *   (app shell layout — Header + Sidebar + Outlet)
 *     / (public)          → HomePage
 *     /forbidden (public) → ForbiddenPage
 *     (protected — requires auth)
 *       /dashboard        → DashboardPage
 *       /profile          → ProfilePage
 *       /notifications    → NotificationsPage
 *       /most-wanted      → MostWantedPage
 *       /cases            → CaseListPage
 *         new/complaint   → FileComplaintPage
 *         new/crime-scene → CrimeScenePage
 *         :caseId         → CaseDetailPage
 *           evidence      → EvidenceListPage
 *           evidence/new  → AddEvidencePage
 *           suspects      → SuspectsPage
 *           suspects/:id  → SuspectDetailPage
 *           interrogations→ InterrogationsPage
 *           trial         → TrialPage
 *       /detective-board/:caseId → DetectiveBoardPage
 *       /reports          → ReportingPage
 *       /bounty-tips      → BountyTipsPage
 *         new             → SubmitTipPage
 *         verify          → VerifyRewardPage
 *       /admin            → AdminPage
 *         users           → UserManagementPage
 *         roles           → RoleManagementPage
 *   *                     → NotFoundPage
 */
const router = createBrowserRouter([
  // ── Guest-only routes (redirect to dashboard if already logged in) ─
  {
    element: <GuestRoute />,
    children: [
      { path: "/login", element: s(LoginPage) },
      { path: "/register", element: s(RegisterPage) },
    ],
  },

  // ── App shell (shared layout: Header + Sidebar + Outlet) ───────────
  {
    element: <AppLayout />,
    children: [
      // Public pages (no auth required, but inside app shell)
      { path: "/", element: s(HomePage) },
      { path: "/forbidden", element: s(ForbiddenPage) },

      // Protected routes (redirect to login if not authenticated)
      {
        element: <ProtectedRoute />,
        children: [
          { path: "/dashboard", element: s(DashboardPage) },
          { path: "/profile", element: s(ProfilePage) },
          { path: "/notifications", element: s(NotificationsPage) },
          { path: "/most-wanted", element: s(MostWantedPage) },

          // Cases
          {
            path: "/cases",
            children: [
              { index: true, element: s(CaseListPage) },
              { path: "new/complaint", element: s(FileComplaintPage) },
              { path: "new/crime-scene", element: s(CrimeScenePage) },
              {
                path: ":caseId",
                children: [
                  { index: true, element: s(CaseDetailPage) },
                  { path: "evidence", element: s(EvidenceListPage) },
                  { path: "evidence/new", element: s(AddEvidencePage) },
                  { path: "suspects", element: s(SuspectsPage) },
                  { path: "suspects/:suspectId", element: s(SuspectDetailPage) },
                  { path: "interrogations", element: s(InterrogationsPage) },
                  { path: "trial", element: s(TrialPage) },
                ],
              },
            ],
          },

          // Detective Board
          { path: "/detective-board/:caseId", element: s(DetectiveBoardPage) },

          // Reporting
          { path: "/reports", element: s(ReportingPage) },

          // Bounty Tips
          {
            path: "/bounty-tips",
            children: [
              { index: true, element: s(BountyTipsPage) },
              { path: "new", element: s(SubmitTipPage) },
              { path: "verify", element: s(VerifyRewardPage) },
            ],
          },

          // Admin Panel
          {
            path: "/admin",
            children: [
              { index: true, element: s(AdminPage) },
              { path: "users", element: s(UserManagementPage) },
              { path: "roles", element: s(RoleManagementPage) },
            ],
          },
        ],
      },
    ],
  },

  // ── Catch-all ──────────────────────────────────────────────────────
  { path: "*", element: s(NotFoundPage) },
]);

// ---------------------------------------------------------------------------
// Exported component
// ---------------------------------------------------------------------------

export default function AppRouter() {
  return <RouterProvider router={router} />;
}

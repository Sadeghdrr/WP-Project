# Step 06 – App Shell Bootstrap – Agent Report

**Branch:** `agent/step-06-app-shell-bootstrap`
**Date:** 2025-07-23
**Status:** ✅ Complete

---

## 1. Objective

Bootstrap the frontend application shell: wire providers, create the
persistent layout (header + sidebar + content area), register all
routes with lazy-loaded placeholder pages, add the global error
boundary, and establish the design-token system.

---

## 2. Dependencies Installed

| Package | Version | Slot | Purpose |
|---|---|---|---|
| `react-router-dom` | ^7.13.1 | 3/6 | Client-side routing |
| `@tanstack/react-query` | ^5.90.21 | 4/6 | Server-state / data-fetching cache |

Remaining budget: **2 slots** reserved for `@xyflow/react` and
`html-to-image` (Detective Board, Step 11+).

> **Note:** `--legacy-peer-deps` required during install due to
> `eslint-plugin-react-hooks@7.0.1` not supporting `eslint@10.0.2`.
> This is a dev-only tooling issue with no runtime impact.

---

## 3. Files Created / Modified

### New files (frontend/src/)

#### API Client
| File | Purpose |
|---|---|
| `api/client.ts` | Fetch wrapper with auth header injection, error normalisation |
| `api/endpoints.ts` | Centralised API URL constants |
| `api/index.ts` | Barrel export |

#### Layout Components
| File | Purpose |
|---|---|
| `components/layout/Header.tsx` | Sticky header with brand, nav links, mobile hamburger |
| `components/layout/Header.module.css` | Header styles |
| `components/layout/Sidebar.tsx` | Fixed sidebar, 3 nav sections, mobile overlay |
| `components/layout/Sidebar.module.css` | Sidebar styles |
| `components/layout/AppLayout.tsx` | Shell: Header + Sidebar + Outlet |
| `components/layout/AppLayout.module.css` | Layout styles |
| `components/layout/index.ts` | Barrel export |

#### UI Primitives
| File | Purpose |
|---|---|
| `components/ui/ErrorBoundary.tsx` | Class-based error boundary with fallback UI |
| `components/ui/PlaceholderPage.tsx` | Reusable placeholder with title + badge |
| `components/ui/PlaceholderPage.module.css` | Placeholder styles |
| `components/ui/index.ts` | Barrel export |

#### Router
| File | Purpose |
|---|---|
| `router/Router.tsx` | `createBrowserRouter` wiring with lazy imports |

#### Placeholder Pages (26 files)
| Folder | Files |
|---|---|
| `pages/Home/` | `HomePage.tsx`, `HomePage.module.css` |
| `pages/Login/` | `LoginPage.tsx` |
| `pages/Register/` | `RegisterPage.tsx` |
| `pages/Dashboard/` | `DashboardPage.tsx` |
| `pages/Cases/` | `CaseListPage.tsx`, `CaseDetailPage.tsx`, `FileComplaintPage.tsx`, `CrimeScenePage.tsx` |
| `pages/Evidence/` | `EvidenceListPage.tsx`, `AddEvidencePage.tsx` |
| `pages/Suspects/` | `SuspectsPage.tsx`, `SuspectDetailPage.tsx`, `InterrogationsPage.tsx`, `TrialPage.tsx` |
| `pages/DetectiveBoard/` | `DetectiveBoardPage.tsx` |
| `pages/MostWanted/` | `MostWantedPage.tsx` |
| `pages/Reporting/` | `ReportingPage.tsx` |
| `pages/BountyTips/` | `BountyTipsPage.tsx`, `SubmitTipPage.tsx`, `VerifyRewardPage.tsx` |
| `pages/Admin/` | `AdminPage.tsx`, `UserManagementPage.tsx`, `RoleManagementPage.tsx` |
| `pages/Profile/` | `ProfilePage.tsx` |
| `pages/Notifications/` | `NotificationsPage.tsx` |
| `pages/NotFound/` | `NotFoundPage.tsx`, `NotFoundPage.module.css` |
| `pages/Forbidden/` | `ForbiddenPage.tsx`, `ForbiddenPage.module.css` |

### Modified files
| File | Change |
|---|---|
| `src/App.tsx` | Replaced Vite boilerplate with provider composition |
| `src/main.tsx` | Minor formatting (quotes, semicolons) |
| `src/index.css` | Replaced Vite boilerplate with design tokens + CSS reset |

### Deleted files
| File | Reason |
|---|---|
| `src/App.css` | Vite boilerplate, no longer imported |

### New documentation
| File | Purpose |
|---|---|
| `frontend/docs/app-shell-notes.md` | Architecture reference for the shell |
| `md-files/step_06_app_shell_bootstrap_report.md` | This report |

---

## 4. Route → Page Traceability

Mapping every route from `routes.ts` to its placeholder page:

| Route path | Page component | Auth | Status |
|---|---|---|---|
| `/` | `HomePage` | public | ✅ |
| `/login` | `LoginPage` | public | ✅ |
| `/register` | `RegisterPage` | public | ✅ |
| `/forbidden` | `ForbiddenPage` | public | ✅ |
| `/dashboard` | `DashboardPage` | auth | ✅ |
| `/profile` | `ProfilePage` | auth | ✅ |
| `/notifications` | `NotificationsPage` | auth | ✅ |
| `/most-wanted` | `MostWantedPage` | auth | ✅ |
| `/cases` | `CaseListPage` | auth | ✅ |
| `/cases/new/complaint` | `FileComplaintPage` | auth | ✅ |
| `/cases/new/crime-scene` | `CrimeScenePage` | auth | ✅ |
| `/cases/:caseId` | `CaseDetailPage` | auth | ✅ |
| `/cases/:caseId/evidence` | `EvidenceListPage` | auth | ✅ |
| `/cases/:caseId/evidence/new` | `AddEvidencePage` | auth | ✅ |
| `/cases/:caseId/suspects` | `SuspectsPage` | auth | ✅ |
| `/cases/:caseId/suspects/:suspectId` | `SuspectDetailPage` | auth | ✅ |
| `/cases/:caseId/interrogations` | `InterrogationsPage` | auth | ✅ |
| `/cases/:caseId/trial` | `TrialPage` | auth | ✅ |
| `/detective-board/:caseId` | `DetectiveBoardPage` | auth | ✅ |
| `/reports` | `ReportingPage` | auth | ✅ |
| `/bounty-tips` | `BountyTipsPage` | auth | ✅ |
| `/bounty-tips/new` | `SubmitTipPage` | auth | ✅ |
| `/bounty-tips/verify` | `VerifyRewardPage` | auth | ✅ |
| `/admin` | `AdminPage` | auth (admin) | ✅ |
| `/admin/users` | `UserManagementPage` | auth (admin) | ✅ |
| `/admin/roles` | `RoleManagementPage` | auth (admin) | ✅ |
| `*` | `NotFoundPage` | public | ✅ |

**All 27 routes have corresponding placeholder pages.**

---

## 5. Project-doc §7 Scoring Alignment

| §7 Item | Coverage in this step |
|---|---|
| 7.1 Frontend UI | App shell renders, all pages reachable |
| 7.2 Routing | Full route tree wired with lazy loading |
| 7.3 State management | react-query provider installed |
| 7.4 Responsive layout | Header + Sidebar responsive at 640px breakpoint |
| 7.5 Error handling | ErrorBoundary wraps entire app |
| 7.6 API integration | API client stub ready (no real calls yet) |

---

## 6. Build Verification

```
✓ tsc --noEmit        → 0 errors
✓ vite build          → 130 modules, 1.85s
✓ All lazy chunks     → individual .js files per page
✓ Main bundle         → 315 kB (100.6 kB gzip)
```

---

## 7. Known Issues / Anomalies

| Issue | Severity | Notes |
|---|---|---|
| `eslint-plugin-react-hooks@7.0.1` vs `eslint@10` peer conflict | Low | Dev-only; used `--legacy-peer-deps` |
| Suspect API endpoints double-prefix (`/suspects/suspects/...`) | Info | Known backend URL structure from Step 2 |
| Auth guards not enforced | Expected | Will be added in Step 07 with AuthProvider |

---

## 8. Deferred to Future Steps

| Item | Target step |
|---|---|
| AuthProvider + protected route wrapper | Step 07 |
| Login / Register form implementation | Step 07 |
| Dashboard real data + charts | Step 08 |
| Case list / detail implementation | Step 09 |
| Evidence CRUD | Step 10 |
| Detective Board (react-flow) | Step 11 |
| All remaining feature UIs | Steps 08–15 |

---

## 9. How to Verify

```bash
cd frontend
npm install --legacy-peer-deps
npx tsc --noEmit          # should show 0 errors
npx vite build            # should succeed
npm run dev               # open http://localhost:5173
```

Navigate to any route (e.g. `/dashboard`, `/cases`, `/admin`) to see
the layout shell with placeholder content.

# App Shell – Architecture Notes

> Created during **Step 06 – App Shell Bootstrap**.
> This document describes the structural decisions made in the application
> shell and serves as the reference for future feature steps.

---

## 1. Provider Stack

```
<StrictMode>
  <QueryClientProvider>       ← @tanstack/react-query   (data cache)
    <ErrorBoundary>            ← catches unhandled render errors
      <RouterProvider>         ← react-router-dom v7     (SPA routing)
      </RouterProvider>
    </ErrorBoundary>
  </QueryClientProvider>
</StrictMode>
```

**Placeholder slots** (to be added in later steps):

| Provider | Purpose | Planned step |
|---|---|---|
| `AuthProvider` | Token state, user object, login/logout | Step 07 |
| `ThemeProvider` | (optional) dark mode / accent colour | TBD |

---

## 2. Route Architecture

The route tree is defined in **two** files:

| File | Role |
|---|---|
| `src/router/routes.ts` | Declarative data – path, title, auth metadata |
| `src/router/Router.tsx` | React-router wiring – `createBrowserRouter` + lazy imports |

### Layout split

- **Public routes** (`/`, `/login`, `/register`, `/forbidden`) render
  outside the `AppLayout` shell (no sidebar/header).
- **Authenticated routes** (`/dashboard`, `/cases/*`, etc.) are nested
  inside `<AppLayout />` which renders the persistent header, sidebar
  and an `<Outlet />` for the active page.

### Lazy loading

Every page except the initial `AppLayout` shell is wrapped in
`React.lazy()` + `<Suspense>`, so each page is its own code-split
chunk.  The production build already confirms individual chunk files
for every route (see build output).

### Auth guards

Auth guards are declared in `routes.ts` (`authRequired`, `minHierarchy`,
`requiredPermissions`) but are **not enforced** in this step.
Guard wrapper components will be added in Step 07 when the auth context
exists.

---

## 3. Layout Components

```
src/components/layout/
├── AppLayout.tsx           ← shell: header + sidebar + <Outlet />
├── AppLayout.module.css
├── Header.tsx              ← sticky top bar, brand, nav links, mobile hamburger
├── Header.module.css
├── Sidebar.tsx             ← fixed left nav, 3 sections, mobile overlay
├── Sidebar.module.css
└── index.ts                ← barrel export
```

### Responsive behaviour

| Breakpoint | Sidebar | Header nav | Menu button |
|---|---|---|---|
| > 640 px | Fixed, visible | Visible inline | Hidden |
| ≤ 640 px | Off-screen, slide-in overlay | Hidden | Visible |

CSS variables (`--header-height`, `--sidebar-width`) control dimensions
for consistent alignment across all layout sections.

---

## 4. Placeholder Pages

Every required page from project-doc.md §5 has a placeholder component.
Each one renders the `<PlaceholderPage>` UI primitive with a descriptive
title and description.  The pages contain **zero** feature logic —
they exist only to:

1. Prove that routes resolve correctly.
2. Give each chunk a named module for the build system.
3. Serve as the starting point for feature implementation.

### Page inventory

| Folder | Pages |
|---|---|
| `Home/` | `HomePage` (custom landing UI) |
| `Login/` | `LoginPage` |
| `Register/` | `RegisterPage` |
| `Dashboard/` | `DashboardPage` |
| `Cases/` | `CaseListPage`, `CaseDetailPage`, `FileComplaintPage`, `CrimeScenePage` |
| `Evidence/` | `EvidenceListPage`, `AddEvidencePage` |
| `Suspects/` | `SuspectsPage`, `SuspectDetailPage`, `InterrogationsPage`, `TrialPage` |
| `DetectiveBoard/` | `DetectiveBoardPage` |
| `MostWanted/` | `MostWantedPage` |
| `Reporting/` | `ReportingPage` |
| `BountyTips/` | `BountyTipsPage`, `SubmitTipPage`, `VerifyRewardPage` |
| `Admin/` | `AdminPage`, `UserManagementPage`, `RoleManagementPage` |
| `Profile/` | `ProfilePage` |
| `Notifications/` | `NotificationsPage` |
| `NotFound/` | `NotFoundPage` (404) |
| `Forbidden/` | `ForbiddenPage` (403) |

---

## 5. API Client

```
src/api/
├── client.ts       ← fetch wrapper with auth header injection
├── endpoints.ts    ← centralized URL constants
└── index.ts        ← barrel export
```

The client uses module-scoped token storage (`setAccessToken` /
`getAccessToken`) rather than reading from localStorage on every request.
This will be wired to the auth context in Step 07.

Error responses are normalised into `ApiError` objects with optional
`fieldErrors` for DRF validation responses.

---

## 6. Design Tokens

All visual constants live as CSS custom properties in `src/index.css`.
Component styles reference these tokens via `var(--token-name)`.

Key token categories:
- **Colours**: `--color-primary`, `--color-surface`, `--color-border`, etc.
- **Spacing**: numeric (`--space-1` … `--space-12`) + semantic aliases
  (`--space-xs` … `--space-xl`)
- **Radii**: `--radius-sm`, `--radius-md`, `--radius-lg`
- **Shadows**: `--shadow-sm`, `--shadow-md`, `--shadow-lg`
- **Typography**: `--font-sans`, `--font-mono`
- **Layout**: `--header-height`, `--sidebar-width`

---

## 7. Styling Approach

- **CSS Modules** (`.module.css`) for all component styles — scoped by
  default, zero config in Vite.
- **Global reset + base** in `src/index.css`.
- No CSS framework / utility library.
- Responsive breakpoints applied inline in each module's `@media` rules.

---

## 8. Deferred Items

Items explicitly **not** implemented in this step:

| Item | Reason | Target step |
|---|---|---|
| Auth context + protected routes | Needs auth API integration | Step 07 |
| Real data fetching | Needs auth + service layer | Step 08+ |
| Form components | Feature-level work | Per-feature steps |
| Dark mode | Not in MVP scope | TBD |
| i18n / l10n | Not in requirements | N/A |
| Service-worker / PWA | Not in requirements | N/A |
| Accessibility audit | Will be done per-component | Ongoing |

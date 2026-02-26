# Step 19 — UX Hardening Pass

**Branch:** `agent/step-19-ux-hardening-pass`  
**Scope:** Frontend only — no backend changes

---

## Objective

Perform a focused UX hardening pass across all existing frontend pages to
improve grading-critical quality in four areas: loading states/skeletons
(300 pts), responsive pages (300 pts), error messages (100 pts), and
component lifecycles (100 pts).

---

## Changes Made

### 1. Loading State Improvements

| File | Change |
| ---- | ------ |
| `DetectiveBoardPage.tsx` | Replaced plain text `Loading board data…` div with `<LoadingSpinner>` UI component |

### 2. Error State Consistency

| File | Change |
| ---- | ------ |
| `DetectiveBoardPage.tsx` | Replaced raw `<div className={css.errorBox}>Error: …</div>` with `<ErrorState>` + `onRetry` |
| `HomePage.tsx` | Replaced inline `<p className={styles.errorMsg}>` with `<ErrorState>` + `onRetry` |
| `MostWantedPage.tsx` | Added `onRetry={() => refetch()}` to existing `<ErrorState>` |
| `BountyTipsPage.tsx` | Added `onRetry={() => refetch()}` to existing `<ErrorState>` |
| `ReportingPage.tsx` | Added `onRetry={() => refetch()}` to existing `<ErrorState>` |
| `AdminPage.tsx` | Added `onRetry` calling both `refetchUsers()` and `refetchRoles()` |

### 3. Empty State Improvements

| File | Change |
| ---- | ------ |
| `CaseDetailPage.tsx` | Replaced `return null` with `<EmptyState heading="Case Not Found">` |

### 4. Responsive CSS (`@media (max-width: 640px)`)

Nine CSS module files received new responsive breakpoints:

| File | Key responsive rules |
| ---- | -------------------- |
| `MostWantedPage.module.css` | Single-column grid, stacked card top, column stats |
| `FileComplaintPage.module.css` | Stacked buttons, reduced padding |
| `CrimeScenePage.module.css` | Stacked buttons, reduced padding |
| `AddEvidencePage.module.css` | Single-column type cards, stacked KV rows, full-width actions |
| `BountyTipsPage.module.css` | Table scroll wrapper, min-width 700px, stacked header/filters |
| `SubmitTipPage.module.css` | Full-width buttons, reduced padding |
| `VerifyRewardPage.module.css` | Stacked result rows |
| `ReportingPage.module.css` | Stacked toolbar, full-width search, table min-width 600px |
| `CaseReportView.module.css` | Single-column grids, table scroll wrapper, stacked suspect cards |

### 5. Table Scroll Wrappers

| File | Change |
| ---- | ------ |
| `BountyTipsPage.tsx` | Wrapped `<table>` in `<div className={css.tableWrap}>` |
| `BountyTipsPage.module.css` | Added `.tableWrap { overflow-x: auto }` |

---

## Files Modified

### TSX (7 files)
- `frontend/src/pages/DetectiveBoard/DetectiveBoardPage.tsx`
- `frontend/src/pages/Home/HomePage.tsx`
- `frontend/src/pages/MostWanted/MostWantedPage.tsx`
- `frontend/src/pages/BountyTips/BountyTipsPage.tsx`
- `frontend/src/pages/Reporting/ReportingPage.tsx`
- `frontend/src/pages/Admin/AdminPage.tsx`
- `frontend/src/pages/Cases/CaseDetailPage.tsx`

### CSS Modules (9 files)
- `frontend/src/pages/MostWanted/MostWantedPage.module.css`
- `frontend/src/pages/Cases/FileComplaintPage.module.css`
- `frontend/src/pages/Cases/CrimeScenePage.module.css`
- `frontend/src/pages/Evidence/AddEvidencePage.module.css`
- `frontend/src/pages/BountyTips/BountyTipsPage.module.css`
- `frontend/src/pages/BountyTips/SubmitTipPage.module.css`
- `frontend/src/pages/BountyTips/VerifyRewardPage.module.css`
- `frontend/src/pages/Reporting/ReportingPage.module.css`
- `frontend/src/pages/Reporting/CaseReportView.module.css`

### Docs (1 file)
- `frontend/docs/ux-hardening-checklist.md`

---

## Verification

- `npx tsc --noEmit` — **0 errors**
- `npx eslint` on all 7 modified TSX files — **0 warnings/errors**

---

## Not In Scope

- 6 placeholder pages (SuspectsPage, SuspectDetailPage, InterrogationsPage,
  TrialPage, ProfilePage, NotificationsPage) — require full feature
  implementation, not UX hardening
- Backend changes — none required

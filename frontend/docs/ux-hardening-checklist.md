# UX Hardening Checklist — Step 19

Systematic audit and remediation of grading-critical UX quality areas.

## Scoring Areas

| Area                      | Weight | Status |
| ------------------------- | ------ | ------ |
| Loading states / Skeletons | 300 pts | ✅ Hardened |
| Responsive pages           | 300 pts | ✅ Hardened |
| Error messages              | 100 pts | ✅ Hardened |
| Component lifecycles        | 100 pts | ✅ Hardened |

---

## Loading States / Skeletons

| Page | Before | After |
| ---- | ------ | ----- |
| DetectiveBoardPage | Plain text `<div>Loading board data…</div>` | `<LoadingSpinner label="Loading board data…" />` |
| HomePage | Skeleton cards for stats ✅ | No change needed |
| MostWantedPage | 6× `<Skeleton height={280} />` ✅ | No change needed |
| BountyTipsPage | `<Skeleton height={300} />` ✅ | No change needed |
| ReportingPage | 8× `<Skeleton height={36} />` ✅ | No change needed |
| AdminPage | `<LoadingSpinner />` ✅ | No change needed |
| CaseDetailPage | Multiple Skeleton variants ✅ | No change needed |

---

## Error States

| Page | Before | After |
| ---- | ------ | ----- |
| DetectiveBoardPage | Raw `<div className={css.errorBox}>Error: …</div>` | `<ErrorState message={…} onRetry={() => refetchBoard()} compact />` |
| HomePage | `<p className={styles.errorMsg}>…</p>` | `<ErrorState message="…" onRetry={() => refetch()} compact />` |
| MostWantedPage | `<ErrorState message={…} />` (no retry) | Added `onRetry={() => refetch()}` |
| BountyTipsPage | `<ErrorState message={…} />` (no retry) | Added `onRetry={() => refetch()}` |
| ReportingPage | `<ErrorState message={…} />` (no retry) | Added `onRetry={() => refetch()}` |
| AdminPage | `<ErrorState message="…" />` (no retry) | Added `onRetry={() => { refetchUsers(); refetchRoles(); }}` |
| CaseDetailPage | `<ErrorState onRetry />` ✅ | No change needed |

---

## Empty States

| Page | Before | After |
| ---- | ------ | ----- |
| CaseDetailPage | `return null` when no data | `<EmptyState heading="Case Not Found" message="No data available for this case." />` |
| MostWantedPage | `<EmptyState />` ✅ | No change needed |
| BountyTipsPage | `<EmptyState />` ✅ | No change needed |
| ReportingPage | `<EmptyState />` ✅ | No change needed |

---

## Responsive CSS

Added `@media (max-width: 640px)` breakpoints to:

| CSS Module | Changes |
| ---------- | ------- |
| MostWantedPage.module.css | Single-column grid, stacked card layout, smaller padding |
| FileComplaintPage.module.css | Stack form fields, full-width submit button |
| CrimeScenePage.module.css | Stack form fields, full-width submit button |
| AddEvidencePage.module.css | Single-column type cards, stacked KV rows, full-width actions |
| BountyTipsPage.module.css | Scroll wrapper for table (`.tableWrap`), min-width on table, stacked header/filters |
| SubmitTipPage.module.css | Stack form fields, full-width buttons |
| VerifyRewardPage.module.css | Stack form and result rows |
| ReportingPage.module.css | Stacked toolbar, full-width search, min-width on table |
| CaseReportView.module.css | Single-column KV/personnel grids, table scroll, stacked suspect cards |

### Pages already responsive (no changes needed)

- HomePage.module.css — `@media (max-width: 640px)` ✅
- CaseDetailPage.module.css — `@media (max-width: 768px)` ✅
- DetectiveBoardPage.module.css — `@media (max-width: 768px)` ✅
- UserManagementPage.module.css — `@media (max-width: 768px)` ✅
- Sidebar / AppLayout — `@media (max-width: 640px)` ✅

---

## Component Lifecycle Fixes

- **BountyTipsPage**: Wrapped `<table>` in `<div className={css.tableWrap}>` for horizontal scroll on overflow
- All `useQuery` hooks already return full query result; `refetch` now properly destructured in 5 pages

---

## Placeholder Pages (out of scope)

The following pages are `<PlaceholderPage>` stubs requiring full feature implementation, NOT UX hardening:
- SuspectsPage, SuspectDetailPage, InterrogationsPage, TrialPage, ProfilePage, NotificationsPage

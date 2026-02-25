# Step 11 – Home Page with Summary Metrics

## Objective

Implement the Home page required by **§5.1** of the project specification:

> Provide a general introduction to the system as well as the police
> department and their duties. Display several statistics (at least three)
> regarding cases and their statuses.

## Branch

`agent/step-11-home-page` (off `master`)

## Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/types/core.ts` | Modified | Updated `DashboardStats` interface to match the real backend `DashboardStatsSerializer` shape; added sub-types `CasesByStatusEntry`, `CasesByCrimeLevelEntry`, `TopWantedSuspect`, `RecentActivityEntry` |
| `frontend/src/pages/Home/HomePage.tsx` | Rewritten | Full implementation: hero section, about/intro paragraphs, duties list, 6 stat cards with auth-conditional fetch via React Query |
| `frontend/src/pages/Home/HomePage.module.css` | Expanded | Intro, duties grid, stats section, skeleton shimmer animation, accent variants, auth hint, error styling, responsive breakpoints |
| `frontend/docs/home-page-notes.md` | Created | Implementation notes — endpoints used, metrics shown, fallback strategy, deferred enhancements |
| `md-files/step-11-agent-report.md` | Created | This report |

## Requirements Coverage

| Requirement (§5.1) | Status |
|---------------------|--------|
| General introduction to the system | ✅ Hero + About section |
| Introduction to the police department | ✅ About the Department paragraph |
| Mention of duties | ✅ Core Duties section (4 items) |
| At least 3 statistics on cases | ✅ 6 stats: Total Cases, Active Cases, Closed Cases, Total Suspects, Evidence Items, Employees |
| Responsive layout | ✅ Mobile breakpoint at 640 px |
| Loading state | ✅ Skeleton shimmer grid |
| Error state | ✅ Red error message |

## Endpoint Usage

- **`GET /api/core/dashboard/`** — authenticated; returns department-wide stats.
- No public stats endpoint exists, so unauthenticated visitors see "—" placeholders.

## Key Design Decisions

1. **Auth-conditional fetching**: The Home route is public but the dashboard
   endpoint requires `IsAuthenticated`. We use `useAuth()` to conditionally
   enable the React Query and show a soft hint for unauthenticated users.

2. **Type alignment**: The previous `DashboardStats` interface had incorrect
   field names (`total_solved_cases` instead of `total_cases`, missing nested
   arrays). Updated to match the real `DashboardStatsSerializer`.

3. **6 stat cards**: Rather than the minimum 3, we show 6 top-level metrics
   for richer information density.

4. **CSS Modules + design tokens**: No third-party component library used;
   all styles use the project's existing CSS custom properties.

## Anomalies & Notes

- **Pre-existing TS errors** in `AuthContext.tsx` (TS6133 unused variable,
  TS2352 type conversion) are unrelated to this change and were not introduced
  by this step.
- **No backend modifications** were made.

## Build Verification

- `npx tsc -b --noEmit` — only pre-existing errors; no new errors.
- `npx vite build` — succeeds; `HomePage` chunk is 4.36 kB (1.74 kB gzip).

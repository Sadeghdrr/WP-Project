# Step 12 — Permission-Aware Modular Dashboard

## Branch

`agent/step-12-modular-dashboard`

## Files Created / Changed

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/pages/Dashboard/DashboardPage.tsx` | Rewritten | Full modular dashboard with permission-aware rendering |
| `frontend/src/pages/Dashboard/DashboardPage.module.css` | Created | Dashboard layout, widget cards, skeleton, responsive styles |
| `frontend/src/hooks/useDashboardStats.ts` | Created | React Query hook for `GET /api/core/dashboard/` |
| `frontend/src/types/core.ts` | Modified | Fixed `TopWantedSuspect` type to match backend serializer |
| `frontend/docs/modular-dashboard-notes.md` | Created | Implementation notes |
| `md-files/step-12-agent-report.md` | Created | This report |

## Dashboard Widgets / Modules Implemented

1. **Stats Overview** — 8 KPI cards (total/active/closed/voided cases, suspects, evidence, employees, unassigned evidence) with color-coded accents
2. **Quick Actions** — Permission-filtered deep links (File Complaint, Report Crime Scene, Browse Cases, Most Wanted, Submit Tip, Admin Panel)
3. **Cases by Status** — Breakdown list from `cases_by_status` (gated on `cases.view_case`)
4. **Cases by Crime Level** — Breakdown list from `cases_by_crime_level` (gated on `cases.view_case`)
5. **Top Wanted Suspects** — Table showing name, score, days wanted (gated on `suspects.view_suspect`)
6. **Evidence Overview** — Total + unassigned counts (gated on `evidence.view_evidence`)
7. **Detective Board** — Info card + link to cases (gated on `board.view_detectiveboard`)
8. **Recent Activity** — Activity feed showing description, actor, timestamp

## Permissions Logic Summary

- Each module has a `MODULE_VISIBILITY` definition with an `anyPermission` array
- Rendering uses `canAny(permissionSet, anyPermission)` — OR logic
- `permissionSet` is a `ReadonlySet<string>` of `"app_label.codename"` strings from `useAuth()`
- **No role-name hardcoding** — adapts automatically to runtime role/permission changes
- Zero-module users see a graceful "No modules available" empty state
- Quick actions are independently permission-gated

## Endpoints Used

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `GET /api/core/dashboard/` | GET | Required | Dashboard stats (role-aware aggregation) |
| `GET /api/accounts/me/` | GET | Required | User info + permission set (via AuthContext) |

## Deferred Widgets / Items

| Item | Reason |
|------|--------|
| Interrogation widget | No dedicated dashboard aggregation; accessible via Quick Actions |
| Trial / Judiciary widget | No dedicated dashboard aggregation |
| Bounty Tips widget | No dedicated dashboard aggregation; accessible via Quick Actions |
| Charts / visualizations | Not required by project-doc; would require charting library |
| Drag-and-drop dashboard customization | Not required ("modular" ≠ "customizable") |

## Backend Anomalies / Problems (Report Only)

1. **`TopWantedSuspect` type mismatch** — The frontend `TopWantedSuspect` type had `status` and `danger_level` fields that don't exist in the backend's `TopWantedSuspectSerializer`. Fixed in this step to match backend: `photo_url`, `most_wanted_score`, `reward_amount`, `days_wanted`, `case_id`, `case_title`.

2. **Pre-existing TS errors** in `AuthContext.tsx` — two unrelated TypeScript errors (TS6133 unused variable, TS2352 type conversion) are not caused by this step.

No other backend anomalies found. The dashboard endpoint returns comprehensive data.

## Confirmation

- **No backend files were modified.**
- All changes are in `frontend/` and `md-files/`.

## Build Verification

- `npx tsc -b --noEmit` — only pre-existing errors; no new errors
- `npx vite build` — succeeds; `DashboardPage` chunk is 13.25 kB (4.13 kB gzip)

## Post-Check: Coverage vs project-doc.md §5.3

| Requirement | Status | Notes |
|-------------|--------|-------|
| "show an appropriate dashboard for every user account" | ✅ Implemented | Personalized greeting + role label |
| "dashboard must be modular" | ✅ Implemented | 8 independent widget components |
| "display a set of modules based on access level" | ✅ Implemented | Permission-gated via `canAny()` |
| "Detective must see Detective Board module" | ✅ Implemented | Gated on `board.view_detectiveboard` |
| "Coroner should not see Detective Board" | ✅ Implemented | Permission check excludes unauthorized roles |
| Loading states / skeleton (300 pts) | ✅ Implemented | Skeleton grid for stats + modules |
| Responsive pages (300 pts) | ✅ Implemented | 3 breakpoints: desktop / tablet / mobile |
| Error messages (100 pts) | ✅ Implemented | `<ErrorState>` with retry |
| Proper state management (100 pts) | ✅ Implemented | React Query for data, permission hooks |

### Coverage Summary

- **Implemented**: Modular dashboard, permission-aware module visibility, stats overview, cases by status/crime level, top wanted, evidence overview, detective board card, recent activity, quick actions, skeleton loading, error state, responsive layout, empty state for no-permission users
- **Partial**: Interrogation/trial/bounty widgets show as quick-action links but not as data-driven widgets (no dedicated aggregation endpoints)
- **Deferred**: Charts/visualizations (not required), drag-and-drop (not required)
- **Blocked by backend**: None

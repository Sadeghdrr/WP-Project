# Modular Dashboard — Implementation Notes

## Overview

The Dashboard page (`/dashboard`) implements **§5.3 — Modular Dashboard** (800 pts).  
It renders a set of permission-aware modules/widgets driven by the user's
permission set, backed by the role-aware `GET /api/core/dashboard/` endpoint.

## Widgets / Modules Implemented

| Widget | Permission Gate | Data Source |
|--------|----------------|-------------|
| Stats Overview (8 KPI cards) | — (all authenticated) | `dashboard.*` top-level fields |
| Quick Actions | Per-action permission check | Static links, filtered |
| Cases by Status | `cases.view_case` | `dashboard.cases_by_status[]` |
| Cases by Crime Level | `cases.view_case` | `dashboard.cases_by_crime_level[]` |
| Top Wanted Suspects | `suspects.view_suspect` | `dashboard.top_wanted_suspects[]` |
| Evidence Overview | `evidence.view_evidence` | `dashboard.total_evidence`, `unassigned_evidence_count` |
| Detective Board | `board.view_detectiveboard` | Static (deep link to cases) |
| Recent Activity | — (all authenticated) | `dashboard.recent_activity[]` |

## Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/core/dashboard/` | GET | All dashboard stats (role-aware) |
| `/api/accounts/me/` | GET | User info + permissions (via AuthContext) |

## Permission Rendering Strategy

- **No role-name hardcoding** — visibility uses `canAny(permissionSet, requiredPerms)`.
- Each module has a `MODULE_VISIBILITY` entry specifying which permissions
  (OR logic) gate its rendering.
- Quick actions are independently filtered by permission.
- If a user has zero visible modules, a graceful "No modules available"
  empty state is shown.
- This approach automatically adapts when roles/permissions are modified
  at runtime via the admin panel — no code changes needed.

## Loading / Error / Responsive

- **Loading**: Skeleton grid (8 stat placeholders + 4 module placeholders)
  using the existing `<Skeleton>` component.
- **Error**: `<ErrorState>` component with retry button.
- **Responsive**: 3-breakpoint layout (desktop → tablet → mobile) using
  CSS Grid `auto-fit` and media queries at 768px and 480px.

## Fallback / Deferred Widgets

| Item | Status | Reason |
|------|--------|--------|
| Interrogation module | Deferred | No dedicated dashboard data; link via Quick Actions |
| Trial / Judiciary module | Deferred | No dedicated dashboard data |
| Bounty Tips module | Deferred | No dedicated dashboard data; link via Quick Actions |
| Reporting module | Deferred | Linked from Quick Actions; full page exists at /reports |
| Admin module | Deferred | Linked from Quick Actions; full page exists at /admin |
| Charts/visualizations | Deferred | Not required by project-doc; would need charting lib |
| Drag-and-drop layout | Not needed | Project-doc says "modular" not "customizable" |

## Type Fix

The `TopWantedSuspect` type in `types/core.ts` was corrected to match the
backend's `TopWantedSuspectSerializer` — added `photo_url`, `most_wanted_score`,
`reward_amount`, `days_wanted`, `case_id`, `case_title`; removed incorrect
`status` and `danger_level` fields.

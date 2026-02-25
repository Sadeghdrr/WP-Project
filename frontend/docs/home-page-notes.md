# Home Page – Implementation Notes

## Overview

The Home page (`/`) is the public landing page of the LAPD Case Management
System.  It satisfies **§5.1** of the project specification (200 pts):

- General introduction to the system + police department + duties.
- At least 3 statistical metrics regarding cases and their statuses.

## Endpoint Used

| Endpoint                  | Method | Auth Required | Purpose                   |
|---------------------------|--------|---------------|---------------------------|
| `/api/core/dashboard/`    | GET    | Yes           | Fetch department-wide stats|

### Response Shape

```jsonc
{
  "total_cases": 42,
  "active_cases": 12,
  "closed_cases": 28,
  "voided_cases": 2,
  "total_suspects": 67,
  "total_evidence": 134,
  "total_employees": 25,
  "unassigned_evidence_count": 3,
  "cases_by_status": [{ "status": "OP", "label": "Open", "count": 8 }],
  "cases_by_crime_level": [{ "crime_level": 1, "label": "Misdemeanour", "count": 5 }],
  "top_wanted_suspects": [{ "id": 1, "full_name": "..." }],
  "recent_activity": [{ "timestamp": "...", "type": "case_created", "description": "...", "actor": "..." }]
}
```

## Metrics Displayed

| Metric          | Field             | Accent   |
|-----------------|-------------------|----------|
| Total Cases     | `total_cases`     | primary  |
| Active Cases    | `active_cases`    | warning  |
| Closed Cases    | `closed_cases`    | success  |
| Total Suspects  | `total_suspects`  | primary  |
| Evidence Items  | `total_evidence`  | primary  |
| Employees       | `total_employees` | primary  |

## Auth-Conditional Fetch Strategy

The dashboard endpoint requires `IsAuthenticated`.  The Home route, however,
is **public** (outside `ProtectedRoute` / `AppLayout`).

Strategy:
- Read `status` from `useAuth()`.
- If `status === "authenticated"` → enable React Query fetch → show live data.
- If unauthenticated → show "—" placeholders + italic hint asking user to sign in.

This avoids blocking the public page on auth while still displaying real data
for logged-in users.

## Loading & Error States

- **Loading**: A 6-card skeleton grid with a shimmer animation is shown while
  the query is in-flight.
- **Error**: A red error message is displayed; stat cards are not rendered.

## Responsive Behaviour

- `> 640 px`: 2-column duty grid, auto-fit stats grid (up to 6 columns).
- `≤ 640 px`: 1-column duty grid, 2-column stats grid, smaller font sizes.

## Deferred Enhancements

- Charts (cases by status / crime level) once a charting library is adopted.
- "Top 5 Most Wanted" suspect cards below stats.
- Recent activity feed / timeline.
- Quick-action buttons (New Case, Search) for authenticated users.

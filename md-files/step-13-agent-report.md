# Step 13 Agent Report — Case & Complaint Status Workspace

## Files Created

| File | Purpose |
|---|---|
| `frontend/src/api/cases.ts` | Cases API service (all case endpoints) |
| `frontend/src/hooks/useCases.ts` | React Query hooks (useCases, useCaseDetail, useCaseActions) |
| `frontend/src/lib/caseWorkflow.ts` | Status labels, colours, workflow action map, permission logic |
| `frontend/src/pages/Cases/CaseListPage.module.css` | Styles for case list page |
| `frontend/src/pages/Cases/CaseDetailPage.module.css` | Styles for case detail page |
| `frontend/docs/cases-workspace-notes.md` | Implementation notes (endpoints, status model, deferred) |

## Files Modified

| File | Change |
|---|---|
| `frontend/src/api/endpoints.ts` | Added 18 case workflow/assignment endpoint paths |
| `frontend/src/api/index.ts` | Added casesApi barrel export |
| `frontend/src/types/cases.ts` | Added CaseListItem, CaseDetail, CaseCalculations, workflow request DTOs |
| `frontend/src/types/index.ts` | Updated barrel exports for new types |
| `frontend/src/hooks/index.ts` | Added useCases/useCaseDetail/useCaseActions exports |
| `frontend/src/lib/index.ts` | Added caseWorkflow exports |
| `frontend/src/pages/Cases/CaseListPage.tsx` | Replaced placeholder with full implementation |
| `frontend/src/pages/Cases/CaseDetailPage.tsx` | Replaced placeholder with full implementation |

## Case/Complaint Requirements Implemented

### Case List Page (§5.6)
- Fetches and displays all cases visible to authenticated user
- Filters: search (text), status, crime level, creation type
- Status badge with colour-coded display
- Crime level badge with colour-coded display
- Creation type display (Complaint / Crime Scene)
- Assigned detective name
- Click-through navigation to case detail
- Loading skeleton, error state, empty state
- Responsive layout (hides columns on mobile)

### Case Detail Page (§5.6)
- Full case metadata (status, crime level, dates, location, rejection count)
- Assigned personnel section (detective, sergeant, captain, judge)
- Case description
- Complainants table (name, primary flag, approval status)
- Witnesses table (name, phone, national ID)
- Calculations section (crime degree, days, threshold, reward)
- Status history timeline (transitions with who/when/message)
- Loading skeleton, error state
- Responsive grid layout

### Workflow Action Panel (§5.6)
- Shows available actions based on current status + user permissions
- Supports all 15 backend workflow transitions:
  - Submit for review, Resubmit
  - Cadet approve/reject, Re-forward to officer
  - Officer approve/reject
  - Approve crime scene
  - Declare suspects
  - Sergeant approve/reject
  - Begin interrogation, Send to captain review
  - Forward to judiciary, Escalate to chief
  - Close case
- Rejection actions show modal requiring message input
- Loading/disabled state during mutations
- Toast notifications for success/error
- Terminal states (voided/closed) show informational message
- No-action state for users without permissions at current stage

## Endpoints Used

19 case-related endpoints covering:
- CRUD: list, detail, create, update, delete
- Workflow: submit, resubmit, cadet-review, officer-review, approve-crime-scene, declare-suspects, sergeant-review, forward-judiciary, transition
- Assignment: assign-detective, assign-sergeant, assign-captain, assign-judge, unassign-detective
- Sub-resources: status-log, calculations

## State-Transition Constraints Respected

The frontend workflow action map (`STATUS_ACTIONS` in `caseWorkflow.ts`) mirrors the backend `ALLOWED_TRANSITIONS` exactly:

- Each status maps to only the transitions the backend supports
- Each action requires specific permissions (OR logic matching backend)
- No frontend-invented transitions
- Rejection actions require a message (matching backend validation)
- 3-rejection voiding is handled by backend; frontend just shows the status
- Terminal states prevent further actions
- Crime scene auto-approval by Police Chief is backend-side logic (no frontend override)

## Deferred Items

| Item | Reason |
|---|---|
| File Complaint form | Placeholder page exists; form implementation deferred to a focused step |
| Crime Scene form | Placeholder page exists; form implementation deferred |
| Inline case editing | PATCH support built in API layer; UI deferred |
| Personnel assignment picker | Requires filtered user list dropdown by role; deferred |
| Complainant add/review UI | API ready; UI deferred to case management deep step |
| Witness add UI | API ready; UI deferred |
| Case delete UI | Admin-only; deferred |
| Full report view | Judiciary report endpoint ready; UI deferred to Reporting step |

## Backend Anomalies / Problems

1. **No pagination on case list**: `GET /api/cases/cases/` returns all cases without pagination. For large datasets this could cause performance issues. The frontend currently handles this but would benefit from paginated responses.

2. **User references in detail are IDs, not objects**: `CaseDetailSerializer` returns `created_by`, `approved_by`, `assigned_detective` etc. as integer foreign keys, not nested user objects. The frontend displays "User #N" which is functional but not user-friendly. The list serializer does include `assigned_detective_name` which is better.

3. **Complainant/witness/status_log nesting**: The detail serializer nests these as arrays which is efficient. However, the `changed_by` and `user` fields within these nested objects may come as either integer IDs or nested objects depending on backend serializer configuration — the frontend handles both shapes defensively.

## Confirmation

- **No backend files were modified** — all changes are in `frontend/` and `md-files/`
- **App compiles** — both `tsc --noEmit` and `vite build` succeed with zero errors

## Coverage Summary (vs project-doc §5.6, 200 pts)

| Requirement | Status | Notes |
|---|---|---|
| View cases relevant to user | **Implemented** | List with filters, role-scoped by backend |
| View complaints relevant to user | **Implemented** | Same list, filtered by creation_type |
| Edit cases if permitted | **Partial** | API layer supports PATCH; detail page shows metadata but inline edit form deferred |
| Status visibility | **Implemented** | Colour-coded badges on list and detail |
| Approve/reject/alter statuses | **Implemented** | Full workflow action panel with 15 transitions |
| Loading states | **Implemented** | Skeleton on list and detail pages |
| Error states | **Implemented** | ErrorState with retry on both pages |
| Responsive layout | **Implemented** | CSS responsive breakpoints for mobile |

# Step 25 — Agent Report: Frontend Bug Fixes

## Summary

Resolved 9 frontend bugs covering workflow actions, dashboard display, permission gating, UI overflow, state management, case lifecycle API ordering, post-action navigation, and evidence file uploads. All fixes are frontend-only — no backend files were modified.

## Branch

`agent/step-25-bug-fixes`

## Files Modified

| # | File | Fixes |
|---|------|-------|
| 1 | `frontend/src/pages/Cases/CaseDetailPage.tsx` | Fix 1, 7, 8 |
| 2 | `frontend/src/pages/Cases/FileComplaintPage.tsx` | Fix 7 |
| 3 | `frontend/src/pages/Dashboard/DashboardPage.tsx` | Fix 2 |
| 4 | `frontend/src/pages/Home/HomePage.tsx` | Fix 2 |
| 5 | `frontend/src/components/layout/Sidebar.tsx` | Fix 3, 4 |
| 6 | `frontend/src/pages/Register/RegisterPage.module.css` | Fix 5 |
| 7 | `frontend/src/pages/Admin/UserManagementPage.tsx` | Fix 6 |
| 8 | `frontend/src/pages/Evidence/AddEvidencePage.tsx` | Fix 9 |

## Files Created

| File | Purpose |
|------|---------|
| `frontend/docs/step-25-fixes-notes.md` | Root-cause analysis and fix notes |
| `md-files/step-25-agent-report.md` | This report |

## Bug Fix Details

### Fix 1: assign_detective Unknown Action
- **Problem**: Clicking "Assign Detective" showed "Unknown action" error
- **Cause**: Missing `case "assign_detective"` branch in `executeAction` switch
- **Solution**: Added the switch case + an assignment modal with user ID input calling `actions.assignDetective.mutateAsync({ user_id })`

### Fix 2: Dashboard API / Cards
- **Problem**: HomePage showed 6 cards (should be 4); DashboardPage had "Unassigned Evidence" card
- **Solution**: Reduced HomePage to 4 cards (Total Cases, Active Cases, Total Suspects, Employees). Removed "Unassigned Evidence" from DashboardPage

### Fix 3: Admin Panel Sidebar Permission
- **Problem**: Admin Panel link used `VIEW_USER`/`VIEW_ROLE`/`CHANGE_USER`/`CHANGE_ROLE` (too permissive)
- **Solution**: Changed to `CAN_MANAGE_USERS` permission only

### Fix 4: Crime Scene Sidebar Link
- **Problem**: No sidebar entry for "Report Crime Scene" route
- **Solution**: Added "Actions" section with "Report Crime Scene" link gated by `CAN_CREATE_CRIME_SCENE`

### Fix 5: Registration Page Overflow
- **Problem**: First/Last Name inputs overflowed the 2-column grid layout
- **Solution**: Added `width: 100%; min-width: 0; box-sizing: border-box;` to `.input` CSS class

### Fix 6: Admin Role Dropdown State Sync
- **Problem**: Role dropdown reset to original value on every render, preventing changes
- **Cause**: Render-time state sync compared `selectedRoleId !== userRoleId` — always true when user selects a new role
- **Solution**: Replaced with `useRef`-based tracking that only resets dropdown when selected user changes (different user ID)

### Fix 7: Case Creation Workflow API Order
- **Problem (complaint)**: File complaint only created case but never submitted it for review
- **Problem (resubmit)**: "Edit & Resubmit" only called resubmit without updating case data first
- **Solution**: Chained `submitForReview()` after case creation. Added edit form modal that calls `PUT update` then `POST resubmit`

### Fix 8: 404 After Case Approval Actions
- **Problem**: After approval actions, user stayed on detail page but lost access → 404/403
- **Solution**: Added post-action redirect to `/cases` for approval/forward/close actions

### Fix 9: Evidence File Upload on Create
- **Problem**: AddEvidencePage had no file upload fields
- **Solution**: Added multi-file upload section (file + type + caption). After evidence creation, files are uploaded via `uploadFile()` API call

## Permission Logic Corrections

| Component | Before | After |
|-----------|--------|-------|
| Admin Panel (Sidebar) | `VIEW_USER \| VIEW_ROLE \| CHANGE_USER \| CHANGE_ROLE` | `CAN_MANAGE_USERS` |
| Crime Scene (Sidebar) | Not present | `CAN_CREATE_CRIME_SCENE` |

## API Call Corrections

| Workflow | Before | After |
|----------|--------|-------|
| File Complaint | `POST /api/cases` | `POST /api/cases` → `POST /api/cases/{id}/submit` |
| Edit & Resubmit | `POST /api/cases/{id}/resubmit` | `PUT /api/cases/{id}` → `POST /api/cases/{id}/resubmit` |
| Evidence Create | `POST /api/evidence` | `POST /api/evidence` → `POST /api/evidence/{id}/files/` (per file) |

## Backend Anomalies

None observed. All required endpoints exist and accept the expected payloads:
- `POST /api/cases/{id}/assign-detective/` accepts `{ user_id }`
- `POST /api/cases/{id}/submit/` exists for review submission
- `PUT /api/cases/{id}/` accepts case data updates
- `POST /api/evidence/{id}/files/` accepts multipart file uploads

## Confirmation

- ✅ Zero backend file modifications
- ✅ TypeScript compilation passes with no errors
- ✅ IDE diagnostics show no errors on all modified files
- ✅ All 9 bugs addressed with root-cause fixes (not workarounds)

---

## Addendum: Additional Fixes (Edit + Dashboard)

### New Scope
Three additional issues were resolved in a follow-up pass:

#### Fix A: Evidence Edit (PATCH /api/evidence/{id}/)
- **File**: `frontend/src/pages/Evidence/EvidenceDetailPage.tsx`
- **CSS**: `frontend/src/pages/Evidence/EvidenceDetailPage.module.css`
- **Root cause**: No edit capability existed on the detail page — only delete
- **Solution**: Added `isEditing` state + `handleEditSave` callback. "✏️ Edit" button in header (gated by `evidence.change_evidence` permission) toggles an inline edit form below the header. Form edits `title` and `description` via `actions.updateEvidence.mutateAsync`. On success the query cache is invalidated and edit mode exits.
- **New CSS classes**: `.btnEdit`, `.btnCancel`, `.editForm`, `.editField`

#### Fix B: Case Edit (PATCH /api/cases/{id}/)
- **File**: `frontend/src/pages/Cases/CaseDetailPage.tsx`
- **Root cause**: No standalone edit capability (the Edit & Resubmit workflow modal was only accessible during resubmit flow)
- **Solution**: Added `isEditing` + edit state (title, description, location, incident_date) as hooks above the early `isLoading`/`error` guards. "✏️ Edit Case" button in `detailHeader` right side (gated by `cases.change_case` + non-terminal status). When editing, an inline form section appears between the workflow panel and the data grid. Save calls `casesApi.updateCase()` (PATCH) then `refetch()`.

#### Fix C: Dashboard API for Unauthenticated Users
- **File**: `frontend/src/pages/Home/HomePage.tsx`
- **Root cause**: `enabled: isAuthenticated` prevented the `GET /api/core/dashboard/` call when auth status was not `"authenticated"`
- **Solution**: Changed to `enabled: authStatus !== "loading"` — fetches stats as soon as auth state resolves (regardless of outcome). `retry: isAuthenticated ? 1 : 0` prevents retry loops for unauthenticated 403 responses. UI updated: skeleton shows for all users while loading; error state only shown to authenticated users; removed "Sign in to see statistics" hint since stats are attempted regardless.

### Addendum File Changes

| File | Change |
|------|--------|
| `frontend/src/pages/Evidence/EvidenceDetailPage.tsx` | Inline edit mode with PATCH |
| `frontend/src/pages/Evidence/EvidenceDetailPage.module.css` | Edit button + form styles |
| `frontend/src/pages/Cases/CaseDetailPage.tsx` | Inline edit mode with PATCH |
| `frontend/src/pages/Home/HomePage.tsx` | Dashboard API enabled for all auth states |

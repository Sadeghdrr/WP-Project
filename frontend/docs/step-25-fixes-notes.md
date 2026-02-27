# Step 25 — Bug Fixes Notes

## Root Cause Analysis & Fix Approach

### 1. Unknown action: assign_detective

**Root cause**: The `executeAction` switch in `WorkflowPanel` (CaseDetailPage.tsx) had no `case "assign_detective"` branch. The action key existed in `STATUS_ACTIONS` (caseWorkflow.ts) and the API hook (`actions.assignDetective`) existed in `useCaseActions`, but the switch fell through to `default` throwing "Unknown action: assign_detective".

**Fix**: Added `assign_detective` case to the switch + a dedicated modal with a user ID input that calls `actions.assignDetective.mutateAsync({ user_id })`. The modal opens when the "Assign Detective" button is clicked, collects a user ID, and makes the API call.

### 2. Dashboard API Not Called + Wrong Cards

**Root cause (HomePage)**: The home page displayed 6 cards (Total Cases, Active Cases, Closed Cases, Total Suspects, Evidence Items, Employees) instead of the required 4. The API call itself was already present and working.

**Root cause (DashboardPage)**: The dashboard showed 8 stat cards including "Unassigned Evidence". The requirement was to remove it.

**Fix**: 
- HomePage: Filtered `statCards` to only 4: Total Cases, Active Cases, Total Suspects, Employees
- DashboardPage: Removed "Unassigned Evidence" from the `StatsOverview` items array

### 3. Admin Panel Visibility Permission

**Root cause**: The sidebar used `[P.ACCOUNTS.VIEW_USER, P.ACCOUNTS.VIEW_ROLE, P.ACCOUNTS.CHANGE_USER, P.ACCOUNTS.CHANGE_ROLE]` with OR logic — any user with basic view permissions could see the admin link.

**Fix**: Changed to `[P.ACCOUNTS.CAN_MANAGE_USERS]` which is the proper admin-level permission.

### 4. Crime Scene Creation Sidebar Permission

**Root cause**: No sidebar link existed for "Report Crime Scene". The route existed but wasn't discoverable from the sidebar for authorized users.

**Fix**: Added a new "Actions" nav section with a "Report Crime Scene" link gated by `P.CASES.CAN_CREATE_CRIME_SCENE`.

### 5. Registration Page UI Bug

**Root cause**: The `.input` CSS class in RegisterPage.module.css lacked `width: 100%`, `min-width: 0`, and `box-sizing: border-box`. Inside the 2-column `.row` grid, inputs could exceed their grid cell width, causing the Last Name field to overflow.

**Fix**: Added `width: 100%; min-width: 0; box-sizing: border-box;` to the `.input` class.

### 6. Admin Role Dropdown Not Changing Role

**Root cause**: In `UserDetailPanel`, the synchronization logic ran on every render:
```tsx
const userRoleId = user?.role_detail?.id ?? "";
if (selectedRoleId !== userRoleId && userRoleId !== "") {
  setSelectedRoleId(userRoleId);
}
```
When a user selected a *new* role from the dropdown, `selectedRoleId` changed, but `userRoleId` remained the original role from the API. Since `selectedRoleId !== userRoleId` was true, it immediately reset the dropdown back to the original role.

**Fix**: Replaced the render-time sync with a `useRef` + `useEffect` pattern that only resets the dropdown when the *user ID* changes (switching between different users in the panel), not on every render.

### 7. Case Creation Workflow Incorrect API Order

**Root cause (complaint creation)**: `FileComplaintPage` only called `POST /api/cases` (creating the case in `complaint_registered` status) without chaining `POST /api/cases/{id}/submit` to advance it to `cadet_review`.

**Root cause (edit & resubmit)**: The "Edit & Resubmit" workflow action only called `POST /api/cases/{id}/resubmit` without first updating the case data via `PUT /api/cases/{id}`.

**Fix**: 
- FileComplaintPage: After successful case creation, chains `submitForReview(data.id)` before navigating
- CaseDetailPage: "Edit & Resubmit" now opens an edit form modal pre-filled with case data. On submit, it calls `PUT /api/cases/{id}` then `POST /api/cases/{id}/resubmit`

### 8. 404 After Case Approval

**Root cause**: After a cadet approves a case (transitioning it from `cadet_review` to `officer_review`), the cadet may lose scope-based access to the case. React Query refetches the detail and gets a 403/404, displaying an error.

**Fix**: Added a `REDIRECT_ACTIONS` set containing action keys (`cadet_approve`, `officer_approve`, `approve_crime_scene`, `cadet_reforward`, `forward_judiciary`, `close_case`) that may cause the user to lose access. After these actions succeed, the user is navigated to `/cases` instead of staying on the detail page.

### 9. Evidence Creation Page Missing File Upload

**Root cause**: The `AddEvidencePage` form had no file upload fields. The `EvidenceDetailPage` (edit/view) had a full file upload section, but the create page was missing it entirely. Since files are uploaded to a per-evidence endpoint (`POST /api/evidence/{id}/files/`), the evidence must be created first before files can be attached.

**Fix**: Added file upload state and UI to AddEvidencePage. Users can add multiple file entries (file + type + caption). After the evidence is created via the API, each attached file is uploaded sequentially via `uploadFile()`. Navigation only proceeds after all uploads complete.

## Architectural Observations

- The permission system is well-structured with `P.*` constants matching `app_label.codename` format
- The `canAny()` helper provides clean OR-logic permission checking
- The `useCaseActions` hook already had all assignment mutations implemented — only the UI was missing
- The `casesApi.updateCase` function existed but was unused by any component
- The evidence file upload API (`uploadFile`) was already implemented in the API layer and used by the detail page

## Edge Cases Handled

- Assign detective: validates user ID is a number before calling API
- File complaint: if `submitForReview` fails after creation, navigation still proceeds (user can submit from detail page)  
- Edit & resubmit: validation requires non-empty title and description
- Evidence file upload: if some file uploads fail, a warning is shown but the evidence is still created
- Admin role dropdown: ref-based tracking prevents render-loop while allowing intentional user changes

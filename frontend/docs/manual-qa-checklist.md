# Manual QA Checklist

**Date:** 2026-02-27  
**Purpose:** Practical test scenarios for demo/submission validation  
**Environment:** Docker Compose (`docker compose up --build`) or local dev (`npm run dev` in frontend/)

---

## Preconditions

### Required Accounts

| Role | How to Create | Used In |
|---|---|---|
| **Base User** (Complainant) | Register via `/register` | Complaint filing, bounty tip submission |
| **Cadet** | Admin assigns role | Complaint review |
| **Police Officer** | Admin assigns role | Complaint approval, crime scene reporting |
| **Detective** | Admin assigns role | Detective board, evidence, suspect declaration |
| **Sergeant** | Admin assigns role | Sergeant review, interrogation |
| **Captain** | Admin assigns role | Forward to judiciary |
| **Police Chief** | Admin assigns role | Critical case oversight |
| **Judge** | Admin assigns role | Trial / General Reporting |
| **Coroner** | Admin assigns role | Evidence verification (biological) |
| **System Admin** | Django superuser (`python manage.py createsuperuser`) or hierarchy ≥ 100 | Admin panel |

### Required Data
- At least 1 case created via complaint flow (with complainant)
- At least 1 case created via crime scene flow (with witnesses)
- Evidence attached to a case (at least one of each type if possible)
- At least 1 suspect identified in a case (via backend or workflow)

---

## Test Scenarios

### 1. Home Page (`/`)

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 1.1 | Public view (unauthenticated) | Navigate to `/` without login | Hero section visible. System intro text displayed. Stats show "—" or zero placeholders. | ☐ |
| 1.2 | Authenticated view | Login, then navigate to `/` | Stats cards populate with real numbers (Total Cases, Active, Solved, Employees, Suspects, Evidence). | ☐ |
| 1.3 | Responsive layout | Resize browser to < 640px | Layout stacks vertically. Stats grid collapses to fewer columns. No horizontal overflow. | ☐ |

### 2. Login Page (`/login`)

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 2.1 | Valid login | Enter valid username + password → Submit | Redirect to `/dashboard`. User info in header. | ☐ |
| 2.2 | Login with email | Enter email as identifier | Login succeeds (backend accepts email login per §4.1). | ☐ |
| 2.3 | Login with national ID | Enter national_id as identifier | Login succeeds. | ☐ |
| 2.4 | Login with phone | Enter phone number as identifier | Login succeeds. | ☐ |
| 2.5 | Invalid credentials | Enter wrong password | Error message displayed inline. Form not cleared. | ☐ |
| 2.6 | Empty form submit | Click submit with empty fields | Submit button disabled or validation prevents submission. | ☐ |
| 2.7 | Already authenticated | Navigate to `/login` while logged in | Redirect to `/dashboard`. | ☐ |

### 3. Registration Page (`/register`)

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 3.1 | Valid registration | Fill all 8 fields (username, email, phone, national_id, first_name, last_name, password, confirm_password) → Submit | Account created. Auto-login. Redirect to `/dashboard`. | ☐ |
| 3.2 | Password mismatch | Enter different passwords | Client-side error: "Passwords do not match". | ☐ |
| 3.3 | Duplicate username | Use existing username | Backend field error shown inline under username field. | ☐ |
| 3.4 | Duplicate email/phone/national_id | Use existing values | Backend field errors shown per field. | ☐ |
| 3.5 | Responsive | Resize < 480px | Form adapts to single column. All fields accessible. | ☐ |

### 4. Modular Dashboard (`/dashboard`)

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 4.1 | Skeleton loading | Navigate to dashboard (first load or cache cleared) | Skeleton cards animate before data arrives. | ☐ |
| 4.2 | Stats overview | Wait for data load | 8 stat cards: Total Cases, Active, Closed, Voided, Suspects, Evidence, Employees, Unassigned Evidence. | ☐ |
| 4.3 | Permission-gated widgets (Detective) | Login as Detective | Detective Board widget visible. Quick action for "Browse Cases". Case widgets visible. | ☐ |
| 4.4 | Permission-gated widgets (Cadet) | Login as Cadet | No Detective Board widget. Limited quick actions. | ☐ |
| 4.5 | Permission-gated widgets (Admin) | Login as Admin/Chief | Admin widget visible. All widgets visible. | ☐ |
| 4.6 | Quick actions | Click each quick action button | Navigates to correct page (File Complaint, Crime Scene, Cases, Most Wanted, etc.). | ☐ |
| 4.7 | Error state | Disconnect API / bad token | ErrorState component with "Try Again" button. | ☐ |
| 4.8 | Responsive | Resize to < 768px, then < 480px | Grid collapses gracefully. Cards stack vertically. | ☐ |

### 5. Case & Complaint Status

#### 5a. Case List (`/cases`)

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 5a.1 | List loads | Navigate to `/cases` | Table of cases with status badges, crime level badges, creation type. | ☐ |
| 5a.2 | Search filter | Type in search box (wait for debounce ~400ms) | Table filters by search term. | ☐ |
| 5a.3 | Status filter | Select a status from dropdown | Table shows only matching status. | ☐ |
| 5a.4 | Crime level filter | Select a crime level | Table filters accordingly. | ☐ |
| 5a.5 | Empty state | Apply filters that match nothing | EmptyState component displayed. | ☐ |
| 5a.6 | Navigation to detail | Click a case row | Navigates to `/cases/:id` with full detail. | ☐ |
| 5a.7 | Skeleton loading | Initial page load | Skeleton table rows animated. | ☐ |
| 5a.8 | Responsive | Resize < 768px | Table adapts or scrolls horizontally. Filters stack. | ☐ |

#### 5b. File Complaint (`/cases/new/complaint`)

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 5b.1 | Valid complaint | Fill title, description, crime_level, incident_date, location → Submit | Case created. Redirect to case detail. | ☐ |
| 5b.2 | Missing required field | Omit title → Submit | Error message shown. | ☐ |
| 5b.3 | Responsive | Resize < 640px | Form adapts to single column. | ☐ |

#### 5c. Crime Scene (`/cases/new/crime-scene`)

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 5c.1 | Valid crime scene | Fill form + add 2 witnesses (name, phone, national_id each) → Submit | Case created with witnesses. Redirect to detail. | ☐ |
| 5c.2 | Dynamic witnesses | Click "Add Witness" multiple times, then remove one | Witness rows add/remove dynamically. | ☐ |
| 5c.3 | No witnesses | Submit without adding any witnesses | Case created successfully (witnesses optional in crime scene). | ☐ |

#### 5d. Case Detail (`/cases/:id`)

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 5d.1 | Full metadata | Open a case detail | Title, description, status, crime level, creation type, dates, location all visible. | ☐ |
| 5d.2 | Personnel section | Open a case with assigned personnel | Detective, Sergeant, Captain, Judge names displayed if assigned. | ☐ |
| 5d.3 | Complainants table | Open a complaint case | Complainants listed in table format. | ☐ |
| 5d.4 | Witnesses table | Open a crime scene case | Witnesses listed with name, phone, national ID. | ☐ |
| 5d.5 | Status log timeline | Scroll to status history | Timeline of status transitions with timestamps. | ☐ |
| 5d.6 | **Workflow: Submit** (Complainant) | Login as complainant who filed case → Click Submit | Case moves to "Submitted" status. | ☐ |
| 5d.7 | **Workflow: Cadet Review** (Cadet) | Login as Cadet → Approve or Reject with message | Case moves to next status. Rejection message visible. | ☐ |
| 5d.8 | **Workflow: Officer Review** (Officer) | Login as Officer → Approve or Reject | Case approved → Open status. | ☐ |
| 5d.9 | **Workflow: Declare Suspects** (Detective) | Login as Detective → Click Declare Suspects | Case transitions. | ☐ |
| 5d.10 | **Workflow: Sergeant Review** (Sergeant) | Login as Sergeant → Approve or Reject | Case moves forward or back. | ☐ |
| 5d.11 | **Workflow: Forward to Judiciary** (Captain) | Login as Captain → Forward | Case forwarded for trial. | ☐ |
| 5d.12 | Evidence link | Click "View Evidence" or evidence count | Navigates to evidence list for this case. | ☐ |
| 5d.13 | Board link | Click "Detective Board" | Navigates to detective board for this case. | ☐ |
| 5d.14 | Rejection message modal | When rejecting, type a message → Confirm | Message sent. Toast notification. | ☐ |
| 5d.15 | Skeleton loading | Navigate to case detail (cold cache) | Skeleton placeholder renders before data. | ☐ |

### 6. Detective Board (`/detective-board/:caseId`)

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 6.1 | Board loads | Navigate to board for an existing case | ReactFlow canvas renders. MiniMap, Controls, Background visible. | ☐ |
| 6.2 | Auto-create board | Navigate to board for a case without a board | Board auto-created. Empty canvas shown. | ☐ |
| 6.3 | Pin entity | Click "Pin Entity" → Select evidence/note → Confirm | New node appears on canvas. | ☐ |
| 6.4 | Drag & drop | Drag a node to new position | Node moves. Position saved (debounced 800ms). | ☐ |
| 6.5 | Connect nodes (red line) | Drag from one node handle to another | Red line connects the two nodes. Persisted to backend. | ☐ |
| 6.6 | Remove connection | Click a connection → Delete | Connection removed. | ☐ |
| 6.7 | Sticky notes | Add a note via sidebar → Edit text | Note appears on canvas. Editable. | ☐ |
| 6.8 | Delete note | Delete a sticky note | Note removed from canvas. | ☐ |
| 6.9 | PNG export | Click "Export as Image" | PNG downloaded. Contains current board state. | ☐ |
| 6.10 | Error boundary | Force error (e.g., malformed data) | BoardErrorBoundary catches. Fallback UI shown. | ☐ |
| 6.11 | Responsive | Resize < 768px | Canvas scales. Controls remain accessible. | ☐ |

### 7. Most Wanted (`/most-wanted`)

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 7.1 | Cards load | Navigate to `/most-wanted` | Cards displayed with rank, photo, name, national ID, status, days wanted, score, bounty. | ☐ |
| 7.2 | Score formula | Check most-wanted score | Score = max_days_wanted × highest_crime_degree. Values match backend calculation. | ☐ |
| 7.3 | Bounty display | Check bounty amount | Formatted in Rials. | ☐ |
| 7.4 | Skeleton loading | Initial load | 6 skeleton cards animate. | ☐ |
| 7.5 | Empty state | No wanted suspects in system | EmptyState message displayed. | ☐ |
| 7.6 | Responsive | Resize < 640px | Cards stack vertically. Images scale. | ☐ |

### 8. Evidence

#### 8a. Evidence List (`/cases/:id/evidence`)

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 8a.1 | List loads | Navigate to evidence list for a case | Table with type badges, titles, dates. | ☐ |
| 8a.2 | Type filter | Select evidence type dropdown | Table filters by type. | ☐ |
| 8a.3 | Search | Type in search box | Debounced filter (300ms). | ☐ |
| 8a.4 | Navigate to detail | Click an evidence row | Navigates to evidence detail page. | ☐ |
| 8a.5 | Navigate to add | Click "Add Evidence" | Navigates to `/cases/:id/evidence/new`. | ☐ |

#### 8b. Add Evidence (`/cases/:id/evidence/new`)

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 8b.1 | Testimony | Select "Testimony" → Fill title, description, transcript → Submit | Evidence created. Redirect to detail. | ☐ |
| 8b.2 | Biological/Medical | Select "Biological" → Fill title, description, add images → Submit | Evidence created with pending verification status. | ☐ |
| 8b.3 | Vehicle | Select "Vehicle" → Fill model, color, license_plate → Submit | Evidence created. | ☐ |
| 8b.4 | Vehicle XOR validation | Fill both license_plate AND serial_number | Client-side error: cannot have both. | ☐ |
| 8b.5 | Vehicle: plate only | Fill license_plate, leave serial_number empty | Accepted. | ☐ |
| 8b.6 | Vehicle: serial only | Fill serial_number, leave license_plate empty | Accepted. | ☐ |
| 8b.7 | Identity Document | Select "Identity" → Fill owner name → Add key-value pairs → Submit | Evidence created with key-value data. | ☐ |
| 8b.8 | Identity: dynamic KV | Add 3 key-value pairs → Remove middle one | Rows add/remove correctly. | ☐ |
| 8b.9 | Other Items | Select "Other" → Fill title, description → Submit | Evidence created. | ☐ |
| 8b.10 | Backend field errors | Submit with invalid data | Errors mapped to specific form fields. | ☐ |

#### 8c. Evidence Detail (`/cases/:id/evidence/:id`)

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 8c.1 | Type-specific display | Open evidence of each type | Fields match evidence type (transcript for testimony, model/plate for vehicle, etc.). | ☐ |
| 8c.2 | File upload | Click upload → Select image/video/audio/document | File uploaded. Appears in attachments. | ☐ |
| 8c.3 | File preview | Click an uploaded image | MediaViewer opens with preview. | ☐ |
| 8c.4 | Coroner verification | Login as Coroner → Open biological evidence → Verify/Reject | Verification status updates. Toast notification. | ☐ |
| 8c.5 | Chain of custody | Scroll to chain-of-custody section | Timeline of custody events displayed. | ☐ |
| 8c.6 | Delete evidence | Click Delete → Confirm | Evidence deleted. Redirect to list. | ☐ |

### 9. General Reporting (`/reports`)

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 9.1 | Case list for reports | Navigate to `/reports` | Searchable case list table. | ☐ |
| 9.2 | Search | Type case title in search box | Table filters. | ☐ |
| 9.3 | Open report | Click a case row | Full aggregated report view opens (`/reports/:caseId`). | ☐ |
| 9.4 | Report content | View report | Case info, creation date, personnel (names + ranks), complainants, witnesses, evidence, suspects, interrogations, trials, status history timeline. | ☐ |
| 9.5 | Print | Click "Print" button | Browser print dialog opens. Print-optimized layout (no nav, clean formatting). | ☐ |
| 9.6 | Role restriction | Login as Judge/Captain/Chief | Report accessible. |  ☐ |
| 9.7 | Skeleton loading | Navigate to report (cold cache) | Skeleton placeholder renders. | ☐ |

### 10. Bounty Tips

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 10.1 | Submit tip (normal user) | Navigate to `/bounty-tips/new` → Fill suspect ID, case ID, info → Submit | Tip created. Success card shown. | ☐ |
| 10.2 | Tip list (officer) | Login as Officer → Navigate to `/bounty-tips` | List of tips with status filter. | ☐ |
| 10.3 | Inline review (officer) | Click review action on a tip → Approve/Reject | Tip status updates inline. | ☐ |
| 10.4 | Inline verify (detective) | Login as Detective → Verify a reviewed tip | Tip verified. Unique code generated. | ☐ |
| 10.5 | Verify reward | Navigate to `/bounty-tips/verify` → Enter national ID + unique code | Result card: tip details, reward amount, claimed status. | ☐ |
| 10.6 | Invalid lookup | Enter wrong national ID or code | Error message displayed. | ☐ |

### 11. Admin Panel (`/admin`)

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 11.1 | Access guard | Login as non-admin → Navigate to `/admin` | Access denied message (hierarchy < 100). | ☐ |
| 11.2 | Overview | Login as Admin → Navigate to `/admin` | Stats (users total/active/inactive, roles count). Nav cards. | ☐ |
| 11.3 | User list | Navigate to `/admin/users` | Searchable, filterable user table. | ☐ |
| 11.4 | User detail | Click a user row | Slide-out detail panel with user info. | ☐ |
| 11.5 | Assign role | Select role from dropdown → Confirm | Role assigned. Toast notification. | ☐ |
| 11.6 | Activate/Deactivate user | Click activate or deactivate button | User status toggles. Toast notification. | ☐ |
| 11.7 | Role list | Navigate to `/admin/roles` | Role cards with hierarchy badges. | ☐ |
| 11.8 | Create role | Click "Create Role" → Fill name, hierarchy → Submit | Role created. Appears in list. | ☐ |
| 11.9 | Edit role | Click edit on a role → Modify → Save | Role updated. | ☐ |
| 11.10 | Delete role | Click delete on a role → Confirm | Role deleted. | ☐ |
| 11.11 | Assign permissions | Click permissions on a role → Select permissions → Save | Permissions assigned. Matches §2.2 "without changing code" requirement. | ☐ |
| 11.12 | Responsive | Resize < 768px | Tables/cards adapt. Detail panel stacks. | ☐ |

### 12. Cross-Cutting

| # | Scenario | Steps | Expected Result | Pass? |
|---|---|---|---|---|
| 12.1 | **Lazy loading** | Navigate between pages (watch Network tab) | JS chunks load on demand (not upfront). | ☐ |
| 12.2 | **404 page** | Navigate to `/nonexistent-page` | NotFoundPage with back/home links. | ☐ |
| 12.3 | **403 page** | Navigate to `/forbidden` | ForbiddenPage displayed. | ☐ |
| 12.4 | **Auth token refresh** | Wait for access token to expire → Perform action | Token silently refreshed. No forced logout. | ☐ |
| 12.5 | **Logout** | Click Logout | Redirected to `/login`. Tokens cleared. Protected routes inaccessible. | ☐ |
| 12.6 | **Sidebar navigation** | Check sidebar as different roles | Links match user permissions (Detective sees Board, Cadet doesn't, etc.). | ☐ |
| 12.7 | **Global search** | Type in header search bar | Dropdown shows results across cases, suspects, evidence. Click navigates. | ☐ |
| 12.8 | **Error boundary** | Trigger uncaught JS error | Error boundary catches. Fallback UI with error message. | ☐ |
| 12.9 | **Docker Compose** | Run `docker compose up --build` from project root | All 3 services start (db, backend, frontend). Frontend accessible at `localhost:5173`. | ☐ |
| 12.10 | **Tests pass** | Run `npx vitest run` in frontend/ | All 8 test files pass. No failures. | ☐ |

---

## Failure Logging

When a test fails:

| Field | What to Record |
|---|---|
| Scenario # | e.g., 5d.7 |
| Actual Result | What happened instead |
| Screenshot | Path or attachment |
| Console Errors | Browser console output |
| Network | Relevant API request/response (status, body) |
| Severity | Blocker / Major / Minor / Cosmetic |
| Notes | Suspected root cause or workaround |

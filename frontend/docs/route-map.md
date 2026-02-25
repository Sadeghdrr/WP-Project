# Frontend Route Map

> Generated: Step 03 — Domain Model & Route Map  
> Branch: `agent/step-03-domain-model-and-routes`  
> Source: `project-doc.md` §5 (Required Pages), §7 (CP2 Scoring)

---

## Overview

9 top-level pages scored in CP2 (total 3 000 pts of UI/UX).  
Routes are permission-aware: each row lists which roles may access it.  
"Auth" column: `public` = no token needed, `any` = any authenticated user, or a list of minimum roles/permissions.

---

## Route Table

| # | Path | Page Name | CP2 Pts | Auth | Lazy | Doc §  |
|---|------|-----------|---------|------|------|--------|
| 1 | `/` | Home | 200 | public | no | §5.1 |
| 2 | `/login` | Login | 200 | public (redirect if authed) | yes | §5.2 |
| 3 | `/register` | Register | 200 | public (redirect if authed) | yes | §5.2 |
| 4 | `/dashboard` | Dashboard | 800 | any | no | §5.3 |
| 5 | `/detective-board/:caseId` | Detective Board | 800 | Detective+ | yes | §5.4 |
| 6 | `/most-wanted` | Most Wanted | 300 | any (Base User+) | yes | §5.5 |
| 7 | `/cases` | Case List | 200 | any | yes | §5.6 |
| 8 | `/cases/new/complaint` | New Complaint | — | Complainant+ | yes | §4.2.1 |
| 9 | `/cases/new/crime-scene` | Crime Scene Report | — | Police Officer+ | yes | §4.2.2 |
| 10 | `/cases/:caseId` | Case Detail | — | role-based | yes | §5.6 |
| 11 | `/cases/:caseId/evidence` | Case Evidence | 200 | role-based | yes | §5.8 |
| 12 | `/cases/:caseId/evidence/new` | Add Evidence | — | Detective+ | yes | §4.3 |
| 13 | `/cases/:caseId/suspects` | Case Suspects | — | Detective+ | yes | §4.4, §4.5 |
| 14 | `/cases/:caseId/suspects/:suspectId` | Suspect Detail | — | Detective+ | yes | §4.5 |
| 15 | `/cases/:caseId/interrogations` | Interrogations | — | Sergeant+, Detective | yes | §4.5 |
| 16 | `/cases/:caseId/trial` | Trial | — | Judge | yes | §4.6 |
| 17 | `/reports` | General Reporting | 300 | Judge, Captain, Police Chief | yes | §5.7 |
| 18 | `/admin` | Admin Panel | 200 | System Admin | yes | §7 |
| 19 | `/admin/users` | User Management | — | System Admin | yes | §7 |
| 20 | `/admin/roles` | Role Management | — | System Admin | yes | §7 |
| 21 | `/bounty-tips` | Bounty Tips | — | any | yes | §4.8 |
| 22 | `/bounty-tips/new` | Submit Tip | — | any | yes | §4.8 |
| 23 | `/bounty-tips/verify` | Verify Reward Code | — | Police Officer+ | yes | §4.8 |
| 24 | `/profile` | My Profile | — | any | yes | — |
| 25 | `/notifications` | Notifications | — | any | yes | — |
| 26 | `*` | 404 Not Found | — | public | yes | — |

---

## Route Grouping

### Public (no auth)
- `/` — Home page with system intro + stats (solved cases, employees, active cases)
- `/login` — Login form (identifier + password)
- `/register` — Registration form (username, email, phone, national_id, password, first/last name)

### Authenticated (any role)
- `/dashboard` — Modular dashboard; modules shown per role's permissions
- `/profile` — View/edit own profile
- `/notifications` — List of user notifications (mark read)
- `/most-wanted` — Most-wanted list with photos + bounty amounts

### Case Management
- `/cases` — Filterable case list (user sees cases per their access)
- `/cases/new/complaint` — Complainant: file a new complaint
- `/cases/new/crime-scene` — Officer+: register a crime scene
- `/cases/:caseId` — Case detail hub (status, complainants, witnesses, status log)
- `/cases/:caseId/evidence` — Evidence list for a case
- `/cases/:caseId/evidence/new` — Add evidence (5 subtypes: testimony, biological, vehicle, identity, other)
- `/cases/:caseId/suspects` — Suspect list for the case
- `/cases/:caseId/suspects/:suspectId` — Suspect detail + warrant info
- `/cases/:caseId/interrogations` — Interrogation records + guilt scores
- `/cases/:caseId/trial` — Trial record, verdict, punishment

### Detective Board
- `/detective-board/:caseId` — Canvas with drag-drop items, red-line connections, export-to-image

### Reporting
- `/reports` — Full case reports for Judge, Captain, Police Chief (all case data, evidence, suspects, personnel)

### Bounty System
- `/bounty-tips` — List tips submitted by current user
- `/bounty-tips/new` — Submit new tip for a case/suspect
- `/bounty-tips/verify` — Police officer verifies bounty claim via national_id + unique_code

### Admin Panel
- `/admin` — Admin dashboard (non-Django, custom React admin)
- `/admin/users` — CRUD users, assign roles
- `/admin/roles` — CRUD roles, assign permissions

---

## Dashboard Modules by Role

The `/dashboard` page renders a different set of modules based on the user's role.
Each module is a card/widget that links to the relevant section.

| Module | Visible To | Links To |
|--------|-----------|----------|
| My Complaints | Complainant | `/cases` (filtered) |
| Complaint Review | Cadet | `/cases` (status=COMPLAINT_REGISTERED) |
| Case Review | Police Officer+ | `/cases` (status=OFFICER_REVIEW) |
| Active Cases | Detective, Sergeant | `/cases` (status=INVESTIGATION+) |
| Detective Board | Detective | `/detective-board/:caseId` |
| Arrest & Interrogation | Sergeant, Detective | `/cases/:id/interrogations` |
| Captain Verdict | Captain | `/cases` (status=CAPTAIN_REVIEW) |
| Chief Approval | Police Chief | `/cases` (status=CHIEF_REVIEW) |
| Trial Queue | Judge | `/cases` (status=JUDICIARY) |
| Evidence Verification | Coroner | `/cases/:id/evidence` (biological, unverified) |
| Reports | Judge, Captain, Police Chief | `/reports` |
| User Management | System Admin | `/admin/users` |
| Role Management | System Admin | `/admin/roles` |
| Notifications | All | `/notifications` |
| Bounty Tips Review | Police Officer | `/bounty-tips` |
| Bounty Tips Verify | Detective | `/bounty-tips` |
| Most Wanted | All | `/most-wanted` |

---

## Guard Strategy

Routes will be protected by a `<ProtectedRoute>` wrapper component that:

1. Checks if a valid JWT access token exists (redirect to `/login` if not)
2. Reads the `role`, `hierarchy_level`, and `permissions_list` claims from the token
3. Compares against the route's `requiredPermissions` or `minHierarchy` config
4. Shows a 403 Forbidden page if the user lacks access

Public routes (`/`, `/login`, `/register`) skip the guard entirely.
Authenticated-but-public routes (`/most-wanted`) require a token but accept any role (Base User hierarchy_level ≥ 0).

---

## API Prefix Note

All API calls use the base path `/api/`.  
**Known bug**: Suspects-app endpoints are double-prefixed as `/api/suspects/suspects/...` (see Step 02 mismatch notes). The route map assumes the frontend will use the actual backend URLs as-is until the backend is fixed.

---

## Navigation Structure

```
TopNav (persistent)
├── Logo / Home link → /
├── Dashboard → /dashboard (if authed)
├── Cases → /cases (if authed)
├── Most Wanted → /most-wanted (if authed)
├── Reports → /reports (if Judge/Captain/Chief)
├── Admin → /admin (if System Admin)
├── Notifications bell icon → /notifications (if authed)
└── Profile / Login → /profile or /login

Sidebar (inside /dashboard, /cases, /admin)
├── Context-specific sub-navigation
└── Breadcrumbs for nested routes
```

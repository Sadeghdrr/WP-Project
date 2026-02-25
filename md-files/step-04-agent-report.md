# Step 04 Agent Report — RBAC Strategy & Permission Matrix

> **Branch:** `agent/step-04-rbac-strategy`  
> **Based on:** `master` (latest)  
> **Depends on:** Step 01 (requirements), Step 02 (API contract), Step 03 (domain model & routes)

---

## 1. Files Created / Changed

| File | Action | Purpose |
|------|--------|---------|
| `frontend/docs/permission-matrix.md` | Created | Maps all frontend pages/actions to backend permission strings, grouped by module |
| `frontend/docs/rbac-strategy.md` | Created | Defines permission-driven RBAC approach, guard types, fallback UX, bootstrap flow |
| `frontend/src/auth/permissions.ts` | Created | 89 permission string constants mirroring `core/permissions_constants.py` in `"app_label.codename"` format |
| `frontend/src/auth/can.ts` | Created | Pure utility functions: `can()`, `canAll()`, `canAny()`, `hasMinHierarchy()`, `checkAccess()`, `buildPermissionSet()` |
| `frontend/src/auth/index.ts` | Created | Barrel export for auth module |
| `md-files/step-04-agent-report.md` | Created | This report |

**Total:** 6 new files (2 docs + 3 TypeScript + 1 report). Zero backend files modified.

---

## 2. RBAC Approach Summary

### Core Principle: Permission-Driven, Not Role-Name-Driven

The frontend NEVER checks `if (role === "Detective")`. Instead, every guard checks permission strings from the user's `permissions_list`. This satisfies the project-doc §2.2 requirement that roles must be modifiable without code changes.

### Permission Data Flow

```
Login → JWT access token claims → { role, hierarchy_level, permissions_list }
                                        ↓
                              React AuthContext (Set<string> for O(1) lookups)
                                        ↓
     Page reload → GET /api/accounts/me/ → rehydrate from fresh DB state
```

### Three Guard Types

1. **Route Guard (`<ProtectedRoute>`)** — wraps route components; redirects to `/login` if unauthenticated, shows 403 page if unauthorized
2. **Component Guard (`<Can>`)** — conditionally renders UI fragments (dashboard modules, nav items)
3. **Action Guard (`can()` function)** — enables/disables buttons and form actions imperatively

### Fallback UX

- Unauthorized routes → 403 page (not redirect)
- Unauthorized actions → disabled buttons with tooltip
- Unauthorized modules → hidden entirely
- Backend 403 → toast error (no redirect)

---

## 3. Permission-Sensitive Frontend Areas Identified

### From project-doc requirements (§2-§5):

| Area | §Ref | Permission-Sensitive? | Guard Type |
|------|------|-----------------------|------------|
| Home page stats | §5.1 | Yes (auth-only; backend requires IsAuthenticated) | Component |
| Login / Register | §5.2 | No (public) | — |
| Modular Dashboard | §5.3 | Yes (module visibility per role's permissions) | Component |
| Detective Board | §5.4 | Yes (Detective+ only) | Route + Action |
| Most Wanted | §5.5 | Yes (auth-only) | Route |
| Case & Complaint Status | §5.6 | Yes (view/edit per access level) | Route + Action |
| General Reporting | §5.7 | Yes (Judge, Captain, Police Chief) | Route |
| Evidence Registration | §5.8 | Yes (evidence CRUD + coroner verification) | Route + Action |
| Admin Panel | §7 CP2 | Yes (System Admin only) | Route + Action |

### From backend permission constants:

- **89 unique permission strings** across 6 Django apps (accounts, cases, evidence, suspects, board, core)
- **18 custom workflow permissions** (e.g., `can_review_complaint`, `can_judge_trial`)
- **71 standard CRUD permissions** (view/add/change/delete for each model)
- All are used in the permission matrix

---

## 4. Backend Anomalies / Problems Affecting RBAC

### 4.1 No `DEFAULT_PERMISSION_CLASSES` in DRF Settings

**Problem:** `REST_FRAMEWORK` config has no `DEFAULT_PERMISSION_CLASSES`. DRF defaults to `AllowAny`. Each view explicitly sets `[IsAuthenticated]`, but any future view added without it would be unprotected.

**Frontend impact:** None — frontend always sends JWT for authenticated requests. Documented as a backend risk.

### 4.2 All Authorization in Service Layer, Not DRF Permission Classes

**Problem:** Zero custom DRF permission classes exist. All fine-grained checks (role, hierarchy, ownership) are enforced inside service methods. This means:
- Every endpoint returns `IsAuthenticated` / `AllowAny` at the DRF level
- 403 errors from business logic come as custom exceptions, not DRF `PermissionDenied`
- Error response format may differ from DRF's standard `{"detail": "..."}`

**Frontend impact:** Error handler must handle both standard DRF error shapes and custom exception shapes. The permission matrix represents *frontend-side best-effort guards* — the backend service layer is always the final authority.

### 4.3 Some Backend Services Check Role Name Directly

**Problem:** `UserManagementService.assign_role()` checks `performed_by.role.name == "System Admin"`. This is a hardcoded role-name check that contradicts the permission-driven philosophy.

**Frontend impact:** The frontend uses `accounts.change_user` permission for UI guards. If backend rejects due to role-name mismatch, show the 403 error as-is. Do NOT add role-name checks to the frontend.

### 4.4 Home Page Stats Endpoint Requires Auth

**Problem:** `DashboardStatsView` requires `IsAuthenticated`, but §5.1 describes the home page as a general intro page showing statistics to visitors.

**Frontend impact:** Show home page publicly with static intro. Stats section requires auth; show "login to view live statistics" for unauthenticated visitors.

### 4.5 JWT Token Staleness Window

**Problem:** JWT `permissions_list` becomes stale if admin changes user's role mid-session. Access token lifetime is 30 minutes.

**Frontend impact:** Rehydrate from `/me` on each page reload. Accept that stale permissions may allow a forbidden action in the UI temporarily — the backend will reject with 403 and the frontend handles it gracefully.

### 4.6 Suspects URL Double-Prefix (Carries from Step 02)

**Problem:** Suspects endpoints are at `/api/suspects/suspects/...` due to a URL config bug.

**Frontend impact:** No RBAC impact, but API calls must use the doubled prefix.

---

## 5. Coverage Verification (Post-Check)

### Covered ✅

| Requirement | Permission Matrix Entry | Guard Strategy |
|-------------|------------------------|----------------|
| §4.1 Registration & Login | Public; no permission needed | — |
| §4.2 Case creation (complaint) | `cases.add_case` | Route + Action |
| §4.2 Case creation (crime scene) | `cases.add_case` + hierarchy ≥ 5 | Route + Action |
| §4.2 Cadet review of complaints | `cases.can_review_complaint` | Action |
| §4.2 Officer approval of cases | `cases.can_approve_case` | Action |
| §4.2 Complainant management | `cases.*_casecomplainant` | Action |
| §4.3 Evidence registration (5 types) | `evidence.add_*evidence` | Route + Action |
| §4.3 Evidence file upload | `evidence.add_evidencefile` | Action |
| §4.3 Coroner verification | `evidence.can_verify_evidence` | Action |
| §4.3 Forensic result | `evidence.can_register_forensic_result` | Action |
| §4.4 Detective board | `board.*_detectiveboard/boarditem/boardconnection/boardnote` | Route + Action |
| §4.4 Board export | `board.can_export_board` | Action |
| §4.5 Suspect identification | `suspects.can_identify_suspect` | Action |
| §4.5 Sergeant approval | `suspects.can_approve_suspect` | Action |
| §4.5 Arrest warrant | `suspects.can_issue_arrest_warrant` | Action |
| §4.5 Interrogation | `suspects.can_conduct_interrogation` + `can_score_guilt` | Action |
| §4.5 Captain verdict | `suspects.can_render_verdict` | Action |
| §4.5 Chief approval (critical) | `cases.can_approve_critical_case` | Action |
| §4.6 Trial / Judge verdict | `suspects.can_judge_trial` | Route + Action |
| §4.7 Most Wanted page | `auth-only` | Route |
| §4.8 Bounty tip submission | `suspects.add_bountytip` | Action |
| §4.8 Bounty tip officer review | `suspects.can_review_bounty_tip` | Action |
| §4.8 Bounty tip detective verify | `suspects.can_verify_bounty_tip` | Action |
| §4.9 Bail management | `suspects.can_set_bail_amount` + `suspects.add_bail` | Action |
| §5.1 Home page | Public (stats auth-gated) | Component |
| §5.2 Login/Register | Public | — |
| §5.3 Modular Dashboard (17 modules) | Per-module permission checks | Component |
| §5.4 Detective Board | Board permissions | Route |
| §5.5 Most Wanted | `auth-only` | Route |
| §5.6 Case Status | Case permissions | Route + Action |
| §5.7 General Reporting | `cases.view_case` + hierarchy ≥ 2 | Route |
| §5.8 Evidence page | Evidence permissions | Route + Action |
| §7 Admin Panel | `accounts.view_user` + `accounts.view_role` | Route + Action |
| §7 User management | `accounts.*_user` | Action |
| §7 Role management | `accounts.*_role` | Action |
| Notifications | `auth-only` | Route |
| Profile | `auth-only` | Route |

### Ambiguous / Needs Clarification ⚠️

| Item | Issue |
|------|-------|
| Home page stats visibility | Doc implies public; backend requires auth. Resolved: show stats only if authenticated |
| Most Wanted "all users" | Could mean public or all authenticated. Resolved: auth-only (matches backend) |
| General Reporting access | §5.7 says "primarily for Judge, Captain, Police Chief" — no dedicated backend permission. Resolved: hierarchy ≥ 2 (Judge level) + `cases.view_case` |
| Crime-scene case creation | §4.2.2 says "police rank other than Cadet" — no dedicated permission. Resolved: hierarchy ≥ 5 (Police Officer) + `cases.add_case` |

### Not Applicable / Public

| Item | Reason |
|------|--------|
| Home page intro text | Static content, no auth |
| System constants endpoint | `AllowAny` — no guard needed |
| Login page | Public by definition |
| Register page | Public by definition |
| 404 page | No auth needed |

---

## 6. Confirmation

- [x] `frontend/docs/permission-matrix.md` — 89 permission strings mapped across 11 sections
- [x] `frontend/docs/rbac-strategy.md` — permission-driven approach, 3 guard types, fallback UX, bootstrap flow
- [x] `frontend/src/auth/permissions.ts` — 89 constants in `P.CASES.VIEW_CASE` format
- [x] `frontend/src/auth/can.ts` — 6 utility functions, all pure TypeScript, zero React dependency
- [x] `frontend/src/auth/index.ts` — barrel export
- [x] TypeScript compiles cleanly (`tsc --noEmit` exit 0, strict mode)
- [x] All 9 CP2 pages covered in permission matrix
- [x] All 9 project-doc flows have permission mappings
- [x] 6 backend anomalies documented (report only — no backend changes)
- [x] Zero backend files modified

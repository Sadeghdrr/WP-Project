# Frontend Permission Matrix

> Generated: Step 04 — RBAC Strategy  
> Branch: `agent/step-04-rbac-strategy`  
> Source: backend service-layer auth checks, `core/permissions_constants.py`, `project-doc.md` §2-§5

---

## How to Read This Matrix

- **Permission strings** use the backend's `"app_label.codename"` format (e.g. `cases.view_case`)
- **`auth-only`** = any authenticated user (no specific permission needed; backend accepts any valid JWT)
- **`public`** = no authentication required
- **`hierarchy ≥ N`** = user's `hierarchy_level` from JWT must be ≥ N (service-layer enforced)
- **`service-layer`** = the backend service checks role name / hierarchy at runtime; frontend should use the indicated permission as a best-effort UI guard, but the backend is the final authority
- **View** = seeing the page/data; **Action** = performing a mutation (create, update, delete, status change)

---

## 1. Public Pages

| Page / Area | Type | Guard | Permission | Notes |
|-------------|------|-------|------------|-------|
| Home page (`/`) | view | `public` | — | Stats from `core.DashboardStatsView` could be public or auth-only depending on backend; currently `IsAuthenticated` |
| Login (`/login`) | action | `public` | — | |
| Register (`/register`) | action | `public` | — | |
| System constants | view | `public` | — | `SystemConstantsView` uses `AllowAny` |

---

## 2. Dashboard Module (§5.3 — 800 pts)

Dashboard is modular: each card/widget shown only if user has the relevant permissions.

| Module | Type | Permission(s) | Applicable Roles (doc) |
|--------|------|---------------|------------------------|
| My Complaints | view | `auth-only` | Complainant |
| Complaint Review queue | view | `cases.can_review_complaint` | Cadet |
| Case Review queue | view | `cases.can_approve_case` | Police Officer+ |
| Active Investigations | view | `cases.view_case` | Detective, Sergeant |
| Detective Board link | view | `board.view_detectiveboard` | Detective |
| Arrest & Interrogation | view | `suspects.can_conduct_interrogation` | Sergeant, Detective |
| Captain Verdict queue | view | `suspects.can_render_verdict` | Captain |
| Chief Approval queue | view | `cases.can_approve_critical_case` | Police Chief |
| Trial queue | view | `suspects.can_judge_trial` | Judge |
| Evidence Verification | view | `evidence.can_verify_evidence` | Coroner |
| Reports link | view | `cases.view_case` + hierarchy ≥ 2 | Judge, Captain, Chief |
| Bounty Tips Review | view | `suspects.can_review_bounty_tip` | Police Officer |
| Bounty Tips Verify | view | `suspects.can_verify_bounty_tip` | Detective |
| User Management | view | `accounts.view_user` | System Admin |
| Role Management | view | `accounts.view_role` | System Admin |
| Notifications | view | `auth-only` | All |
| Most Wanted link | view | `auth-only` | All |

---

## 3. Cases Module (§5.6 — 200 pts)

### 3.1 Case List & Detail

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View case list | view | `cases.view_case` | Backend filters by role in service layer |
| View case detail | view | `cases.view_case` | |
| Create case (complaint) | action | `cases.add_case` | Complainant creates; creation_type=`complaint` |
| Create case (crime scene) | action | `cases.add_case` + hierarchy ≥ 5 | Police Officer+ only (not Cadet); creation_type=`crime_scene` |
| Edit case | action | `cases.change_case` | |
| Delete case | action | `cases.delete_case` | |

### 3.2 Case Status Transitions

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| Review complaint (Cadet) | action | `cases.can_review_complaint` | Cadet approves/returns to complainant |
| Approve case (Officer) | action | `cases.can_approve_case` | Officer approves/returns to Cadet |
| Assign detective | action | `cases.can_assign_detective` | |
| Change case status | action | `cases.can_change_case_status` | Generic status transition |
| Forward to judiciary | action | `cases.can_forward_to_judiciary` | Captain forwards |
| Approve critical case | action | `cases.can_approve_critical_case` | Police Chief for critical crimes |

### 3.3 Complainants & Witnesses

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View complainants | view | `cases.view_casecomplainant` | |
| Add complainant | action | `cases.add_casecomplainant` | |
| Approve/reject complainant | action | `cases.change_casecomplainant` | Cadet reviews |
| View witnesses | view | `cases.view_casewitness` | |
| Add witness | action | `cases.add_casewitness` | |

### 3.4 Case Status Log

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View status log | view | `cases.view_casestatuslog` | Read-only audit trail |

---

## 4. Evidence Module (§5.8 — 200 pts)

### 4.1 Evidence CRUD

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View evidence list | view | `evidence.view_evidence` | |
| View evidence detail | view | `evidence.view_evidence` | |
| Add testimony evidence | action | `evidence.add_testimonyevidence` | |
| Add biological evidence | action | `evidence.add_biologicalevidence` | |
| Add vehicle evidence | action | `evidence.add_vehicleevidence` | |
| Add identity evidence | action | `evidence.add_identityevidence` | |
| Add other evidence | action | `evidence.add_evidence` | Fallback for "other" type |
| Edit evidence | action | `evidence.change_evidence` | |
| Delete evidence | action | `evidence.delete_evidence` | |

### 4.2 Evidence Verification (Coroner)

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| Verify biological evidence | action | `evidence.can_verify_evidence` | Coroner verifies |
| Register forensic result | action | `evidence.can_register_forensic_result` | Coroner fills forensic_result |

### 4.3 Evidence Files

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View files | view | `evidence.view_evidencefile` | |
| Upload file | action | `evidence.add_evidencefile` | |
| Delete file | action | `evidence.delete_evidencefile` | |

---

## 5. Suspects Module

### 5.1 Suspect CRUD

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View suspects | view | `suspects.view_suspect` | |
| Identify suspect | action | `suspects.can_identify_suspect` | Detective identifies |
| Approve suspect (Sergeant) | action | `suspects.can_approve_suspect` | Sergeant approves/rejects |
| Edit suspect | action | `suspects.change_suspect` | |
| Delete suspect | action | `suspects.delete_suspect` | |

### 5.2 Warrants

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| Issue arrest warrant | action | `suspects.can_issue_arrest_warrant` | Sergeant issues |

### 5.3 Interrogation

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View interrogations | view | `suspects.view_interrogation` | |
| Conduct interrogation | action | `suspects.can_conduct_interrogation` | Sergeant + Detective |
| Score guilt | action | `suspects.can_score_guilt` | 1-10 scale |

### 5.4 Trial

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View trials | view | `suspects.view_trial` | |
| Render verdict | action | `suspects.can_render_verdict` | Captain's verdict |
| Judge trial | action | `suspects.can_judge_trial` | Judge's final verdict |

### 5.5 Bounty Tips

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View bounty tips | view | `suspects.view_bountytip` | |
| Submit bounty tip | action | `suspects.add_bountytip` | Any user can submit |
| Review bounty tip (Officer) | action | `suspects.can_review_bounty_tip` | Initial review |
| Verify bounty tip (Detective) | action | `suspects.can_verify_bounty_tip` | Final verification |

### 5.6 Bail

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View bails | view | `suspects.view_bail` | |
| Set bail amount | action | `suspects.can_set_bail_amount` | Sergeant sets amount |
| Create bail | action | `suspects.add_bail` | |

---

## 6. Detective Board (§5.4 — 800 pts)

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View board | view | `board.view_detectiveboard` | |
| Create board | action | `board.add_detectiveboard` | |
| Add board item | action | `board.add_boarditem` | Drag-drop placement |
| Move board item | action | `board.change_boarditem` | Position update |
| Remove board item | action | `board.delete_boarditem` | |
| Add note | action | `board.add_boardnote` | |
| Edit note | action | `board.change_boardnote` | |
| Delete note | action | `board.delete_boardnote` | |
| Add connection | action | `board.add_boardconnection` | Red line between items |
| Remove connection | action | `board.delete_boardconnection` | |
| Export board as image | action | `board.can_export_board` | Client-side export |
| Edit board | action | `board.change_detectiveboard` | |

---

## 7. Most Wanted (§5.5 — 300 pts)

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View most wanted list | view | `auth-only` | Doc says "visible to all users"; backend requires auth |

---

## 8. General Reporting (§5.7 — 300 pts)

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View full case reports | view | `cases.view_case` + hierarchy ≥ 2 | Judge, Captain, Police Chief per §5.7 |

> **Note**: Backend doesn't have a dedicated report permission. The frontend should gate this route by hierarchy level (≥ Judge = 2) and `cases.view_case`. The backend service layer may enforce additional checks.

---

## 9. Admin Panel (§7 CP2 — 200 pts)

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View admin panel | view | `accounts.view_user` + `accounts.view_role` | System Admin |
| List users | view | `accounts.view_user` | |
| View user detail | view | `accounts.view_user` | |
| Assign role to user | action | `accounts.change_user` | `service-layer`: hierarchy check |
| Activate user | action | `accounts.change_user` | `service-layer`: hierarchy check |
| Deactivate user | action | `accounts.change_user` | `service-layer`: hierarchy check |
| List roles | view | `accounts.view_role` | |
| Create role | action | `accounts.add_role` | |
| Edit role | action | `accounts.change_role` | |
| Delete role | action | `accounts.delete_role` | Blocked if users assigned |
| Assign permissions to role | action | `accounts.change_role` | |
| View all permissions | view | `auth-only` | `PermissionListView` needs only auth |

---

## 10. Notifications

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View notifications | view | `auth-only` | Backend filters by `recipient=request.user` |
| Mark as read | action | `auth-only` | |

---

## 11. Profile

| Action | Type | Permission(s) | Notes |
|--------|------|---------------|-------|
| View own profile | view | `auth-only` | `GET /api/accounts/me/` |
| Edit own profile | action | `auth-only` | `PATCH /api/accounts/me/` (email, phone, name) |

---

## Permission String Reference

All unique permission strings used in this matrix (74 total):

### Accounts (8)
`accounts.view_user`, `accounts.add_user`, `accounts.change_user`, `accounts.delete_user`, `accounts.view_role`, `accounts.add_role`, `accounts.change_role`, `accounts.delete_role`

### Cases (22)
`cases.view_case`, `cases.add_case`, `cases.change_case`, `cases.delete_case`, `cases.view_casecomplainant`, `cases.add_casecomplainant`, `cases.change_casecomplainant`, `cases.delete_casecomplainant`, `cases.view_casewitness`, `cases.add_casewitness`, `cases.change_casewitness`, `cases.delete_casewitness`, `cases.view_casestatuslog`, `cases.add_casestatuslog`, `cases.change_casestatuslog`, `cases.delete_casestatuslog`, `cases.can_review_complaint`, `cases.can_approve_case`, `cases.can_assign_detective`, `cases.can_change_case_status`, `cases.can_forward_to_judiciary`, `cases.can_approve_critical_case`

### Evidence (22)
`evidence.view_evidence`, `evidence.add_evidence`, `evidence.change_evidence`, `evidence.delete_evidence`, `evidence.view_testimonyevidence`, `evidence.add_testimonyevidence`, `evidence.change_testimonyevidence`, `evidence.delete_testimonyevidence`, `evidence.view_biologicalevidence`, `evidence.add_biologicalevidence`, `evidence.change_biologicalevidence`, `evidence.delete_biologicalevidence`, `evidence.view_vehicleevidence`, `evidence.add_vehicleevidence`, `evidence.change_vehicleevidence`, `evidence.delete_vehicleevidence`, `evidence.view_identityevidence`, `evidence.add_identityevidence`, `evidence.change_identityevidence`, `evidence.delete_identityevidence`, `evidence.view_evidencefile`, `evidence.add_evidencefile`, `evidence.change_evidencefile`, `evidence.delete_evidencefile`, `evidence.can_verify_evidence`, `evidence.can_register_forensic_result`

### Suspects (20)
`suspects.view_suspect`, `suspects.add_suspect`, `suspects.change_suspect`, `suspects.delete_suspect`, `suspects.view_interrogation`, `suspects.add_interrogation`, `suspects.change_interrogation`, `suspects.delete_interrogation`, `suspects.view_trial`, `suspects.add_trial`, `suspects.change_trial`, `suspects.delete_trial`, `suspects.view_bountytip`, `suspects.add_bountytip`, `suspects.change_bountytip`, `suspects.delete_bountytip`, `suspects.view_bail`, `suspects.add_bail`, `suspects.change_bail`, `suspects.delete_bail`, `suspects.can_identify_suspect`, `suspects.can_approve_suspect`, `suspects.can_issue_arrest_warrant`, `suspects.can_conduct_interrogation`, `suspects.can_score_guilt`, `suspects.can_render_verdict`, `suspects.can_judge_trial`, `suspects.can_review_bounty_tip`, `suspects.can_verify_bounty_tip`, `suspects.can_set_bail_amount`

### Board (13)
`board.view_detectiveboard`, `board.add_detectiveboard`, `board.change_detectiveboard`, `board.delete_detectiveboard`, `board.view_boardnote`, `board.add_boardnote`, `board.change_boardnote`, `board.delete_boardnote`, `board.view_boarditem`, `board.add_boarditem`, `board.change_boarditem`, `board.delete_boarditem`, `board.view_boardconnection`, `board.add_boardconnection`, `board.change_boardconnection`, `board.delete_boardconnection`, `board.can_export_board`

### Core (4)
`core.view_notification`, `core.add_notification`, `core.change_notification`, `core.delete_notification`

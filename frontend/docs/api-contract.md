# Frontend API Contract Inventory

> Source: backend source code (runtime truth) cross-referenced with md-files/ docs.
> Generated: 2026-02-25 | Branch: `agent/step-02-api-contract-inventory`
>
> **Auth mechanism:** JWT via SimpleJWT. Login returns `access` + `refresh` tokens.
> JWT access tokens carry custom claims: `role`, `hierarchy_level`, `permissions_list`.
> All endpoints except those marked **Public** require `Authorization: Bearer <access_token>`.

---

## Table of Contents

1. [Authentication & User Profile](#1-authentication--user-profile)
2. [Admin Panel — User & Role Management](#2-admin-panel--user--role-management)
3. [Home Page — Dashboard & Statistics](#3-home-page--dashboard--statistics)
4. [Case & Complaint Management](#4-case--complaint-management)
5. [Evidence Registration & Review](#5-evidence-registration--review)
6. [Detective Board](#6-detective-board)
7. [Suspects & Most Wanted](#7-suspects--most-wanted)
8. [Interrogation, Trial & Verdict](#8-interrogation-trial--verdict)
9. [Bounty Tips](#9-bounty-tips)
10. [Bail & Payment (Optional)](#10-bail--payment-optional)
11. [Notifications](#11-notifications)
12. [System Constants & Global Search](#12-system-constants--global-search)

---

## 1. Authentication & User Profile

### Login / Registration Page

| Endpoint | Purpose | Auth | Request | Response | Errors |
|---|---|---|---|---|---|
| `POST /api/accounts/auth/register/` | Register new user (Base User role) | **Public** | `{ username, password, password_confirm, email, phone_number, first_name, last_name, national_id }` | `201` → `{ id, username, email, national_id, phone_number, first_name, last_name, is_active, date_joined, role, role_detail: {id,name,description,hierarchy_level}, permissions: [str] }` | `400` validation (duplicate fields, password mismatch, national_id not 10 digits, phone format) |
| `POST /api/accounts/auth/login/` | Login (multi-field: username/email/phone/national_id + password) | **Public** | `{ identifier, password }` | `200` → `{ access, refresh, user: UserDetail }` | `400` invalid credentials or disabled account |
| `POST /api/accounts/auth/token/refresh/` | Refresh expired access token | **Public** | `{ refresh }` | `200` → `{ access }` | `401` invalid/expired refresh token |

### Current User ("Me")

| Endpoint | Purpose | Auth | Request | Response | Errors |
|---|---|---|---|---|---|
| `GET /api/accounts/me/` | Get own profile + role + permissions | Auth | — | `200` → `UserDetail` (see register response shape) | `401` |
| `PATCH /api/accounts/me/` | Update own profile (limited fields) | Auth | `{ email?, phone_number?, first_name?, last_name? }` | `200` → `UserDetail` | `400` validation |

**Validation notes:**
- `national_id`: exactly 10 digits
- `phone_number`: Iranian mobile format `^(\+98|0)?9\d{9}$`
- `password`: min 8 characters
- All of username, email, phone_number, national_id must be unique

---

## 2. Admin Panel — User & Role Management

### User Management

| Endpoint | Purpose | Auth | Request | Response | Errors |
|---|---|---|---|---|---|
| `GET /api/accounts/users/` | List all users (filterable) | Auth (Admin) | Query: `role`, `hierarchy_level`, `is_active`, `search` | `200` → `[{ id, username, email, national_id, phone_number, first_name, last_name, is_active, role, role_name, hierarchy_level }]` | `401` |
| `GET /api/accounts/users/{id}/` | Get user detail | Auth (Admin) | — | `200` → `UserDetail` | `404` |
| `PATCH /api/accounts/users/{id}/assign-role/` | Assign role to user | Auth (Admin) | `{ role_id }` | `200` → `UserDetail` | `400`, `403`, `404` |
| `PATCH /api/accounts/users/{id}/activate/` | Activate user | Auth (Admin) | — | `200` → `UserDetail` | `403`, `404` |
| `PATCH /api/accounts/users/{id}/deactivate/` | Deactivate user | Auth (Admin) | — | `200` → `UserDetail` | `403`, `404` |

### Role Management

| Endpoint | Purpose | Auth | Request | Response | Errors |
|---|---|---|---|---|---|
| `GET /api/accounts/roles/` | List all roles | Auth | — | `200` → `[{ id, name, description, hierarchy_level }]` | `401` |
| `POST /api/accounts/roles/` | Create role | Auth (Admin) | `{ name, description, hierarchy_level, permissions: [int] }` | `201` → `RoleDetail` with `permissions_display` | `400` |
| `GET /api/accounts/roles/{id}/` | Get role detail | Auth | — | `200` → `RoleDetail` | `404` |
| `PUT /api/accounts/roles/{id}/` | Full update role | Auth (Admin) | `{ name, description, hierarchy_level, permissions }` | `200` → `RoleDetail` | `400` |
| `PATCH /api/accounts/roles/{id}/` | Partial update role | Auth (Admin) | partial fields | `200` → `RoleDetail` | `400` |
| `DELETE /api/accounts/roles/{id}/` | Delete role | Auth (Admin) | — | `204` | `400` users still assigned |
| `POST /api/accounts/roles/{id}/assign-permissions/` | Replace role's permission set | Auth (Admin) | `{ permission_ids: [int] }` | `200` → `RoleDetail` | `400` |

### Permission Listing

| Endpoint | Purpose | Auth | Request | Response | Errors |
|---|---|---|---|---|---|
| `GET /api/accounts/permissions/` | List all Django permissions (for picker UI) | Auth | — | `200` → `[{ id, name, codename, full_codename }]` | `401` |

---

## 3. Home Page — Dashboard & Statistics

| Endpoint | Purpose | Auth | Request | Response | Errors |
|---|---|---|---|---|---|
| `GET /api/core/dashboard/` | Aggregated dashboard statistics | Auth | — | `200` → see below | `401` |

**Dashboard response shape:**
```
{
  total_cases, active_cases, closed_cases, voided_cases,
  total_suspects, total_evidence, total_employees,
  unassigned_evidence_count,
  cases_by_status: [{ status, label, count }],
  cases_by_crime_level: [{ crime_level, label, count }],
  top_wanted_suspects: [{ id, full_name, national_id, photo_url,
                          most_wanted_score, reward_amount, days_wanted,
                          case_id, case_title }],
  recent_activity: [{ timestamp, type, description, actor }]
}
```

**Frontend usage:** Home page needs at least 3 statistics (§5.1). Use `total_cases` (closed), `total_employees`, `active_cases` from this endpoint. Dashboard page uses full response for role-specific module summaries.

---

## 4. Case & Complaint Management

### Case CRUD

| Endpoint | Purpose | Auth | Request | Response | Errors |
|---|---|---|---|---|---|
| `GET /api/cases/` | List cases (filtered by role visibility) | Auth | Query: `status`, `crime_level`, `detective`, `creation_type`, `created_after`, `created_before`, `search` | `200` → `[CaseList]` | `401` |
| `POST /api/cases/` | Create case (complaint or crime-scene) | Auth | See create payloads below | `201` → `CaseDetail` | `400`, `403` |
| `GET /api/cases/{id}/` | Full case detail | Auth | — | `200` → `CaseDetail` | `404` |
| `PATCH /api/cases/{id}/` | Update mutable fields | Auth | `{ title?, description?, incident_date?, location? }` | `200` → `CaseDetail` | `400`, `404` |
| `DELETE /api/cases/{id}/` | Delete case (admin only) | Auth (Admin) | — | `204` | `403`, `404` |

**Create payloads by type:**

Complaint case:
```json
{
  "creation_type": "complaint",
  "title": "...", "description": "...", "crime_level": 1-4,
  "incident_date": "ISO", "location": "..."
}
```

Crime-scene case:
```json
{
  "creation_type": "crime_scene",
  "title": "...", "description": "...", "crime_level": 1-4,
  "incident_date": "ISO", "location": "...",
  "witnesses": [{ "full_name": "...", "phone_number": "...", "national_id": "..." }]
}
```

**CaseDetail response shape:**
```
{
  id, title, description, crime_level, crime_level_display,
  status, status_display, creation_type, rejection_count,
  incident_date, location,
  created_by, approved_by, assigned_detective, assigned_sergeant,
  assigned_captain, assigned_judge,
  complainants: [{ id, user, user_display, is_primary, status, reviewed_by }],
  witnesses: [{ id, full_name, phone_number, national_id }],
  status_logs: [{ id, from_status, to_status, changed_by, changed_by_name, message }],
  calculations: { crime_level_degree, days_since_creation, tracking_threshold, reward_rials },
  created_at, updated_at
}
```

**CaseStatus progression:**
```
complaint_registered → cadet_review → officer_review → open
                                    → returned_to_complainant (→ resubmit → cadet_review)
                       cadet_review → returned_to_complainant (3x → voided)
crime_scene → pending_approval → open
open → investigation → suspect_identified → sergeant_review → arrest_ordered
     → interrogation → captain_review → (chief_review for critical) → judiciary → closed
```

### Case Workflow Actions

| Endpoint | Purpose | Auth/Role | Request | Response |
|---|---|---|---|---|
| `POST /api/cases/{id}/submit/` | Complainant submits for review | Complainant | — | `CaseDetail` |
| `POST /api/cases/{id}/resubmit/` | Re-submit returned complaint | Complainant | `{ title?, description?, incident_date?, location? }` | `CaseDetail` |
| `POST /api/cases/{id}/cadet-review/` | Cadet approve/reject | Cadet | `{ decision: "approve"|"reject", message? }` (message required on reject) | `CaseDetail` |
| `POST /api/cases/{id}/officer-review/` | Officer approve/reject | Police Officer | `{ decision: "approve"|"reject", message? }` | `CaseDetail` |
| `POST /api/cases/{id}/approve-crime-scene/` | Approve crime-scene case | Superior rank | — | `CaseDetail` |
| `POST /api/cases/{id}/declare-suspects/` | Detective declares suspects | Detective | — | `CaseDetail` |
| `POST /api/cases/{id}/sergeant-review/` | Sergeant approve/reject suspects | Sergeant | `{ decision: "approve"|"reject", message? }` | `CaseDetail` |
| `POST /api/cases/{id}/forward-judiciary/` | Forward to judiciary | Captain/Chief | — | `CaseDetail` |
| `POST /api/cases/{id}/transition/` | Generic status transition | Role-dependent | `{ target_status, message? }` | `CaseDetail` |

### Case Assignment Actions

| Endpoint | Purpose | Auth/Role | Request | Response |
|---|---|---|---|---|
| `POST /api/cases/{id}/assign-detective/` | Assign detective | Sergeant+ | `{ user_id }` | `CaseDetail` |
| `DELETE /api/cases/{id}/unassign-detective/` | Remove detective | Sergeant+ | — | `CaseDetail` |
| `POST /api/cases/{id}/assign-sergeant/` | Assign sergeant | Captain+ | `{ user_id }` | `CaseDetail` |
| `POST /api/cases/{id}/assign-captain/` | Assign captain | Chief/Admin | `{ user_id }` | `CaseDetail` |
| `POST /api/cases/{id}/assign-judge/` | Assign judge | Captain+ | `{ user_id }` | `CaseDetail` |

### Case Sub-Resources

| Endpoint | Purpose | Auth | Request | Response |
|---|---|---|---|---|
| `GET /api/cases/{id}/complainants/` | List complainants | Auth | — | `[ComplainantDetail]` |
| `POST /api/cases/{id}/complainants/` | Add complainant | Auth | `{ user_id }` | `ComplainantDetail` |
| `POST /api/cases/{id}/complainants/{pk}/review/` | Cadet reviews complainant | Cadet | `{ decision: "approve"|"reject" }` | `ComplainantDetail` |
| `GET /api/cases/{id}/witnesses/` | List witnesses | Auth | — | `[WitnessDetail]` |
| `POST /api/cases/{id}/witnesses/` | Add witness | Auth | `{ full_name, phone_number, national_id }` | `WitnessDetail` |
| `GET /api/cases/{id}/status-log/` | Status audit trail | Auth | — | `[StatusLog]` |
| `GET /api/cases/{id}/calculations/` | Reward/tracking calculations | Auth | — | `{ crime_level_degree, days_since_creation, tracking_threshold, reward_rials }` |

### Case Report (General Reporting Page)

| Endpoint | Purpose | Auth/Role | Request | Response |
|---|---|---|---|---|
| `GET /api/cases/{id}/report/` | Full aggregated case report | Judge, Captain, Police Chief, Admin | — | See below |

**Report response shape:**
```
{
  case: { id, title, description, crime_level, status, creation_type, incident_date, location, ... },
  personnel: [{ id, full_name, role }],
  complainants: [{ id, full_name, is_primary, status }],
  witnesses: [{ id, full_name, phone_number, national_id }],
  evidence: [{ id, type, title, description, registered_by }],
  suspects: [{
    id, full_name, national_id, status,
    interrogations: [{ detective_score, sergeant_score, notes }],
    trials: [{ verdict, punishment_title, punishment_description }]
  }],
  status_history: [{ from_status, to_status, changed_by, message, timestamp }],
  calculations: { crime_level_degree, days_since_creation, tracking_threshold, reward_rials }
}
```

---

## 5. Evidence Registration & Review

### Evidence CRUD

| Endpoint | Purpose | Auth | Request | Response | Errors |
|---|---|---|---|---|---|
| `GET /api/evidence/` | List evidence (filtered) | Auth | Query: `evidence_type`, `case`, `registered_by`, `is_verified` (bio only), `search`, `created_after`, `created_before` | `200` → `[EvidenceList]` | `400` invalid filters |
| `POST /api/evidence/` | Create evidence (polymorphic) | Auth | See type-specific payloads below | `201` → `EvidenceDetail` | `400` |
| `GET /api/evidence/{id}/` | Retrieve evidence detail | Auth | — | `200` → polymorphic `EvidenceDetail` | `404` |
| `PATCH /api/evidence/{id}/` | Update evidence | Auth | Type-specific fields (immutable: `evidence_type`, `registered_by`, `case`) | `200` → `EvidenceDetail` | `400` |
| `DELETE /api/evidence/{id}/` | Delete evidence | Auth | — | `204` | `404` |

**Create payloads by evidence type:**

| Type | Common Fields | Type-Specific Fields |
|---|---|---|
| `testimony` | `evidence_type`, `case`, `title`, `description` | `statement_text` |
| `biological` | same | *(none — forensic fields via verify workflow)* |
| `vehicle` | same | `vehicle_model`\*, `color`\*, `license_plate`, `serial_number` (**plate XOR serial**) |
| `identity` | same | `owner_full_name`\*, `document_details: { key: value, ... }` |
| `other` | same | *(none)* |

**EvidenceDetail response (common fields):**
```
{ id, title, description, evidence_type, evidence_type_display,
  case, registered_by, registered_by_name, created_at, updated_at }
```

**Type-specific extra fields in detail:**
- `testimony`: `+ statement_text, files[]`
- `biological`: `+ forensic_result, is_verified, verified_by, verified_by_name, files[]`
- `vehicle`: `+ vehicle_model, color, license_plate, serial_number, files[]`
- `identity`: `+ owner_full_name, document_details, files[]`
- `other`: `+ files[]`

### Evidence Workflow & File Actions

| Endpoint | Purpose | Auth/Role | Request | Response |
|---|---|---|---|---|
| `POST /api/evidence/{id}/verify/` | Coroner verifies biological evidence | Coroner | `{ decision: "approve"|"reject", forensic_result? (req on approve), notes? (req on reject) }` | `BiologicalEvidenceDetail` |
| `POST /api/evidence/{id}/link-case/` | Associate evidence with case | Auth | `{ case_id }` | `EvidenceDetail` |
| `POST /api/evidence/{id}/unlink-case/` | Remove evidence-case association | Auth | `{ case_id }` | `EvidenceDetail` |
| `GET /api/evidence/{id}/files/` | List attached files | Auth | — | `[{ id, file, file_type, file_type_display, caption, created_at }]` |
| `POST /api/evidence/{id}/files/` | Upload file (multipart/form-data) | Auth | `file`\*, `file_type`\* (image/video/audio/document), `caption?` | File object |
| `GET /api/evidence/{id}/chain-of-custody/` | Evidence audit trail | Auth | — | `[{ id, timestamp, action, performed_by, performer_name, details }]` |

---

## 6. Detective Board

### Board CRUD

| Endpoint | Purpose | Auth | Request | Response | Errors |
|---|---|---|---|---|---|
| `GET /api/boards/` | List boards for current user | Auth | — | `200` → `[{ id, case, detective, item_count, connection_count, created_at, updated_at }]` | `401` |
| `POST /api/boards/` | Create board for a case (1 board per case) | Auth (Detective) | `{ case }` | `201` → `BoardList` | `400` already exists |
| `GET /api/boards/{id}/` | Get board metadata | Auth | — | `200` → `BoardList` | `404` |
| `PATCH /api/boards/{id}/` | Update board metadata | Auth | `{ case? }` | `200` → `BoardList` | `400` |
| `DELETE /api/boards/{id}/` | Delete board + all items | Auth | — | `204` | `404` |

### Full Board State (key endpoint for Detective Board page)

| Endpoint | Purpose | Auth | Request | Response |
|---|---|---|---|---|
| `GET /api/boards/{id}/full/` | Full board graph in one request | Auth | — | See below |

**Full board state response:**
```
{
  id, case, detective,
  items: [{
    id, board, content_type, object_id,
    content_object_summary: { content_type_id, app_label, model, object_id, display_name, detail_url },
    position_x, position_y
  }],
  connections: [{ id, board, from_item, to_item, label, created_at, updated_at }],
  notes: [{ id, board, title, content, created_by, created_at, updated_at }]
}
```

**Allowed content types for board items:** `cases.case`, `suspects.suspect`, `evidence.evidence`, `evidence.testimonyevidence`, `evidence.biologicalevidence`, `evidence.vehicleevidence`, `evidence.identityevidence`, `board.boardnote`

### Board Items

| Endpoint | Purpose | Auth | Request | Response |
|---|---|---|---|---|
| `POST /api/boards/{board_pk}/items/` | Pin content onto board | Auth | `{ content_object: { content_type_id, object_id }, position_x?, position_y? }` | `BoardItem` |
| `DELETE /api/boards/{board_pk}/items/{id}/` | Remove pin from board | Auth | — | `204` |
| `PATCH /api/boards/{board_pk}/items/batch-coordinates/` | Batch save drag-and-drop positions | Auth | `{ items: [{ id, position_x, position_y }] }` | `[BoardItem]` |

### Board Connections (Red Lines)

| Endpoint | Purpose | Auth | Request | Response |
|---|---|---|---|---|
| `POST /api/boards/{board_pk}/connections/` | Draw connection between items | Auth | `{ from_item, to_item, label? }` (no self-loops) | `Connection` |
| `DELETE /api/boards/{board_pk}/connections/{id}/` | Remove connection | Auth | — | `204` |

### Board Notes

| Endpoint | Purpose | Auth | Request | Response |
|---|---|---|---|---|
| `POST /api/boards/{board_pk}/notes/` | Add sticky note | Auth | `{ title, content? }` | `Note` |
| `GET /api/boards/{board_pk}/notes/{id}/` | Get note | Auth | — | `Note` |
| `PATCH /api/boards/{board_pk}/notes/{id}/` | Update note | Auth | `{ title?, content? }` | `Note` |
| `DELETE /api/boards/{board_pk}/notes/{id}/` | Delete note | Auth | — | `204` |

---

## 7. Suspects & Most Wanted

### Suspect CRUD

> **⚠ URL BUG:** Backend has a double-prefix routing issue. `suspects/urls.py` registers router prefix `suspects` but root `urls.py` mounts at `api/suspects/`, resulting in actual URLs being `/api/suspects/suspects/...` instead of `/api/suspects/...`. See [api-mismatch-notes.md](api-mismatch-notes.md) §4.1 for details. The URLs below show the **intended** paths per the docstrings; the **actual** runtime paths have the doubled prefix.

| Endpoint | Purpose | Auth | Request | Response | Errors |
|---|---|---|---|---|---|
| `GET /api/suspects/suspects/` | List suspects (filtered) | Auth | Query: `status`, `case`, `national_id`, `search`, `most_wanted`, `created_after`, `created_before`, `approval_status` | `200` → `[SuspectList]` | `400` |
| `POST /api/suspects/suspects/` | Identify suspect in a case | Auth (Detective) | `{ case, full_name, national_id?, phone_number?, photo?, address?, description?, user? }` | `201` → `SuspectDetail` | `400`, `403` |
| `GET /api/suspects/suspects/{id}/` | Full suspect detail | Auth | — | `200` → `SuspectDetail` | `404` |
| `PATCH /api/suspects/suspects/{id}/` | Update suspect profile | Auth (Detective) | `{ full_name?, national_id?, phone_number?, photo?, address?, description? }` | `200` → `SuspectDetail` | `400`, `403` |

**SuspectDetail response shape:**
```
{
  id, full_name, national_id, phone_number, photo, address, description,
  status, status_display, case, case_title,
  wanted_since, days_wanted, is_most_wanted, most_wanted_score, reward_amount,
  identified_by, identified_by_name,
  sergeant_approval_status, sergeant_rejection_message,
  approved_by_sergeant,
  interrogations: [...], trials: [...], bails: [...],
  bounty_tip_count,
  created_at, updated_at
}
```

**SuspectStatus values:** `wanted`, `arrested`, `under_interrogation`, `pending_captain_verdict`, `pending_chief_approval`, `under_trial`, `convicted`, `acquitted`, `released`

### Most Wanted (Most Wanted Page)

| Endpoint | Purpose | Auth | Request | Response |
|---|---|---|---|---|
| `GET /api/suspects/suspects/most-wanted/` | Ranked most-wanted list | Auth (any role) | — | `[{ id, full_name, national_id, photo, description, address, status, case, case_title, wanted_since, days_wanted, most_wanted_score, reward_amount, calculated_reward }]` |

**Ranking formula (backend-computed):** `score = max_days_wanted × highest_crime_degree`
**Bounty formula (backend-computed):** `reward = score × 20,000,000 Rials`
**Eligibility:** wanted > 30 days AND linked to at least one open case.

### Suspect Workflow Actions

| Endpoint | Purpose | Auth/Role | Request | Response |
|---|---|---|---|---|
| `POST .../suspects/{id}/approve/` | Sergeant approves/rejects suspect ID | Sergeant | `{ decision: "approve"|"reject", rejection_message? }` | `SuspectDetail` |
| `POST .../suspects/{id}/issue-warrant/` | Issue arrest warrant | Sergeant | `{ warrant_reason, priority?: "normal"|"high"|"critical" }` | `SuspectDetail` |
| `POST .../suspects/{id}/arrest/` | Execute arrest | Sergeant/Captain | `{ arrest_location, arrest_notes?, warrant_override_justification? }` | `SuspectDetail` |
| `POST .../suspects/{id}/transition-status/` | Generic status transition | Role-dependent | `{ new_status, reason }` | `SuspectDetail` |
| `POST .../suspects/{id}/captain-verdict/` | Captain renders verdict | Captain | `{ verdict: "guilty"|"innocent", notes }` | `SuspectDetail` |
| `POST .../suspects/{id}/chief-approval/` | Chief approves/rejects (critical cases) | Police Chief | `{ decision: "approve"|"reject", notes? }` (notes req on reject) | `SuspectDetail` |

---

## 8. Interrogation, Trial & Verdict

### Interrogations (nested under suspects)

| Endpoint | Purpose | Auth | Request | Response |
|---|---|---|---|---|
| `GET .../suspects/{suspect_pk}/interrogations/` | List interrogation sessions | Auth | — | `[{ id, suspect, case, detective, detective_name, sergeant, sergeant_name, detective_guilt_score, sergeant_guilt_score, created_at }]` |
| `POST .../suspects/{suspect_pk}/interrogations/` | Record interrogation session | Auth (Detective/Sergeant) | `{ detective_guilt_score: 1-10, sergeant_guilt_score: 1-10, notes? }` | `InterrogationDetail` |
| `GET .../suspects/{suspect_pk}/interrogations/{id}/` | Get interrogation detail | Auth | — | `InterrogationDetail` with `suspect_name`, `notes`, `updated_at` |

### Trials (nested under suspects)

| Endpoint | Purpose | Auth | Request | Response |
|---|---|---|---|---|
| `GET .../suspects/{suspect_pk}/trials/` | List trials | Auth | — | `[{ id, suspect, case, judge, judge_name, verdict, verdict_display, punishment_title, created_at }]` |
| `POST .../suspects/{suspect_pk}/trials/` | Record trial verdict | Auth (Judge) | `{ verdict: "guilty"|"innocent", punishment_title?, punishment_description? }` (punishment fields req if guilty) | `TrialDetail` |
| `GET .../suspects/{suspect_pk}/trials/{id}/` | Get trial detail | Auth | — | `TrialDetail` with `suspect_name`, `punishment_description`, `updated_at` |

---

## 9. Bounty Tips

> **⚠ URL note:** Due to the double-prefix bug, actual runtime path is `/api/suspects/bounty-tips/...`

| Endpoint | Purpose | Auth | Request | Response |
|---|---|---|---|---|
| `GET /api/suspects/bounty-tips/` | List bounty tips | Auth | — | `[{ id, suspect, case, informant, informant_name, status, status_display, is_claimed, created_at }]` |
| `POST /api/suspects/bounty-tips/` | Submit bounty tip | Auth (any user) | `{ suspect?, case?, information }` (at least one of suspect/case) | `BountyTipDetail` |
| `GET /api/suspects/bounty-tips/{id}/` | Get tip detail | Auth | — | `BountyTipDetail` with `reviewed_by`, `verified_by`, `unique_code`, `reward_amount`, `updated_at` |
| `POST /api/suspects/bounty-tips/{id}/review/` | Officer reviews tip | Police Officer | `{ decision: "accept"|"reject", review_notes? }` | `BountyTipDetail` |
| `POST /api/suspects/bounty-tips/{id}/verify/` | Detective verifies tip → generates reward code | Detective | `{ decision: "verify"|"reject", verification_notes? }` | `BountyTipDetail` |
| `POST /api/suspects/bounty-tips/lookup-reward/` | Look up reward by national ID + code | Auth (any rank) | `{ national_id, unique_code }` | Reward info |

**Bounty tip status flow:** `pending` → `officer_reviewed` → `verified` (unique_code generated) or `rejected`

---

## 10. Bail & Payment (Optional)

> Bail is explicitly optional per §4.9. Backend fully supports it.

### Bail (nested under suspects)

| Endpoint | Purpose | Auth | Request | Response |
|---|---|---|---|---|
| `GET .../suspects/{suspect_pk}/bails/` | List bail records | Auth | — | `[{ id, suspect, case, amount, conditions, is_paid, approved_by, approved_by_name, paid_at, created_at }]` |
| `POST .../suspects/{suspect_pk}/bails/` | Create bail (set amount) | Sergeant | `{ amount, conditions? }` | `BailDetail` with `suspect_name`, `payment_reference` |
| `GET .../suspects/{suspect_pk}/bails/{id}/` | Get bail detail | Auth | — | `BailDetail` |
| `POST .../suspects/{suspect_pk}/bails/{id}/pay/` | Process bail payment | Auth | `{ payment_reference }` | `BailDetail` |

**Eligibility:** Level 2 and Level 3 crimes only. Sergeant approval required.

---

## 11. Notifications

| Endpoint | Purpose | Auth | Request | Response |
|---|---|---|---|---|
| `GET /api/core/notifications/` | List notifications for current user | Auth | — | `[{ id, title, message, is_read, created_at, content_type, object_id }]` |
| `POST /api/core/notifications/{id}/read/` | Mark notification as read | Auth | — | `Notification` |

**Notification triggers (backend-generated):**
- Evidence registered on a case → notify Detective
- Suspect identified → notify Sergeant
- Suspect approved/rejected → notify Detective
- Warrant issued → notify Detective
- Arrest executed → notify involved parties

**Mechanism:** HTTP polling only (no WebSocket).

---

## 12. System Constants & Global Search

### System Constants

| Endpoint | Purpose | Auth | Request | Response |
|---|---|---|---|---|
| `GET /api/core/constants/` | All enum/choice values for dropdowns | **Public** | — | See below |

**Constants response shape:**
```
{
  crime_levels: [{ value, label }],
  case_statuses: [{ value, label }],
  case_creation_types: [{ value, label }],
  evidence_types: [{ value, label }],
  evidence_file_types: [{ value, label }],
  suspect_statuses: [{ value, label }],
  verdict_choices: [{ value, label }],
  bounty_tip_statuses: [{ value, label }],
  complainant_statuses: [{ value, label }],
  role_hierarchy: [{ id, name, hierarchy_level }]
}
```

### Global Search

| Endpoint | Purpose | Auth | Request | Response |
|---|---|---|---|---|
| `GET /api/core/search/` | Unified search across cases, suspects, evidence | Auth | Query: `q` (min 2 chars, required), `category?` (cases/suspects/evidence), `limit?` (default 10, max 50) | See below |

**Search response shape:**
```
{
  query, total_results,
  cases: [{ id, title, status, crime_level, crime_level_label, created_at }],
  suspects: [{ id, full_name, national_id, status, case_id, case_title }],
  evidence: [{ id, title, evidence_type, evidence_type_label, case_id, case_title }]
}
```

---

## Endpoint Count Summary

| Feature Area | Endpoints |
|---|---|
| Auth & User Profile | 5 |
| Admin (User/Role/Permission) | 12 |
| Dashboard & Statistics | 1 |
| Cases (CRUD + Workflow + Sub-resources) | 27 |
| Evidence (CRUD + Workflow + Files) | 11 |
| Detective Board (CRUD + Items + Connections + Notes) | 15 |
| Suspects (CRUD + Workflow + Most Wanted) | 10 |
| Interrogations | 3 |
| Trials | 3 |
| Bounty Tips | 6 |
| Bail | 4 |
| Notifications | 2 |
| System Constants + Search | 2 |
| **Total** | **101** |

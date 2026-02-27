# Case / Suspect Workflow Refactor — Frontend Migration Guide

> **Date:** 2026-02-27  
> **Scope:** Backend refactoring that decouples case status from suspect lifecycle.  
> Suspects now progress independently; the case auto-transitions to `judiciary` when **all** suspects reach trial.

---

## 1. Summary of Backend Changes

### Removed Case Statuses

The following `CaseStatus` values no longer exist:

| Removed Status          | Old Position in Flow                          |
|-------------------------|-----------------------------------------------|
| `suspect_identified`    | After `investigation`, before `sergeant_review` |
| `sergeant_review`       | Sergeant reviewed suspect list on the case     |
| `arrest_ordered`        | After sergeant approved, before interrogation  |
| `interrogation`         | Case-level interrogation status                |
| `captain_review`        | Captain reviewing the case                     |
| `chief_review`          | Chief reviewing critical cases                 |

### Remaining Case Statuses (complete list)

```
complaint_registered → cadet_review → officer_review → open → investigation → judiciary → closed
                         ↓                 ↓
              returned_to_complainant  returned_to_cadet
                                           ↕
                                        voided
                       pending_approval (crime-scene path)
```

Full enum:
```typescript
type CaseStatus =
  | "complaint_registered"
  | "cadet_review"
  | "returned_to_complainant"
  | "officer_review"
  | "returned_to_cadet"
  | "voided"
  | "pending_approval"
  | "open"
  | "investigation"
  | "judiciary"
  | "closed";
```

### Removed API Endpoints (Cases)

| Endpoint                                  | Was Used For                                      |
|-------------------------------------------|---------------------------------------------------|
| `POST /api/cases/{id}/declare-suspects/`  | Detective declared suspects identified on the case |
| `POST /api/cases/{id}/sergeant-review/`   | Sergeant approved/rejected suspect list on the case |
| `POST /api/cases/{id}/forward-judiciary/` | Captain/Chief forwarded case to judiciary          |

### Removed API Endpoint (Suspects)

| Endpoint                                 | Was Used For                             |
|------------------------------------------|------------------------------------------|
| `POST /api/suspects/{id}/issue-warrant/` | Sergeant manually issued arrest warrant  |

---

## 2. New Workflow: How It Works Now

### Case Flow (simplified)

```
complaint_registered → cadet_review → officer_review → open → investigation → judiciary → closed
```

- The case stays in `investigation` during the **entire** suspect lifecycle.
- `investigation → judiciary` happens **automatically** when all suspects reach `under_trial`.
- `judiciary → closed` is triggered via the existing `POST /api/cases/{id}/transition/` endpoint.

### Suspect Flow (independent, per-suspect)

Each suspect progresses through their own status lifecycle, independent of the case status:

```
identify suspect          → wanted (default status)
sergeant approves         → wanted (+ auto-creates arrest warrant)
execute arrest            → arrested
begin interrogation       → under_interrogation
captain verdict           → under_trial (non-critical) or pending_chief_approval (critical)
chief approval (critical) → under_trial
trial verdict             → convicted / acquitted / released
```

#### Key Changes

1. **Sergeant approval now auto-creates the arrest warrant.**
   - `POST /api/suspects/{id}/approve/` with `decision: "approve"` automatically creates an active `Warrant`.
   - No separate `issue-warrant` call needed.

2. **When ALL suspects on a case reach `under_trial` (or beyond), the case auto-transitions to `judiciary`.**
   - "Beyond" means `convicted`, `acquitted`, or `released`.
   - This is triggered server-side; no frontend action needed.
   - The frontend should poll/refetch the case detail to show the updated status.

3. **Detective can edit a rejected suspect** to resubmit for approval.
   - `PATCH /api/suspects/{id}/` on a rejected suspect automatically resets `sergeant_approval_status` back to `"pending"`.
   - The sergeant can then re-review.

---

## 3. Frontend Files That Need Updates

### 3.1 `src/types/cases.ts` — Remove 6 status values

```diff
 export type CaseStatus =
   | "complaint_registered"
   | "cadet_review"
   | "returned_to_complainant"
   | "officer_review"
   | "returned_to_cadet"
   | "voided"
   | "pending_approval"
   | "open"
   | "investigation"
-  | "suspect_identified"
-  | "sergeant_review"
-  | "arrest_ordered"
-  | "interrogation"
-  | "captain_review"
-  | "chief_review"
   | "judiciary"
   | "closed";
```

### 3.2 `src/lib/caseWorkflow.ts` — Update labels, colors, actions

**STATUS_LABELS** — Remove 6 entries:
```diff
- suspect_identified: "Suspect Identified",
- sergeant_review: "Under Sergeant Review",
- arrest_ordered: "Arrest Ordered",
- interrogation: "Under Interrogation",
- captain_review: "Under Captain Review",
- chief_review: "Under Chief Review",
```

**STATUS_COLORS** — Remove same 6 entries:
```diff
- suspect_identified: "purple",
- sergeant_review: "blue",
- arrest_ordered: "orange",
- interrogation: "blue",
- captain_review: "blue",
- chief_review: "blue",
```

**STATUS_ACTIONS** — Replace old investigation/review actions:
```diff
  investigation: [
-   {
-     key: "declare_suspects",
-     label: "Declare Suspects",
-     variant: "primary",
-     requiredPermissions: ["cases.can_change_case_status"],
-   },
+   // No case-level actions; suspect flow is managed per-suspect.
+   // Case auto-transitions to judiciary when all suspects are under trial.
  ],
- sergeant_review: [...],
- arrest_ordered: [...],
- interrogation: [...],
- captain_review: [...],
- chief_review: [...],
```

Optionally add an `investigation` entry for "Transition to Judiciary" (manual override):
```typescript
investigation: [
  {
    key: "transition_judiciary",
    label: "Forward to Judiciary",
    variant: "primary",
    requiredPermissions: ["cases.can_forward_to_judiciary"],
  },
],
```
> This uses the generic `POST /api/cases/{id}/transition/` endpoint with `{ target_status: "judiciary" }`.

### 3.3 `src/api/endpoints.ts` — Remove 3 endpoints

```diff
- CASE_DECLARE_SUSPECTS: (caseId: number) => `/cases/${caseId}/declare-suspects/`,
- CASE_SERGEANT_REVIEW: (caseId: number) => `/cases/${caseId}/sergeant-review/`,
- CASE_FORWARD_JUDICIARY: (caseId: number) => `/cases/${caseId}/forward-judiciary/`,
```

Add suspect workflow endpoints (if not already present):
```typescript
  // Suspect workflow
  SUSPECT_APPROVE: (id: number) => `/suspects/${id}/approve/`,
  SUSPECT_ARREST: (id: number) => `/suspects/${id}/arrest/`,
  SUSPECT_TRANSITION: (id: number) => `/suspects/${id}/transition-status/`,
  SUSPECT_CAPTAIN_VERDICT: (id: number) => `/suspects/${id}/captain-verdict/`,
  SUSPECT_CHIEF_APPROVAL: (id: number) => `/suspects/${id}/chief-approval/`,
  suspectInterrogations: (suspectId: number) => `/suspects/${suspectId}/interrogations/`,
  suspectTrials: (suspectId: number) => `/suspects/${suspectId}/trials/`,
  suspectBails: (suspectId: number) => `/suspects/${suspectId}/bails/`,
```

### 3.4 Any component referencing removed endpoints/statuses

Search for and update:
- `CASE_DECLARE_SUSPECTS` / `CASE_SERGEANT_REVIEW` / `CASE_FORWARD_JUDICIARY`
- `declare-suspects` / `sergeant-review` / `forward-judiciary`
- `suspect_identified` / `sergeant_review` / `arrest_ordered` / `interrogation` / `captain_review` / `chief_review` (as case status strings)
- `issue-warrant` / `SUSPECT_ISSUE_WARRANT`

---

## 4. Suspect Workflow API Reference

### Suspect Lifecycle Endpoints

| Action                    | Method | URL                                          | Request Body                                                          | Required Permission                       |
|---------------------------|--------|----------------------------------------------|-----------------------------------------------------------------------|-------------------------------------------|
| Create (identify)         | POST   | `/api/suspects/`                             | `{ case, full_name, national_id, ... }`                               | `suspects.can_identify_suspect`           |
| Update profile            | PATCH  | `/api/suspects/{id}/`                        | `{ full_name?, address?, description?, ... }`                          | `suspects.change_suspect`                 |
| Sergeant approve/reject   | POST   | `/api/suspects/{id}/approve/`                | `{ decision: "approve"\|"reject", rejection_message?: "..." }`        | `suspects.can_approve_suspect`            |
| Execute arrest            | POST   | `/api/suspects/{id}/arrest/`                 | `{ arrest_location, arrest_notes?, warrant_override_justification? }` | `suspects.can_issue_arrest_warrant`       |
| Generic status transition | POST   | `/api/suspects/{id}/transition-status/`      | `{ new_status: "...", reason: "..." }`                                | Based on transition rules                 |
| Captain verdict           | POST   | `/api/suspects/{id}/captain-verdict/`        | `{ verdict: "guilty"\|"innocent", notes?: "..." }`                    | `suspects.can_render_verdict`             |
| Chief approval (critical) | POST   | `/api/suspects/{id}/chief-approval/`         | `{ decision: "approve"\|"reject", notes?: "..." }`                    | `cases.can_approve_critical_case`         |
| Create interrogation      | POST   | `/api/suspects/{suspectPk}/interrogations/`  | `{ detective_guilt_score, sergeant_guilt_score, notes? }`             | `suspects.can_conduct_interrogation`      |
| Create trial              | POST   | `/api/suspects/{suspectPk}/trials/`          | `{ verdict, punishment_title?, punishment_description? }`             | `suspects.can_judge_trial`                |

### Approval Side Effects

When sergeant **approves** a suspect:
- `sergeant_approval_status` → `"approved"`
- An **arrest warrant** is auto-created (status `"active"`, priority `"normal"`)
- Notification sent to the detective

When sergeant **rejects** a suspect:
- `sergeant_approval_status` → `"rejected"`
- `sergeant_rejection_message` populated
- Notification sent to the detective
- Detective can **edit the suspect** (`PATCH`) → `sergeant_approval_status` auto-resets to `"pending"`

### Auto-Transition: Case → Judiciary

After `submit_captain_verdict` (non-critical) or `process_chief_approval` (critical) moves a suspect to `under_trial`, the backend checks:

> Are **all** suspects on this case in `under_trial`, `convicted`, `acquitted`, or `released`?

If yes → the case automatically transitions from `investigation` to `judiciary`.

**Frontend implication:** After a captain/chief action succeeds, refetch the case detail to check if the status changed to `judiciary`.

---

## 5. Suspect Status Display Metadata (for UI)

```typescript
export const SUSPECT_STATUS_LABELS: Record<SuspectStatus, string> = {
  wanted: "Wanted",
  arrested: "Arrested / In Custody",
  under_interrogation: "Under Interrogation",
  pending_captain_verdict: "Pending Captain Verdict",
  pending_chief_approval: "Pending Chief Approval",
  under_trial: "Under Trial",
  convicted: "Convicted",
  acquitted: "Acquitted",
  released: "Released",
};

export const SUSPECT_STATUS_COLORS: Record<SuspectStatus, string> = {
  wanted: "red",
  arrested: "orange",
  under_interrogation: "blue",
  pending_captain_verdict: "yellow",
  pending_chief_approval: "yellow",
  under_trial: "purple",
  convicted: "red",
  acquitted: "green",
  released: "green",
};
```

### Suspect Workflow Actions (per status)

```typescript
export const SUSPECT_STATUS_ACTIONS: Partial<Record<SuspectStatus, SuspectWorkflowAction[]>> = {
  wanted: [
    // Shown only if sergeant_approval_status === "pending"
    { key: "approve", label: "Approve Suspect", variant: "primary",
      requiredPermissions: ["suspects.can_approve_suspect"] },
    { key: "reject", label: "Reject Suspect", variant: "danger", needsMessage: true,
      requiredPermissions: ["suspects.can_approve_suspect"] },
    // Shown only if sergeant_approval_status === "approved"
    { key: "arrest", label: "Execute Arrest", variant: "primary",
      requiredPermissions: ["suspects.can_issue_arrest_warrant"] },
  ],
  arrested: [
    { key: "begin_interrogation", label: "Begin Interrogation", variant: "primary",
      requiredPermissions: ["suspects.can_conduct_interrogation"] },
  ],
  under_interrogation: [
    { key: "captain_verdict", label: "Submit Captain Verdict", variant: "primary",
      requiredPermissions: ["suspects.can_render_verdict"] },
  ],
  pending_captain_verdict: [
    { key: "captain_verdict", label: "Submit Captain Verdict", variant: "primary",
      requiredPermissions: ["suspects.can_render_verdict"] },
  ],
  pending_chief_approval: [
    { key: "chief_approve", label: "Approve", variant: "primary",
      requiredPermissions: ["cases.can_approve_critical_case"] },
    { key: "chief_reject", label: "Reject", variant: "danger", needsMessage: true,
      requiredPermissions: ["cases.can_approve_critical_case"] },
  ],
};
```

---

## 6. Recommended UI Flow

### Case Detail Page — Investigation Status

When a case is in `investigation`:
1. Show a **Suspects panel/tab** listing all suspects and their individual statuses.
2. Each suspect row should show:
   - Name, national ID, status badge, approval status badge
   - Action buttons based on the suspect's current status and the user's permissions
3. Show a progress indicator: "X of Y suspects at trial" to visualize how close the case is to auto-transitioning.
4. Remove any "Declare Suspects" or "Forward to Judiciary" buttons from the case toolbar.

### Suspect Approval Flow (Sergeant)

```
Suspect created (status: wanted, approval: pending)
  → Sergeant sees "Approve" / "Reject" buttons
  → On approve: warrant auto-created, "Execute Arrest" button appears
  → On reject: detective sees rejection message, edits suspect, approval resets to pending
```

### Suspect Arrest → Trial Flow

```
wanted (approved) → Execute Arrest → arrested
arrested → Begin Interrogation → under_interrogation
under_interrogation → Submit Captain Verdict
  → non-critical case: under_trial
  → critical case: pending_chief_approval → Chief approves → under_trial
under_trial → (auto: case transitions to judiciary when all suspects are under_trial)
```

### Case Auto-Transition Notification

After any captain verdict or chief approval succeeds, the frontend should:
1. Refetch the case detail (`GET /api/cases/{id}/`)
2. If status changed to `judiciary`, show a toast/notification: "All suspects are at trial. Case forwarded to judiciary."

---

## 7. Migration Checklist

- [ ] Update `CaseStatus` type — remove 6 values
- [ ] Update `STATUS_LABELS` — remove 6 entries
- [ ] Update `STATUS_COLORS` — remove 6 entries
- [ ] Update `STATUS_ACTIONS` — remove 6 entries, update `investigation` entry
- [ ] Remove 3 endpoint functions from `endpoints.ts`
- [ ] Add suspect workflow endpoints to `endpoints.ts`
- [ ] Create `suspects` API service with approve, arrest, verdict calls
- [ ] Update case detail page — remove declare/sergeant/forward buttons
- [ ] Add suspects panel to case detail page (investigation status)
- [ ] Add suspect detail page with per-suspect workflow actions
- [ ] Handle auto-transition: refetch case after suspect verdict actions
- [ ] Remove any `issue-warrant` UI references
- [ ] Search codebase for any remaining references to removed statuses/endpoints

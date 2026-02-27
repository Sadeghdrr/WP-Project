# Suspects App — API Report

## 1. Endpoint Reference Table

### 1.1 Suspect CRUD & Workflow

| HTTP Method | URL                                     | Purpose                                          | Access Level                           |
| ----------- | --------------------------------------- | ------------------------------------------------ | -------------------------------------- |
| `GET`       | `/api/suspects/`                        | List suspects (filtered, role-scoped)            | Authenticated (role-scoped visibility) |
| `POST`      | `/api/suspects/`                        | Identify/create a new suspect for a case         | Detective (`CAN_IDENTIFY_SUSPECT`)     |
| `GET`       | `/api/suspects/{id}/`                   | Retrieve full suspect detail with nested data    | Authenticated (role-scoped)            |
| `PATCH`     | `/api/suspects/{id}/`                   | Update suspect profile fields                    | Detective+ (`CHANGE_SUSPECT`)          |
| `GET`       | `/api/suspects/most-wanted/`            | Public Most Wanted listing (> 30 days wanted)    | All authenticated users                |
| `POST`      | `/api/suspects/{id}/approve/`           | Sergeant approves/rejects suspect identification | Sergeant (`CAN_APPROVE_SUSPECT`)       |
| `POST`      | `/api/suspects/{id}/issue-warrant/`     | Issue an arrest warrant for approved suspect     | Sergeant (`CAN_ISSUE_ARREST_WARRANT`)  |
| `POST`      | `/api/suspects/{id}/arrest/`            | Execute arrest — transition to "In Custody"      | Sergeant+ (`CAN_ISSUE_ARREST_WARRANT`) |
| `POST`      | `/api/suspects/{id}/transition-status/` | Generic lifecycle status transition              | Varies by transition (see §3)          |

### 1.2 Interrogations (Nested under Suspects)

| HTTP Method | URL                                               | Purpose                                   | Access Level                                     |
| ----------- | ------------------------------------------------- | ----------------------------------------- | ------------------------------------------------ |
| `GET`       | `/api/suspects/{suspect_pk}/interrogations/`      | List interrogation sessions for a suspect | Authenticated (`VIEW_INTERROGATION`)             |
| `POST`      | `/api/suspects/{suspect_pk}/interrogations/`      | Create an interrogation session           | Detective/Sergeant (`CAN_CONDUCT_INTERROGATION`) |
| `GET`       | `/api/suspects/{suspect_pk}/interrogations/{id}/` | Retrieve interrogation session detail     | Authenticated (`VIEW_INTERROGATION`)             |

### 1.3 Trials (Nested under Suspects)

| HTTP Method | URL                                       | Purpose                                      | Access Level                 |
| ----------- | ----------------------------------------- | -------------------------------------------- | ---------------------------- |
| `GET`       | `/api/suspects/{suspect_pk}/trials/`      | List trial records for a suspect             | Authenticated (`VIEW_TRIAL`) |
| `POST`      | `/api/suspects/{suspect_pk}/trials/`      | Create a trial record (verdict + punishment) | Judge (`CAN_JUDGE_TRIAL`)    |
| `GET`       | `/api/suspects/{suspect_pk}/trials/{id}/` | Retrieve trial record detail                 | Authenticated (`VIEW_TRIAL`) |

### 1.4 Bails (Nested under Suspects)

| HTTP Method | URL                                          | Purpose                                 | Access Level                     |
| ----------- | -------------------------------------------- | --------------------------------------- | -------------------------------- |
| `GET`       | `/api/suspects/{suspect_pk}/bails/`          | List bail records for a suspect         | Authenticated (`VIEW_BAIL`)      |
| `POST`      | `/api/suspects/{suspect_pk}/bails/`          | Create a bail record (set bail amount)  | Sergeant (`CAN_SET_BAIL_AMOUNT`) |
| `GET`       | `/api/suspects/{suspect_pk}/bails/{id}/`     | Retrieve bail record detail             | Authenticated (`VIEW_BAIL`)      |
| `POST`      | `/api/suspects/{suspect_pk}/bails/{id}/pay/` | Process bail payment (gateway callback) | Authenticated                    |

### 1.5 Bounty Tips (Top-Level)

| HTTP Method | URL                               | Purpose                                     | Access Level                             |
| ----------- | --------------------------------- | ------------------------------------------- | ---------------------------------------- |
| `GET`       | `/api/bounty-tips/`               | List bounty tips (role-scoped)              | Authenticated (role-scoped)              |
| `POST`      | `/api/bounty-tips/`               | Submit a bounty tip (citizen action; open case and wanted suspect validations apply) | Any authenticated user |
| `GET`       | `/api/bounty-tips/{id}/`          | Retrieve bounty tip detail                  | Authenticated (owner or police)          |
| `POST`      | `/api/bounty-tips/{id}/review/`   | Officer reviews a bounty tip                | Police Officer (`CAN_REVIEW_BOUNTY_TIP`) |
| `POST`      | `/api/bounty-tips/{id}/verify/`   | Detective verifies a bounty tip             | Detective (`CAN_VERIFY_BOUNTY_TIP`)      |
| `POST`      | `/api/bounty-tips/lookup-reward/` | Look up reward by national ID + unique code | Any police rank                          |

---

## 2. Global Status vs. Case-Specific Involvement

### 2.1 Conceptual Distinction

The suspects app manages two conceptually distinct status dimensions:

#### Global Status (Suspect Lifecycle)

The `Suspect.status` field tracks the **lifecycle state** of a suspect within a specific case. Since each `Suspect` row represents a person-case combination (a person can be a suspect in multiple cases, each creating a separate `Suspect` row), this status governs the suspect's progression through the justice system for that particular case:

```
WANTED → ARRESTED → UNDER_INTERROGATION → UNDER_TRIAL → CONVICTED / ACQUITTED
                                                      ↘ RELEASED (bail)
```

| Status                | Meaning                                        |
| --------------------- | ---------------------------------------------- |
| `wanted`              | Suspect identified and pending arrest          |
| `arrested`            | In custody after arrest execution              |
| `under_interrogation` | Being interrogated by Detective + Sergeant     |
| `under_trial`         | Case forwarded to judiciary, trial in progress |
| `convicted`           | Found guilty by Judge                          |
| `acquitted`           | Found innocent by Judge                        |
| `released`            | Released on bail/fine payment                  |

#### Case-Specific Involvement

A suspect's involvement across multiple cases is handled through **separate `Suspect` rows sharing the same `national_id`**. Each row has its own independent `status`, allowing a person to be:

- `wanted` in Case A
- `arrested` in Case B
- `convicted` in Case C

Cross-case aggregation (for Most Wanted ranking) uses `national_id` to group all records for the same individual.

### 2.2 API Handling

| Concern                         | API Approach                                                                                                                                                                            |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **View single case status**     | `GET /api/suspects/{id}/` — returns the status for that specific suspect-case row                                                                                                       |
| **View all cases for a person** | `GET /api/suspects/?national_id=1234567890` — returns all suspect rows for that national ID                                                                                             |
| **Transition status**           | `POST /api/suspects/{id}/arrest/` or `/transition-status/` — operates on a single suspect-case row                                                                                      |
| **Most Wanted (cross-case)**    | `GET /api/suspects/most-wanted/` — aggregates across all `national_id` records, computing `most_wanted_score = max(days_wanted across open cases) × max(crime_degree across all cases)` |
| **Sergeant approval**           | Per suspect-case row — Sergeant approves each suspect identification independently                                                                                                      |

### 2.3 Design Rationale

This design satisfies the project requirements (§4.4, §4.7):

- **§4.4**: Detective identifies suspects per case → each creates a `Suspect` row.
- **§4.7**: Most Wanted ranking aggregates across cases using `national_id` grouping.
- **§4.7 Note 1**: The score formula `max(Lj) × max(Di)` requires cross-case data, computed as a Python property on the model.

---

## 3. ArrestAndWarrantService Workflow

### 3.1 Overview

The `ArrestAndWarrantService` is the central service class that manages the complete arrest lifecycle. It enforces strict permission checks, state validation, and audit logging at every step.

### 3.2 Full Workflow Sequence

```
┌─────────────────────────────────────────────────────────────────────┐
│  Step 1: Detective Identifies Suspect                               │
│  ─────────────────────────────────────                              │
│  Endpoint: POST /api/suspects/                                      │
│  Service:  SuspectProfileService.create_suspect()                   │
│  Permission: CAN_IDENTIFY_SUSPECT (Detective)                       │
│  Result: Suspect created with status=WANTED,                        │
│          sergeant_approval_status=pending                           │
│  Notification: → Sergeant (new suspect pending approval)            │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 2: Sergeant Approves/Rejects                                  │
│  ─────────────────────────────────                                  │
│  Endpoint: POST /api/suspects/{id}/approve/                         │
│  Service:  ArrestAndWarrantService.approve_or_reject_suspect()      │
│  Permission: CAN_APPROVE_SUSPECT (Sergeant)                         │
│                                                                     │
│  Validation:                                                        │
│  ✓ Suspect must be in "pending" approval status                     │
│  ✓ If rejecting, rejection_message is required                      │
│                                                                     │
│  On Approve:                                                        │
│    → sergeant_approval_status = "approved"                          │
│    → Notification to Detective: "Approved, warrant may be issued"   │
│                                                                     │
│  On Reject:                                                         │
│    → sergeant_approval_status = "rejected"                          │
│    → sergeant_rejection_message = <reason>                          │
│    → Notification to Detective with objection message               │
│    → Case remains open for further investigation                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ (if approved)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 3: Sergeant Issues Arrest Warrant                             │
│  ──────────────────────────────────────                             │
│  Endpoint: POST /api/suspects/{id}/issue-warrant/                   │
│  Service:  ArrestAndWarrantService.issue_arrest_warrant()           │
│  Permission: CAN_ISSUE_ARREST_WARRANT (Sergeant)                    │
│                                                                     │
│  Validation:                                                        │
│  ✓ sergeant_approval_status == "approved"                           │
│  ✓ status == WANTED                                                 │
│  ✓ No duplicate active warrant                                      │
│                                                                     │
│  Records: warrant_reason, priority, timestamp, issuing_sergeant     │
│  Notification: → Detective (warrant issued, arrest can proceed)     │
│                                                                     │
│  Note: Suspect remains in WANTED status; warrant is on record.      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 4: Execute Arrest (CRITICAL)                                  │
│  ─────────────────────────────────                                  │
│  Endpoint: POST /api/suspects/{id}/arrest/                          │
│  Service:  ArrestAndWarrantService.execute_arrest()                 │
│  Permission: CAN_ISSUE_ARREST_WARRANT (Sergeant+)                   │
│                                                                     │
│  Validation Sequence:                                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 1. Permission Check                                           │  │
│  │    → User must have CAN_ISSUE_ARREST_WARRANT                  │  │
│  │    → Raises PermissionError if not                             │  │
│  │                                                               │  │
│  │ 2. Status Guard                                               │  │
│  │    → Suspect must be in WANTED status                         │  │
│  │    → Raises ValidationError if arrested/convicted/etc.        │  │
│  │                                                               │  │
│  │ 3. Approval Guard                                             │  │
│  │    → sergeant_approval_status must be "approved"              │  │
│  │    → Prevents arrest of unverified suspects                   │  │
│  │                                                               │  │
│  │ 4. Warrant Validation                                         │  │
│  │    → Check if active warrant exists for this suspect          │  │
│  │    → If NO warrant:                                           │  │
│  │      • warrant_override_justification must be provided        │  │
│  │      • If blank → Raises ValidationError                     │  │
│  │      • If provided → Logged as warrantless arrest             │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Execution:                                                         │
│    → suspect.status = ARRESTED                                      │
│    → Audit log: officer, location, notes, timestamp, warrant info   │
│                                                                     │
│  Notifications:                                                     │
│    → Detective (suspect arrested)                                   │
│    → Captain (suspect arrested)                                     │
│    → Police Chief (if critical case)                                │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 5+: Subsequent Lifecycle Transitions                          │
│  ─────────────────────────────────────────                          │
│  Endpoint: POST /api/suspects/{id}/transition-status/               │
│  Service:  ArrestAndWarrantService.transition_status()              │
│                                                                     │
│  State Machine:                                                     │
│  ┌──────────────────────┬──────────────────────┬──────────────────┐ │
│  │ Current Status       │ Allowed Targets      │ Required Perm    │ │
│  ├──────────────────────┼──────────────────────┼──────────────────┤ │
│  │ ARRESTED             │ UNDER_INTERROGATION  │ CAN_CONDUCT_     │ │
│  │                      │                      │ INTERROGATION    │ │
│  │ ARRESTED             │ RELEASED             │ CAN_SET_BAIL_    │ │
│  │                      │                      │ AMOUNT           │ │
│  │ UNDER_INTERROGATION  │ UNDER_TRIAL          │ CAN_RENDER_      │ │
│  │                      │                      │ VERDICT          │ │
│  │ UNDER_TRIAL          │ CONVICTED            │ CAN_JUDGE_TRIAL  │ │
│  │ UNDER_TRIAL          │ ACQUITTED            │ CAN_JUDGE_TRIAL  │ │
│  │ CONVICTED            │ RELEASED             │ CAN_SET_BAIL_    │ │
│  │                      │                      │ AMOUNT           │ │
│  └──────────────────────┴──────────────────────┴──────────────────┘ │
│                                                                     │
│  Invalid transitions raise ValidationError.                         │
│  Missing permissions raise PermissionError.                         │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 Permission Summary

| Permission Codename         | Role(s)               | Used In                                            |
| --------------------------- | --------------------- | -------------------------------------------------- |
| `can_identify_suspect`      | Detective             | Creating suspect records                           |
| `can_approve_suspect`       | Sergeant              | Approving/rejecting suspect identifications        |
| `can_issue_arrest_warrant`  | Sergeant              | Issuing warrants + executing arrests               |
| `can_conduct_interrogation` | Detective, Sergeant   | Creating interrogation sessions, status transition |
| `can_score_guilt`           | Detective, Sergeant   | Assigning guilt probability (1–10)                 |
| `can_render_verdict`        | Captain, Police Chief | Forwarding to trial (status transition)            |
| `can_judge_trial`           | Judge                 | Recording trial verdict + punishment               |
| `can_review_bounty_tip`     | Police Officer        | Initial bounty tip review                          |
| `can_verify_bounty_tip`     | Detective             | Bounty tip verification + code generation          |
| `can_set_bail_amount`       | Sergeant              | Setting bail amount, releasing suspects            |

### 3.4 Key Design Decisions

1. **Defence in Depth**: Both the view layer (`IsAuthenticated`) and the service layer (role-specific `has_perm` checks) enforce authorization. The service is the authoritative source.

2. **Warrant-or-Override**: The arrest endpoint allows warrantless arrests with mandatory justification, creating an auditable paper trail for emergency situations (e.g., caught in the act).

3. **State Machine Enforcement**: The `_ALLOWED_TRANSITIONS` dict in `ArrestAndWarrantService` defines the complete legal state machine. Any transition not in this map is rejected with a `ValidationError`.

4. **Atomic Transactions**: All state-changing operations use `@transaction.atomic` to ensure data consistency — either the full operation succeeds or nothing changes.

5. **Notification Dispatch**: Every significant workflow step dispatches notifications to relevant personnel (Detective, Sergeant, Captain, Chief), ensuring the chain of command is informed.

---

## 4. Architecture Notes

### 4.1 Separation of Concerns

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│   URLs      │───▶│   Views      │───▶│   Services      │
│  (routing)  │    │  (thin: I/O  │    │  (all business  │
│             │    │   only)      │    │   logic)        │
└─────────────┘    └──────┬───────┘    └────────┬────────┘
                          │                     │
                   ┌──────▼───────┐    ┌────────▼────────┐
                   │ Serializers  │    │    Models        │
                   │ (validation  │    │  (data layer +   │
                   │  + shape)    │    │   computed props) │
                   └──────────────┘    └─────────────────┘
```

### 4.2 File Summary

| File             | Purpose                                                                    |
| ---------------- | -------------------------------------------------------------------------- |
| `urls.py`        | Route definitions using DRF routers + nested routers                       |
| `views.py`       | Thin ViewSets — parse request, delegate to service, return response        |
| `serializers.py` | Input validation + output shaping — no business logic                      |
| `services.py`    | All business logic: permissions, state transitions, audit, notifications   |
| `models.py`      | Data layer with computed properties (`most_wanted_score`, `reward_amount`) |

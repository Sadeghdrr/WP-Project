# Cases Services — Complaint Flow Implementation Report

**Scope:** Complaint-based case creation, cadet/officer review, 3-strike void rule, complainant management  
**Branch:** `feat/cases-services`  
**Files Modified:** `cases/services.py`, `cases/views.py`, `cases/serializers.py`

---

## 1. State Diagram — Complaint Workflow

```
                    ┌───────────────────────┐
                    │  COMPLAINT_REGISTERED  │
                    │  (citizen creates)     │
                    └───────────┬───────────┘
                                │
                   [POST /cases/{id}/submit/]
                    (primary complainant)
                                │
                                ▼
                    ┌───────────────────────┐
            ┌──────│     CADET_REVIEW       │──────┐
            │      └───────────────────────┘      │
            │                                      │
    [cadet rejects]                        [cadet approves]
    rejection_count++                              │
            │                                      │
            ▼                                      ▼
  ┌──────────────────────────┐        ┌───────────────────────┐
  │ RETURNED_TO_COMPLAINANT  │        │    OFFICER_REVIEW     │
  │ (with rejection message) │        │ (forwarded to officer)│
  └────────────┬─────────────┘        └───────────┬───────────┘
               │                                  │
   [POST /cases/{id}/resubmit/]          ┌────────┴────────┐
   (complainant edits & resends)         │                  │
               │                [officer approves]  [officer rejects]
               ▼                         │                  │
      CADET_REVIEW ↺                     ▼                  ▼
                                ┌──────────────┐  ┌────────────────────┐
                                │     OPEN     │  │  RETURNED_TO_CADET │
                                │ (case live!) │  │ (back to cadet)    │
                                └──────────────┘  └────────┬───────────┘
                                                           │
                                                  [cadet re-reviews &
                                                   re-submits to officer]
                                                           │
                                                           ▼
                                                   OFFICER_REVIEW ↺

  ┌──────────────────────────────────────────────────────────────────┐
  │  3-STRIKE AUTO-VOID RULE                                         │
  │  ────────────────────────                                        │
  │  If rejection_count >= 3 during cadet review:                    │
  │                                                                  │
  │    CADET_REVIEW ──────────► VOIDED                               │
  │    (automatic, no manual step needed)                            │
  │                                                                  │
  │  The complainant is notified. Case is permanently closed.        │
  └──────────────────────────────────────────────────────────────────┘
```

---

## 2. Notifications Emitted

| Trigger Status           | Event Type          | Recipients                     |
|--------------------------|---------------------|--------------------------------|
| `RETURNED_TO_COMPLAINANT`| `complaint_returned`| Primary complainant            |
| `VOIDED`                 | `case_rejected`     | Primary complainant            |
| `OFFICER_REVIEW`         | `case_status_changed`| *(no specific recipient)*     |
| `OPEN`                   | `case_approved`     | Case creator (`created_by`)    |
| `RETURNED_TO_CADET`      | `case_rejected`     | *(no specific cadet assigned)* |
| `INVESTIGATION`          | `assignment_changed`| Assigned detective             |
| `SERGEANT_REVIEW`        | `case_status_changed`| Assigned sergeant             |
| `CAPTAIN_REVIEW`         | `case_status_changed`| Assigned captain              |
| `JUDICIARY`              | `case_status_changed`| Assigned judge                |
| `CLOSED`                 | `case_status_changed`| Case creator + detective      |

Notifications are created via `NotificationService.create()` from `core.domain.notifications`.

---

## 3. API Sequences

### 3.1 Happy Path — Complaint Created, Reviewed, Approved

```bash
# Step 1: Complainant creates a complaint case
curl -X POST /api/cases/ \
  -H "Authorization: Bearer <complainant_token>" \
  -d '{
    "creation_type": "complaint",
    "title": "Stolen bicycle",
    "description": "My bicycle was stolen from outside the library.",
    "crime_level": 1
  }'
# → 201 Created, case.status = "complaint_registered"

# Step 2: Complainant submits for cadet review
curl -X POST /api/cases/1/submit/ \
  -H "Authorization: Bearer <complainant_token>"
# → 200 OK, case.status = "cadet_review"

# Step 3: Cadet reviews individual complainant info (approve)
curl -X POST /api/cases/1/complainants/1/review/ \
  -H "Authorization: Bearer <cadet_token>" \
  -d '{"decision": "approve"}'
# → 200 OK, complainant.status = "approved"

# Step 4: Cadet approves the case → forwarded to officer
curl -X POST /api/cases/1/cadet-review/ \
  -H "Authorization: Bearer <cadet_token>" \
  -d '{"decision": "approve"}'
# → 200 OK, case.status = "officer_review"

# Step 5: Officer approves → case is OPEN
curl -X POST /api/cases/1/officer-review/ \
  -H "Authorization: Bearer <officer_token>" \
  -d '{"decision": "approve"}'
# → 200 OK, case.status = "open", case.approved_by = officer
```

### 3.2 Rejection & Resubmission Path

```bash
# … after Step 2 above (case in cadet_review) …

# Cadet finds defects → rejects with message
curl -X POST /api/cases/1/cadet-review/ \
  -H "Authorization: Bearer <cadet_token>" \
  -d '{"decision": "reject", "message": "Missing incident date and location."}'
# → 200 OK, case.status = "returned_to_complainant", rejection_count = 1
# → Notification sent to primary complainant

# Complainant edits and resubmits
curl -X POST /api/cases/1/resubmit/ \
  -H "Authorization: Bearer <complainant_token>" \
  -d '{
    "incident_date": "2026-02-20T14:30:00Z",
    "location": "Central Library, Main St"
  }'
# → 200 OK, case.status = "cadet_review"

# Cadet approves this time
curl -X POST /api/cases/1/cadet-review/ \
  -H "Authorization: Bearer <cadet_token>" \
  -d '{"decision": "approve"}'
# → 200 OK, case.status = "officer_review"
```

### 3.3 Officer Rejects → Returned to Cadet

```bash
# Case is in officer_review after cadet approval

# Officer finds a flaw → returns to cadet (NOT to complainant)
curl -X POST /api/cases/1/officer-review/ \
  -H "Authorization: Bearer <officer_token>" \
  -d '{"decision": "reject", "message": "Crime level seems incorrect."}'
# → 200 OK, case.status = "returned_to_cadet"

# Cadet re-reviews and re-submits to officer
# (Uses generic transition endpoint)
curl -X POST /api/cases/1/transition/ \
  -H "Authorization: Bearer <cadet_token>" \
  -d '{"target_status": "officer_review"}'
# → 200 OK, case.status = "officer_review"
```

### 3.4 Three-Strike Void Path

```bash
# Strike 1: Cadet rejects
curl -X POST /api/cases/1/cadet-review/ \
  -H "Authorization: Bearer <cadet_token>" \
  -d '{"decision": "reject", "message": "Incomplete information."}'
# → 200 OK, status = "returned_to_complainant", rejection_count = 1

# Complainant resubmits
curl -X POST /api/cases/1/resubmit/ \
  -H "Authorization: Bearer <complainant_token>" \
  -d '{"description": "Updated description with more details."}'
# → 200 OK, status = "cadet_review"

# Strike 2: Cadet rejects again
curl -X POST /api/cases/1/cadet-review/ \
  -H "Authorization: Bearer <cadet_token>" \
  -d '{"decision": "reject", "message": "Still missing witness info."}'
# → 200 OK, status = "returned_to_complainant", rejection_count = 2

# Complainant resubmits again
curl -X POST /api/cases/1/resubmit/ \
  -H "Authorization: Bearer <complainant_token>" \
  -d '{"description": "Final attempt with all information."}'
# → 200 OK, status = "cadet_review"

# Strike 3: Cadet rejects a third time → AUTO-VOID
curl -X POST /api/cases/1/cadet-review/ \
  -H "Authorization: Bearer <cadet_token>" \
  -d '{"decision": "reject", "message": "Information is still false."}'
# → 200 OK, status = "voided", rejection_count = 3
# → Notification sent to primary complainant: "Case Rejected"
# → Case is permanently voided — no further resubmissions possible
```

### 3.5 Adding Additional Complainants

```bash
# Add another complainant to an existing case
curl -X POST /api/cases/1/complainants/ \
  -H "Authorization: Bearer <authorized_token>" \
  -d '{"user_id": 42}'
# → 201 Created, new CaseComplainant record

# Cadet reviews the additional complainant
curl -X POST /api/cases/1/complainants/2/review/ \
  -H "Authorization: Bearer <cadet_token>" \
  -d '{"decision": "approve"}'
# → 200 OK, complainant.status = "approved"
```

---

## 4. Implementation Architecture

### 4.1 Fat Services, Skinny Views

All business logic resides in `cases/services.py`:

| Service Class            | Methods Implemented                                                    |
|--------------------------|------------------------------------------------------------------------|
| `CaseCreationService`    | `create_complaint_case()`                                              |
| `CaseWorkflowService`    | `transition_state()`, `submit_for_review()`, `resubmit_complaint()`,   |
|                          | `process_cadet_review()`, `process_officer_review()`,                  |
|                          | `_dispatch_notifications()`                                            |
| `CaseComplainantService` | `add_complainant()`, `review_complainant()`                            |

### 4.2 Concurrency Control

- `transition_state()` uses `Case.objects.select_for_update().get(pk=case.pk)` inside `@transaction.atomic` to prevent race conditions on status changes.
- `process_cadet_review()` also locks the case row before incrementing `rejection_count`.
- `process_officer_review()` locks before setting `approved_by`.

### 4.3 Status Logging

Every state transition creates a `CaseStatusLog` entry recording:
- `from_status` → `to_status`
- `changed_by` (the acting user)
- `message` (rejection reason or context)
- `created_at` (automatic timestamp)

### 4.4 Serializer Validations Implemented

| Serializer                       | Validation                                         |
|----------------------------------|----------------------------------------------------|
| `ComplaintCaseCreateSerializer`   | `crime_level` must be a valid `CrimeLevel` value   |
| `CadetReviewSerializer`          | `message` required when `decision == "reject"`     |
| `OfficerReviewSerializer`        | `message` required when `decision == "reject"`     |
| `SergeantReviewSerializer`       | `message` required when `decision == "reject"`     |
| `CaseWitnessCreateSerializer`    | `national_id` must be exactly 10 digits            |

---

## 5. Permission Matrix (Complaint Flow)

| Transition                                      | Required Permission        | Typical Role         |
|-------------------------------------------------|---------------------------|----------------------|
| `COMPLAINT_REGISTERED → CADET_REVIEW`           | `add_case`                | Complainant          |
| `CADET_REVIEW → OFFICER_REVIEW`                 | `can_review_complaint`    | Cadet                |
| `CADET_REVIEW → RETURNED_TO_COMPLAINANT`        | `can_review_complaint`    | Cadet                |
| `CADET_REVIEW → VOIDED`                         | `can_review_complaint`    | Cadet (auto-trigger) |
| `RETURNED_TO_COMPLAINANT → CADET_REVIEW`        | `add_case`                | Complainant          |
| `OFFICER_REVIEW → OPEN`                         | `can_approve_case`        | Police Officer       |
| `OFFICER_REVIEW → RETURNED_TO_CADET`            | `can_approve_case`        | Police Officer       |
| `RETURNED_TO_CADET → OFFICER_REVIEW`            | `can_review_complaint`    | Cadet                |

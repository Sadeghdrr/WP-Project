# Crime-Scene Case Creation — Service Implementation Report

**Branch:** `feat/cases-services`  
**Scope:** `CaseCreationService.create_crime_scene_case`, `CaseWitnessService`, `CaseWorkflowService.approve_crime_scene`, `CaseAssignmentService` basics  
**Date:** February 2026

---

## 1. Approval Rules Table

The crime-scene creation path determines the initial status based on the **creator's role**:

| Creator Role     | Initial Status      | Requires Approval? | Auto `approved_by` |
|------------------|----------------------|---------------------|---------------------|
| Police Chief     | `OPEN`              | ❌ No               | Set to creator      |
| Captain          | `PENDING_APPROVAL`  | ✅ Yes              | —                   |
| Sergeant         | `PENDING_APPROVAL`  | ✅ Yes              | —                   |
| Detective        | `PENDING_APPROVAL`  | ✅ Yes              | —                   |
| Police Officer   | `PENDING_APPROVAL`  | ✅ Yes              | —                   |
| Patrol Officer   | `PENDING_APPROVAL`  | ✅ Yes              | —                   |
| Cadet            | ❌ **FORBIDDEN**    | N/A                 | N/A                 |
| Base User        | ❌ **FORBIDDEN**    | N/A                 | N/A                 |
| Complainant      | ❌ **FORBIDDEN**    | N/A                 | N/A                 |

### Who Can Approve?

Any user holding the `can_approve_case` permission can approve a crime-scene case in `PENDING_APPROVAL` status. This permission is assigned to:

| Approver Role    | Can Approve? |
|------------------|--------------|
| Police Chief     | ✅           |
| Captain          | ✅           |
| Police Officer   | ✅           |
| Sergeant         | ❌           |
| Detective        | ❌           |
| Cadet            | ❌           |

> **Rule:** Only **one** superior approval is needed (§4.2.2). The approver is recorded in `case.approved_by`.

---

## 2. Assignment Rules & Exceptions

### 2.1 Detective Assignment

| Constraint           | Detail |
|----------------------|--------|
| Permission required  | `can_assign_detective` |
| Case status          | Must be `OPEN` |
| Assignee role        | Must hold `Detective` role |
| Side effect          | Status transitions to `INVESTIGATION` |
| Notification         | Sent to assigned detective |

### 2.2 Sergeant Assignment

| Constraint           | Detail |
|----------------------|--------|
| Permission required  | `can_assign_detective` |
| Case status          | Any active status (no status transition) |
| Assignee role        | Must hold `Sergeant` role |
| Side effect          | Status log entry created |
| Notification         | Sent to assigned sergeant |

### 2.3 Captain Assignment

| Constraint           | Detail |
|----------------------|--------|
| Permission required  | `can_assign_detective` |
| Case status          | Any active status (no status transition) |
| Assignee role        | Must hold `Captain` role |
| Side effect          | Status log entry created |
| Notification         | Sent to assigned captain |

### 2.4 Judge Assignment

| Constraint           | Detail |
|----------------------|--------|
| Permission required  | `can_forward_to_judiciary` |
| Case status          | Typically `JUDICIARY` (not enforced — flexible for pre-assignment) |
| Assignee role        | Must hold `Judge` role |
| Side effect          | Status log entry created |
| Notification         | Sent to assigned judge |

### 2.5 Exceptions Raised

| Scenario | Exception Type | HTTP Status |
|----------|----------------|-------------|
| Wrong role for assignee | `DomainError` | 400 |
| Missing permission | `PermissionDenied` | 403 |
| Wrong case status for detective assignment | `InvalidTransition` | 409 |
| Unassign with invalid field name | `DomainError` | 400 |

---

## 3. Witness Validation Rules

| Field          | Validation Rule |
|----------------|-----------------|
| `full_name`    | Required, max 255 chars |
| `phone_number` | Required, 7–15 digits, optionally prefixed with `+` |
| `national_id`  | Required, exactly 10 digits |

Witnesses cannot be added to `CLOSED` or `VOIDED` cases.

---

## 4. API Sequences

### 4.1 Officer Path (Requires Approval)

```bash
# Step 1: Officer creates a crime-scene case
curl -X POST /api/cases/ \
  -H "Authorization: Bearer <officer_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "creation_type": "crime_scene",
    "title": "Armed Robbery at 5th Avenue",
    "description": "Two armed suspects robbed a jewelry store.",
    "crime_level": 2,
    "incident_date": "2026-02-23T14:30:00Z",
    "location": "5th Avenue, Downtown LA",
    "witnesses": [
      {
        "full_name": "John Smith",
        "phone_number": "+12025551234",
        "national_id": "1234567890"
      }
    ]
  }'
# Response: 201 Created — status = "pending_approval"

# Step 2: Superior (Captain/Chief) approves the case
curl -X POST /api/cases/{case_id}/approve-crime-scene/ \
  -H "Authorization: Bearer <captain_token>"
# Response: 200 OK — status = "open"

# Step 3: Assign a detective (Sergeant/Captain)
curl -X POST /api/cases/{case_id}/assign-detective/ \
  -H "Authorization: Bearer <sergeant_token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 42}'
# Response: 200 OK — status = "investigation"

# Step 4: Assign a sergeant
curl -X POST /api/cases/{case_id}/assign-sergeant/ \
  -H "Authorization: Bearer <captain_token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 15}'
# Response: 200 OK

# Step 5: Add more witnesses later
curl -X POST /api/cases/{case_id}/witnesses/ \
  -H "Authorization: Bearer <detective_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Jane Doe",
    "phone_number": "09121234567",
    "national_id": "9876543210"
  }'
# Response: 201 Created
```

### 4.2 Chief Path (Auto-Approved)

```bash
# Step 1: Police Chief creates a crime-scene case
curl -X POST /api/cases/ \
  -H "Authorization: Bearer <chief_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "creation_type": "crime_scene",
    "title": "Serial Killer Investigation - Downtown",
    "description": "Third victim found with matching MO.",
    "crime_level": 4,
    "incident_date": "2026-02-22T08:00:00Z",
    "location": "Warehouse District, LA",
    "witnesses": []
  }'
# Response: 201 Created — status = "open" (auto-approved!)
# approved_by = chief user ID

# Step 2: Directly assign detective (no approval step needed)
curl -X POST /api/cases/{case_id}/assign-detective/ \
  -H "Authorization: Bearer <chief_token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 42}'
# Response: 200 OK — status = "investigation"
```

### 4.3 Forbidden Path (Cadet Attempt)

```bash
# Cadet tries to create a crime-scene case
curl -X POST /api/cases/ \
  -H "Authorization: Bearer <cadet_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "creation_type": "crime_scene",
    "title": "Suspicious Activity",
    "description": "Saw something odd.",
    "crime_level": 1,
    "incident_date": "2026-02-23T10:00:00Z",
    "location": "Park"
  }'
# Response: 403 Forbidden
# {"detail": "Your role is not permitted to create a crime-scene case."}
```

---

## 5. State Machine Diagram (Crime-Scene Subset)

```
[Officer/Patrol/Detective/Sergeant/Captain creates case]
              │
    ┌─────────┴─────────┐
    │ role == Chief?     │
    ├──── YES ──────────▶ OPEN  (approved_by = creator)
    └──── NO ───────────▶ PENDING_APPROVAL
                              │
                    [Superior approves]
                              │
                              ▼
                            OPEN
                              │
                    [Detective assigned]
                              │
                              ▼
                        INVESTIGATION  ◀──┐
                              │           │ [Sergeant rejects]
                    [Detective declares]  │
                              │           │
                              ▼           │
                     SUSPECT_IDENTIFIED   │
                              │           │
                              ▼           │
                      SERGEANT_REVIEW ────┘
                              │
                    [Sergeant approves]
                              │
                              ▼
                       ARREST_ORDERED
                              │
                              ▼
                        INTERROGATION
                              │
                              ▼
                       CAPTAIN_REVIEW
                         ├──────────────▶ JUDICIARY  (non-critical)
                         └──▶ CHIEF_REVIEW ──▶ JUDICIARY  (critical)
                                                    │
                                                    ▼
                                                  CLOSED
```

---

## 6. Files Modified

| File | Changes |
|------|---------|
| `backend/cases/services.py` | Implemented `create_crime_scene_case`, `approve_crime_scene_case`, `declare_suspects_identified`, `process_sergeant_review`, `forward_to_judiciary`, `add_witness`, `assign_detective`, `assign_sergeant`, `assign_captain`, `assign_judge`, `unassign_role` |
| `backend/cases/views.py` | Wired all stub endpoints to service calls; moved imports to top-level |
| `backend/cases/serializers.py` | Added `validate_phone_number` to `CaseWitnessCreateSerializer`; added `re` import |

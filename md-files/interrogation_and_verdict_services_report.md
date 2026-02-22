# Interrogation Scoring & Captain/Chief Verdict Services Report

## 1  Overview

This report documents the implementation of two interconnected features in
the **suspects** application:

| Feature | Service Class | Purpose |
|---------|---------------|---------|
| Interrogation Scoring | `InterrogationService` | CRUD for interrogation sessions with dual 1-10 guilt scores |
| Captain / Chief Verdict Gate | `VerdictService` | Verdict & approval workflow with mandatory Police Chief gate for CRITICAL cases |

Both services follow the project's **Fat Service / Skinny View** architecture.

---

## 2  Model Changes

### 2.1  New Suspect Statuses

Two new values were added to `SuspectStatus`:

| Value | Purpose |
|-------|---------|
| `PENDING_CAPTAIN_VERDICT` | Suspect awaits the Captain's guilty / innocent verdict |
| `PENDING_CHIEF_APPROVAL` | CRITICAL-level case verdict requires Police Chief sign-off |

`Suspect.status` and `SuspectStatusLog.from_status / to_status` field
`max_length` increased from **20 → 30** to accommodate the new values.

Migration: `suspects/migrations/0005_alter_suspect_status_and_more.py`

### 2.2  State Machine Additions

```
UNDER_INTERROGATION  →  PENDING_CAPTAIN_VERDICT
PENDING_CAPTAIN_VERDICT  →  UNDER_TRIAL            (non-critical)
PENDING_CAPTAIN_VERDICT  →  PENDING_CHIEF_APPROVAL  (CRITICAL)
PENDING_CHIEF_APPROVAL   →  UNDER_TRIAL             (chief approves)
PENDING_CHIEF_APPROVAL   →  UNDER_INTERROGATION     (chief rejects)
```

---

## 3  InterrogationService

**Location:** `suspects/services.py` — class `InterrogationService`

### 3.1  Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_interrogations_for_suspect` | `(suspect_id, requesting_user)` | Returns role-scoped queryset of interrogations for one suspect |
| `get_interrogation_detail` | `(interrogation_id)` | Returns a single interrogation with `select_related` |
| `list_interrogations` | `(filters)` | General-purpose listing with optional filter kwargs |
| `create_interrogation` | `(suspect_id, validated_data, requesting_user)` | Creates an interrogation record with score validation and automatic status transition |

### 3.2  Scoring Rules

- Both `detective_guilt_score` and `sergeant_guilt_score` must be integers
  in the range **1 – 10** (enforced at model and serializer levels).
- Scores are assigned by the Detective and Sergeant linked to the
  suspect's parent `Case`.

### 3.3  Create Workflow

```
1. Permission check: CAN_CONDUCT_INTERROGATION
2. Status guard: suspect must be ARRESTED or UNDER_INTERROGATION
3. Score validation: 1 ≤ score ≤ 10
4. Create Interrogation record
5. Auto-transition suspect → UNDER_INTERROGATION (if ARRESTED)
6. Log transition in SuspectStatusLog
7. Notify Captain about new interrogation
```

---

## 4  VerdictService

**Location:** `suspects/services.py` — class `VerdictService`

### 4.1  Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `submit_captain_verdict` | `(actor, suspect_id, verdict, notes)` | Captain renders guilty/innocent verdict |
| `process_chief_approval` | `(actor, suspect_id, decision, notes)` | Police Chief approves / rejects CRITICAL case verdicts |

### 4.2  Captain Verdict Flow

```
1. Permission check: CAN_RENDER_VERDICT + role == Captain
2. Lock suspect row (select_for_update)
3. Guard: status == PENDING_CAPTAIN_VERDICT
4. Read case.crime_level
5a. If CRITICAL → status = PENDING_CHIEF_APPROVAL
    → Notify all Police Chiefs
5b. Else → status = UNDER_TRIAL
    → Notify Detective & Sergeant
6. Save verdict + notes → SuspectStatusLog
```

### 4.3  Chief Approval Flow

```
1. Permission check: CAN_APPROVE_CRITICAL_CASE + role == Police Chief
2. Lock suspect row (select_for_update)
3. Guard: status == PENDING_CHIEF_APPROVAL
4a. Decision == "approve"
    → status = UNDER_TRIAL
    → Notify Captain + Detective
4b. Decision == "reject"
    → notes are mandatory (validated in serializer)
    → status = UNDER_INTERROGATION
    → Notify Captain + Detective
5. Save decision + notes → SuspectStatusLog
```

---

## 5  API Endpoints

### 5.1  Interrogation Endpoints (InterrogationViewSet)

| Method | URL | Action | Response |
|--------|-----|--------|----------|
| GET | `/api/suspects/{id}/interrogations/` | list | 200 — array of `InterrogationListSerializer` |
| POST | `/api/suspects/{id}/interrogations/` | create | 201 — `InterrogationDetailSerializer` |
| GET | `/api/suspects/{id}/interrogations/{pk}/` | retrieve | 200 — `InterrogationDetailSerializer` |

### 5.2  Verdict Endpoints (SuspectViewSet actions)

| Method | URL | Action | Request Body |
|--------|-----|--------|-------------|
| POST | `/api/suspects/{id}/captain-verdict/` | captain_verdict | `{"verdict": "guilty\|innocent", "notes": "..."}` |
| POST | `/api/suspects/{id}/chief-approval/` | chief_approval | `{"decision": "approve\|reject", "notes": "..."}` |

Both verdict endpoints return **200** with `SuspectDetailSerializer` on
success, **400** for validation / domain errors, **403** for permission
errors.

---

## 6  Serializers

| Serializer | Purpose |
|------------|---------|
| `InterrogationListSerializer` | Compact list view (detective/sergeant names resolved) |
| `InterrogationDetailSerializer` | Full detail view including suspect name |
| `InterrogationCreateSerializer` | Input validation — `min_value=1, max_value=10` on score fields |
| `CaptainVerdictSerializer` | `verdict` (guilty/innocent), `notes` (required) |
| `ChiefApprovalSerializer` | `decision` (approve/reject), `notes` (required on reject) |

---

## 7  Notification Events

Four new event types registered in `core/domain/notifications.py`:

| Event Key | Triggered When | Recipients |
|-----------|---------------|------------|
| `chief_approval_required` | Captain verdicts a CRITICAL case | Police Chiefs |
| `captain_verdict_applied` | Captain verdicts a non-CRITICAL case | Detective, Sergeant |
| `chief_verdict_approved` | Chief approves a CRITICAL case | Captain, Detective |
| `chief_verdict_rejected` | Chief rejects a CRITICAL case | Captain, Detective |

---

## 8  Permission Map Refactoring

`_TRANSITION_PERMISSION_MAP` values changed from plain permission
strings to `(app_label, codename)` tuples.  This allows cross-app
permission lookups — specifically `CasesPerms.CAN_APPROVE_CRITICAL_CASE`
(defined in the **cases** app) is now referenced by the suspects state
machine without string-interpolation hacks.

```python
# Before
(FROM, TO): "permission_codename"

# After
(FROM, TO): ("app_label", "permission_codename")
```

The `transition_status` method in `ArrestAndWarrantService` was updated
to unpack both components when checking `user.has_perm()`.

---

## 9  Sequence Diagram — CRITICAL Case

```
Detective/Sergeant        Captain           Police Chief
      │                     │                     │
      │  create_interrogation                     │
      │────────────────────►│                     │
      │  (scores 1-10)      │                     │
      │                     │                     │
      │                     │  submit_captain_verdict
      │                     │  (crime_level=CRITICAL)
      │                     │────────────────────►│
      │                     │  PENDING_CHIEF_APPROVAL│
      │                     │                     │
      │                     │  process_chief_approval
      │                     │◄────────────────────│
      │                     │  (approve/reject)   │
      │                     │                     │
      │  UNDER_TRIAL (approve)                    │
      │  or UNDER_INTERROGATION (reject)          │
```

---

## 10  Files Changed

| File | Changes |
|------|---------|
| `suspects/models.py` | Added `PENDING_CAPTAIN_VERDICT`, `PENDING_CHIEF_APPROVAL`; widened `max_length` |
| `suspects/services.py` | Implemented `InterrogationService` (4 methods), `VerdictService` (2 methods), updated state machine |
| `suspects/serializers.py` | Implemented list/detail serializer methods, added `CaptainVerdictSerializer`, `ChiefApprovalSerializer` |
| `suspects/views.py` | Wired `InterrogationViewSet` (list/create/retrieve), added `captain_verdict` & `chief_approval` actions |
| `suspects/migrations/0005_*` | Auto-generated migration for status field changes |
| `core/domain/notifications.py` | Added 4 notification event types |

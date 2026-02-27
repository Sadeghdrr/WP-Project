# Cases App — API Design Report

**App:** `cases`  
**Branch:** `feat/cases-api-drafts`  
**Status:** Structural Draft — reviewed & bug-fixed (business logic not yet implemented — all methods raise `NotImplementedError`)

---

## 1. Endpoint Reference Table

| # | HTTP Method | URL | Purpose | Access Level |
|---|-------------|-----|---------|--------------|
| 1 | `GET` | `/api/cases/` | List cases visible to the authenticated user, with optional filters | Role-scoped (see §3.1) |
| 2 | `POST` | `/api/cases/` | Create a case via complaint or crime-scene path | Citizen (complaint) / Police rank (crime-scene) |
| 3 | `GET` | `/api/cases/{id}/` | Full case detail with nested complainants, witnesses, status log, calculations | Role-scoped |
| 4 | `PATCH` | `/api/cases/{id}/` | Partial update of mutable metadata fields (title, description, incident_date, location) | Case owner / Admin |
| 5 | `DELETE` | `/api/cases/{id}/` | Hard-delete a case | Admin only |
| 6 | `POST` | `/api/cases/{id}/submit/` | Complainant submits draft for Cadet review | Primary complainant |
| 7 | `POST` | `/api/cases/{id}/resubmit/` | Complainant edits and re-submits a returned complaint | Primary complainant |
| 8 | `POST` | `/api/cases/{id}/cadet-review/` | Cadet approve/reject a complaint case | `can_review_complaint` (Cadet) |
| 9 | `POST` | `/api/cases/{id}/officer-review/` | Officer approve/reject a case forwarded by the Cadet | `can_approve_case` (Officer) |
| 10 | `POST` | `/api/cases/{id}/approve-crime-scene/` | Superior approves a crime-scene case (PENDING_APPROVAL → OPEN) | `can_approve_case` (Officer+) |
| 11 | `POST` | `/api/cases/{id}/declare-suspects/` | Detective declares suspects identified → auto-escalates to Sergeant review | Assigned detective |
| 12 | `POST` | `/api/cases/{id}/sergeant-review/` | Sergeant approves arrest or rejects and returns to Detective | Assigned sergeant (`can_change_case_status`) |
| 13 | `POST` | `/api/cases/{id}/forward-judiciary/` | Captain/Chief forwards the case to the judiciary system | `can_forward_to_judiciary` |
| 14 | `POST` | `/api/cases/{id}/transition/` | Generic centralized state-transition endpoint (for steps without a dedicated action) | Permission validated against `ALLOWED_TRANSITIONS` map |
| 15 | `POST` | `/api/cases/{id}/assign-detective/` | Assign a detective → moves case to INVESTIGATION | `can_assign_detective` (Sergeant/Captain) |
| 16 | `DELETE` | `/api/cases/{id}/unassign-detective/` | Remove the assigned detective | `can_assign_detective` |
| 17 | `POST` | `/api/cases/{id}/assign-sergeant/` | Assign a sergeant to the case | `can_assign_detective` |
| 18 | `POST` | `/api/cases/{id}/assign-captain/` | Assign a captain to the case | `can_assign_detective` |
| 19 | `POST` | `/api/cases/{id}/assign-judge/` | Assign a judge to the case | `can_forward_to_judiciary` |
| 20 | `GET` | `/api/cases/{id}/complainants/` | List all complainants on the case | Role-scoped |
| 21 | `POST` | `/api/cases/{id}/complainants/` | Add an additional complainant to the case | `add_casecomplainant` / Admin |
| 22 | `POST` | `/api/cases/{id}/complainants/{c_pk}/review/` | Cadet approves/rejects an individual complainant | `can_review_complaint` (Cadet) |
| 23 | `GET` | `/api/cases/{id}/witnesses/` | List witnesses on the case | Role-scoped |
| 24 | `POST` | `/api/cases/{id}/witnesses/` | Add a witness to the case | Case write access |
| 25 | `GET` | `/api/cases/{id}/status-log/` | Immutable audit trail of all status transitions (newest first) | Role-scoped |
| 26 | `GET` | `/api/cases/{id}/calculations/` | Computed tracking threshold and reward values | Role-scoped |

> **Access Levels** are enforced in `services.py`, not in views or serializers.
> All endpoints require `IsAuthenticated`.

---

## 2. 16-Stage Case Workflow State Machine

The case lifecycle consists of **16 statuses** split across two creation paths that converge into a shared investigation pipeline.

### 2.1 Complaint Registration Path

```
COMPLAINT_REGISTERED
  │
  ▼  [complainant submits]
CADET_REVIEW
  ├──→ OFFICER_REVIEW            [cadet approves]
  ├──→ RETURNED_TO_COMPLAINANT   [cadet rejects; rejection_count++]
  │       │
  │       ▼  [complainant edits & re-submits]
  │    CADET_REVIEW  ↺
  └──→ VOIDED                    [auto: rejection_count >= 3]

OFFICER_REVIEW
  ├──→ OPEN                      [officer approves; approved_by set]
  └──→ RETURNED_TO_CADET         [officer rejects]
          │
          ▼  [cadet re-submits to officer]
       OFFICER_REVIEW  ↺
```

### 2.2 Crime-Scene Registration Path

```
PENDING_APPROVAL
  └──→ OPEN  [one superior approves]

* If creator is Police Chief → OPEN immediately on creation (no approval needed)
```

### 2.3 Common Investigation Pipeline (after OPEN)

```
OPEN
  └──→ INVESTIGATION            [detective assigned]
          └──→ SUSPECT_IDENTIFIED  [detective declares]
                  └──→ SERGEANT_REVIEW
                          ├──→ ARREST_ORDERED      [sergeant approves]
                          └──→ INVESTIGATION ↺     [sergeant rejects; back to detective]

ARREST_ORDERED
  └──→ INTERROGATION
          └──→ CAPTAIN_REVIEW
                  ├──→ JUDICIARY        [non-critical cases]
                  └──→ CHIEF_REVIEW     [critical cases only (crime_level == 4)]
                          └──→ JUDICIARY

JUDICIARY
  └──→ CLOSED
```

### 2.4 ALLOWED_TRANSITIONS Map

Every valid `(from_status, to_status)` pair is registered in `services.py`'s `ALLOWED_TRANSITIONS` dict along with the set of permission codenames that authorize the transition (OR-logic: having any one of the listed permissions is sufficient). Transitions not present in the map are illegal and raise `ValidationError`.

### 2.5 Auto-Void Rule

When a complaint reaches **3 rejections** (`rejection_count >= MAX_REJECTION_COUNT`), the service automatically transitions it to `VOIDED` via `transition_state` — no manual step required. The `(CADET_REVIEW, VOIDED)` transition is registered in `ALLOWED_TRANSITIONS` with `can_review_complaint` permission so the delegation through `transition_state` succeeds.

### 2.6 How `transition_state` Enforces the State Machine

`CaseWorkflowService.transition_state` is the single choke-point for all status changes:

1. **Lookup** `(current_status, target_status)` in `ALLOWED_TRANSITIONS`. If absent → `ValidationError` (illegal transition).
2. **Permission check** — resolves the set of valid codenames for this edge and asserts `requesting_user.has_perm()` for at least one. If none → `PermissionError`.
3. **Extra guards** — critical-case detour (must go through `CHIEF_REVIEW`), non-blank message on rejections.
4. **Atomic write** — updates `case.status`, writes `CaseStatusLog`, dispatches notifications — all inside `@transaction.atomic`.

Role-specific methods (`submit_for_review`, `process_cadet_review`, `process_sergeant_review`, etc.) are thin wrappers that add ownership pre-checks (e.g., "only the primary complainant may call `submit_for_review`") before delegating to `transition_state`.

### 2.7 Notification Dispatch

`_dispatch_notifications` is called at the end of every `transition_state` call (inside the same transaction). It creates `core.models.Notification` records for the next actor. In a production implementation, a `post_commit` hook (or Celery `on_commit` task) would send push notifications after the transaction completes.

---

## 3. Service Layer Architecture

Seven service classes enforce a strict separation between HTTP concerns and business logic:

| Service Class | Responsibility |
|---------------|----------------|
| `CaseQueryService` | Filtered, role-scoped queryset construction for listing |
| `CaseCreationService` | Complaint and crime-scene case creation flows |
| `CaseWorkflowService` | Central state-machine gateway + role-specific convenience methods |
| `CaseAssignmentService` | Assign/unassign detective, sergeant, captain, judge |
| `CaseComplainantService` | Add and review complainants |
| `CaseWitnessService` | Add witnesses to crime-scene cases |
| `CaseCalculationService` | Reward & tracking-threshold formula computation |

### 3.1 Role-Scoped Query Strategy (`CaseQueryService`)

The list endpoint is scoped by role before applying explicit filters:

| Role | Visible Cases |
|------|---------------|
| Complainant / Base User | Cases where they are a complainant |
| Cadet | Cases in `COMPLAINT_REGISTERED` or `CADET_REVIEW` |
| Officer | Cases in `OFFICER_REVIEW` or above |
| Detective | Cases where `assigned_detective == user` |
| Sergeant | Cases where `assigned_sergeant == user` or detective cases under supervision |
| Captain / Chief / Admin | All cases (unrestricted) |
| Judge | Cases in `JUDICIARY` or `CLOSED` assigned to them |

**Implementation note:** `CaseListSerializer` expects a `complainant_count` annotation on the queryset. The service must annotate accordingly:
```python
.annotate(complainant_count=Count("complainants"))
```

---

## 4. Formula Calculations

### 4.1 Most-Wanted Tracking Threshold

From project-doc §4.7 Note 1:

$$\text{threshold} = \max(L_j) \times \max(D_i)$$

At the single-case level:

$$\text{threshold} = \text{crime\_level} \times \text{days\_since\_creation}$$

Where:
- $L_j$ = `case.crime_level` (integer 1–4 from `CrimeLevel`)
- $D_i$ = days elapsed since `case.created_at` (proxy until suspects app provides exact wanted timestamp)

### 4.2 Bounty Reward

From project-doc §4.7 Note 2:

$$\text{reward} = \max(L_j) \times \max(D_i) \times 20{,}000{,}000 \text{ Rials}$$

At the single-case level:

$$\text{reward} = \text{threshold} \times 20{,}000{,}000$$

### 4.3 API Response Shape

```json
{
  "crime_level_degree": 3,
  "days_since_creation": 45,
  "tracking_threshold": 135,
  "reward_rials": 2700000000
}
```

### 4.4 Most-Wanted Page Aggregation

The per-case threshold from this service is an input to the Most-Wanted ranking computed in the `suspects` app. The suspects app will query `max(threshold across all open cases for this suspect)` by calling `CaseCalculationService.calculate_tracking_threshold(case)` for each relevant case.

---

## 5. Serializer Inventory

| Serializer | Purpose | Direction |
|------------|---------|-----------|
| `CaseFilterSerializer` | Validates query-parameter filters for listing | Read (input) |
| `CaseListSerializer` | Compact list-page representation with summary counts | Read (output) |
| `CaseDetailSerializer` | Full case detail with nested complainants, witnesses, status log, calculations | Read (output) |
| `CaseStatusLogSerializer` | Audit trail entry | Read (output, nested) |
| `CaseComplainantSerializer` | Complainant junction record | Read (output, nested) |
| `CaseWitnessSerializer` | Witness record | Read (output, nested) |
| `CaseCalculationsSerializer` | Formula computation results | Read (output, nested + standalone) |
| `ComplaintCaseCreateSerializer` | Complaint-path case creation | Write (input) |
| `CrimeSceneCaseCreateSerializer` | Crime-scene-path case creation (with nested witnesses) | Write (input) |
| `CaseUpdateSerializer` | Partial metadata update (title, description, incident_date, location) | Write (input) |
| `CaseWitnessCreateSerializer` | Witness input for add-witness endpoint | Write (input) |
| `CaseTransitionSerializer` | Generic transition request (target_status + optional message) | Write (input) |
| `CadetReviewSerializer` | Cadet review decision (approve/reject + message) | Write (input) |
| `OfficerReviewSerializer` | Officer review decision | Write (input) |
| `SergeantReviewSerializer` | Sergeant review decision | Write (input) |
| `AssignPersonnelSerializer` | Generic personnel assignment (user_id) | Write (input) |
| `AddComplainantSerializer` | Add complainant (user_id) | Write (input) |
| `ComplainantReviewSerializer` | Cadet approves/rejects individual complainant | Write (input) |
| `ResubmitComplaintSerializer` | Complainant edits before re-submission | Write (input) |

---

## 6. Filter Parameters

`GET /api/cases/` supports the following query parameters (validated by `CaseFilterSerializer`):

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by `CaseStatus` value |
| `crime_level` | integer | Filter by `CrimeLevel` degree (1–4) |
| `detective` | integer | Filter by assigned detective user PK |
| `creation_type` | string | `"complaint"` or `"crime_scene"` |
| `created_after` | date | ISO 8601 date lower bound on `created_at` |
| `created_before` | date | ISO 8601 date upper bound on `created_at` |
| `search` | string | Free-text search on `title` and `description` |

---

## 7. Bugs Found & Fixed During Review

| # | File | Bug Description | Fix Applied |
|---|------|-----------------|-------------|
| 1 | `backend/urls.py` | Cases URLs were **not registered** in the main URL configuration — all `/api/cases/` endpoints would return 404 | Added `path('api/', include('cases.urls'))` |
| 2 | `cases/views.py` | `CaseStatusLogSerializer` and `CaseComplainantSerializer` were referenced in action docstrings / implementation contracts but **not imported** — would cause `NameError` when methods are implemented | Added both to the import block |
| 3 | `cases/services.py` | `(CADET_REVIEW, VOIDED)` transition was **missing** from `ALLOWED_TRANSITIONS` — `process_cadet_review`'s auto-void logic delegates to `transition_state`, which requires the transition key to exist in the map; without it, the 3rd rejection would raise `ValidationError` instead of voiding the case | Added `(CaseStatus.CADET_REVIEW, CaseStatus.VOIDED): {CasesPerms.CAN_REVIEW_COMPLAINT}` to the map |

---

## 8. File Inventory

| File | Role |
|------|------|
| `backend/cases/models.py` | Data models — Case, CaseComplainant, CaseWitness, CaseStatusLog (unchanged) |
| `backend/cases/serializers.py` | 19 Request/Response serializers (existing draft, reviewed) |
| `backend/cases/services.py` | 7 service classes with full contracts (existing draft, VOIDED transition added) |
| `backend/cases/views.py` | Thin CaseViewSet with 26 endpoints (existing draft, missing imports added) |
| `backend/cases/urls.py` | DefaultRouter registration (existing, reviewed) |
| `backend/backend/urls.py` | Main URL config — cases route added |
| `md-files/cases_api_report.md` | This document |

---

## 9. Dependencies

No new dependencies required. The cases app uses only:
- `djangorestframework` (already in `requirements.txt`)
- `core.models.TimeStampedModel` and `core.permissions_constants.CasesPerms` (internal)

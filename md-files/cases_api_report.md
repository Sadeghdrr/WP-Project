# Cases App — API Design Report

**App:** `cases`
**Branch:** `feat/cases-api-drafts`
**Status:** Structural Draft (business logic not yet implemented)

---

## 1. Endpoint Reference Table

| # | HTTP Method | URL | Purpose | Access Level |
|---|-------------|-----|---------|--------------|
| 1 | `GET` | `/api/cases/` | List cases visible to the requesting user (role-scoped + filtered) | All authenticated users (role-scoped) |
| 2 | `POST` | `/api/cases/` | Create a new case (complaint or crime-scene path, determined by `creation_type`) | Authenticated users / Police ranks |
| 3 | `GET` | `/api/cases/{id}/` | Retrieve full case detail with nested complainants, witnesses, logs, and formula fields | Role-scoped visibility |
| 4 | `PATCH` | `/api/cases/{id}/` | Partial update of mutable metadata (title, description, incident_date, location) | Case owner / Admin |
| 5 | `DELETE` | `/api/cases/{id}/` | Hard-delete a case (admin only) | Admin |
| 6 | `POST` | `/api/cases/{id}/submit/` | Complainant submits draft complaint for Cadet review (`COMPLAINT_REGISTERED → CADET_REVIEW`) | Primary complainant |
| 7 | `POST` | `/api/cases/{id}/resubmit/` | Complainant edits & re-submits a returned case (`RETURNED_TO_COMPLAINANT → CADET_REVIEW`) | Primary complainant |
| 8 | `POST` | `/api/cases/{id}/cadet-review/` | Cadet approves (`→ OFFICER_REVIEW`) or rejects (`→ RETURNED_TO_COMPLAINANT` / `VOIDED`) a complaint | Cadet (`CAN_REVIEW_COMPLAINT`) |
| 9 | `POST` | `/api/cases/{id}/officer-review/` | Officer approves (`→ OPEN`) or rejects (`→ RETURNED_TO_CADET`) a cadet-forwarded case | Officer (`CAN_APPROVE_CASE`) |
| 10 | `POST` | `/api/cases/{id}/approve-crime-scene/` | Superior approves a crime-scene case (`PENDING_APPROVAL → OPEN`) | Officer and above (`CAN_APPROVE_CASE`) |
| 11 | `POST` | `/api/cases/{id}/declare-suspects/` | Detective declares suspects identified; escalates to Sergeant (`INVESTIGATION → SUSPECT_IDENTIFIED → SERGEANT_REVIEW`) | Assigned Detective |
| 12 | `POST` | `/api/cases/{id}/sergeant-review/` | Sergeant approves arrest (`→ ARREST_ORDERED`) or rejects with message (`→ INVESTIGATION`) | Assigned Sergeant |
| 13 | `POST` | `/api/cases/{id}/forward-judiciary/` | Captain/Chief forwards solved case to judiciary; handles CHIEF_REVIEW detour for critical cases | Captain (`CAN_FORWARD_TO_JUDICIARY`), Chief (`CAN_APPROVE_CRITICAL_CASE`) |
| 14 | `POST` | `/api/cases/{id}/transition/` | **Generic centralized transition** for remaining pipeline steps (e.g., `ARREST_ORDERED→INTERROGATION`, `INTERROGATION→CAPTAIN_REVIEW`, `JUDICIARY→CLOSED`) | Role-based (permission resolved from transition map) |
| 15 | `POST` | `/api/cases/{id}/assign-detective/` | Assign a detective to an open case; triggers `OPEN → INVESTIGATION` | Sergeant/Captain (`CAN_ASSIGN_DETECTIVE`) |
| 16 | `DELETE` | `/api/cases/{id}/unassign-detective/` | Remove the assigned detective | Sergeant/Captain/Admin |
| 17 | `POST` | `/api/cases/{id}/assign-sergeant/` | Assign a sergeant to the case | Captain/Admin |
| 18 | `POST` | `/api/cases/{id}/assign-captain/` | Assign a captain to the case | Admin/Chief |
| 19 | `POST` | `/api/cases/{id}/assign-judge/` | Assign a judge to the case (used at judiciary referral stage) | Captain/Chief (`CAN_FORWARD_TO_JUDICIARY`) |
| 20 | `GET` | `/api/cases/{id}/complainants/` | List all complainants linked to a case | Role-scoped |
| 21 | `POST` | `/api/cases/{id}/complainants/` | Add an additional complainant to an existing case | Officer/Admin |
| 22 | `POST` | `/api/cases/{id}/complainants/{c_pk}/review/` | Cadet approves or rejects an individual complainant's information | Cadet (`CAN_REVIEW_COMPLAINT`) |
| 23 | `GET` | `/api/cases/{id}/witnesses/` | List all witnesses linked to a case | Role-scoped |
| 24 | `POST` | `/api/cases/{id}/witnesses/` | Add a witness (crime-scene cases) | Officer and above |
| 25 | `GET` | `/api/cases/{id}/status-log/` | Read-only chronological audit trail of all status transitions | Role-scoped (all involved parties) |
| 26 | `GET` | `/api/cases/{id}/calculations/` | Return computed reward amount and tracking threshold for this case | All authenticated users |

> **Note:** All endpoints require `IsAuthenticated`. Fine-grained permission checks (ownership, role hierarchy) are enforced exclusively in `services.py`, *not* in views or serializers.

---

## 2. Workflow & State-Machine Architecture

### 2.1 The 16-Stage Flow Modelled as a State Machine

The `CaseStatus` model field represents the node in the state machine. Each legal edge between nodes is encoded in the `ALLOWED_TRANSITIONS` dictionary in `services.py`:

```python
ALLOWED_TRANSITIONS: dict[tuple[str, str], set[str]] = {
    (from_status, to_status): {required_permission_codenames},
    ...
}
```

#### Complaint Creation Path

```
COMPLAINT_REGISTERED
  └─[complainant submits]──► CADET_REVIEW
        ├─[cadet rejects, +rejection_count]──► RETURNED_TO_COMPLAINANT
        │     └─[complainant edits & resubmits]──► CADET_REVIEW (↺)
        │   * 3rd rejection ──────────────────────► VOIDED (auto)
        └─[cadet approves]──► OFFICER_REVIEW
              ├─[officer rejects]──► RETURNED_TO_CADET
              │     └─[cadet resubmits]──► OFFICER_REVIEW (↺)
              └─[officer approves]──► OPEN
```

#### Crime-Scene Path

```
PENDING_APPROVAL
  └─[superior approves (1 required)]──► OPEN
  * Police Chief registers → already OPEN (no approval needed)
```

#### Common Investigation Pipeline (shared by both paths after OPEN)

```
OPEN
  └─[detective assigned]──► INVESTIGATION
        └─[detective identifies suspects]──► SUSPECT_IDENTIFIED
              └─[auto-escalate]──► SERGEANT_REVIEW
                    ├─[sergeant rejects + message]──► INVESTIGATION (↺)
                    └─[sergeant approves]──► ARREST_ORDERED
                          └──► INTERROGATION
                                └──► CAPTAIN_REVIEW
                                      ├─[non-critical]──► JUDICIARY
                                      └─[critical only]──► CHIEF_REVIEW
                                                                └──► JUDICIARY
                                                                        └──► CLOSED
```

### 2.2 The Rejection Counter & Auto-Void

The `rejection_count` field on `Case` is incremented exclusively inside `CaseWorkflowService.process_cadet_review`. After each increment, the service checks:

```python
if case.rejection_count >= MAX_REJECTION_COUNT:   # 3
    transition_state(case, VOIDED, requesting_user, message)
```

This means the complainant has **three total attempts** before the case is permanently voided. The `VOIDED` transition is not in `ALLOWED_TRANSITIONS` as a manual option — it is only reachable via this auto-trigger path, preventing accidental voiding.

### 2.3 How `transition_state` Enforces the State Machine

`CaseWorkflowService.transition_state` is the single choke-point for all status changes:

1. **Lookup** `(current_status, target_status)` in `ALLOWED_TRANSITIONS`. If absent → `ValidationError` (illegal transition).
2. **Permission check** — resolves the set of valid codenames for this edge and asserts `requesting_user.has_perm()` for at least one. If none → `PermissionError`.
3. **Extra guards** — critical-case detour (must go through `CHIEF_REVIEW`), non-blank message on rejections.
4. **Atomic write** — updates `case.status`, writes `CaseStatusLog`, dispatches notifications — all inside `@transaction.atomic`.

Role-specific methods (`submit_for_review`, `process_cadet_review`, `process_sergeant_review`, etc.) are thin wrappers that add ownership pre-checks (e.g., "only the primary complainant may call `submit_for_review`") before delegating to `transition_state`.

### 2.4 Notification Dispatch

`_dispatch_notifications` is called at the end of every `transition_state` call (inside the same transaction). It creates `core.models.Notification` records for the next actor. In a production implementation, a `post_commit` hook (or Celery `*_on_commit` task) would send push notifications after the transaction completes.

---

## 3. Math Formulas — Calculation & Exposure

### 3.1 Definitions (project-doc §4.7)

| Symbol | Meaning |
|--------|---------|
| $L_j$ | Crime level degree of case $j$: `1` = Level 3, `2` = Level 2, `3` = Level 1, `4` = Critical |
| $D_i$ | Maximum days suspect $i$ has been in "Wanted" status on any **open** case |

**Tracking Threshold (Most-Wanted Score):**

$$\text{threshold} = \max(L_j) \times \max(D_i)$$

**Reward Formula:**

$$\text{reward} = \max(L_j) \times \max(D_i) \times 20{,}000{,}000 \text{ Rials}$$

### 3.2 Where the Calculations Live

All formula math is isolated inside `CaseCalculationService` in `cases/services.py`. **No formula logic appears in views or serializers.**

```
CaseCalculationService
├── calculate_tracking_threshold(case) → int
│     degree = case.crime_level          ← L_j (integer 1–4 from CrimeLevel)
│     days   = (today - case.created_at).days  ← D_i proxy
│     return degree * days
│
├── calculate_reward(case) → int
│     return calculate_tracking_threshold(case) * 20_000_000
│
└── get_calculations_dict(case) → dict
      {
        "crime_level_degree":  <int>,
        "days_since_creation": <int>,
        "tracking_threshold":  <int>,
        "reward_rials":        <int>,
      }
```

> **Important note on `D_i`:** The formula ultimately requires days per *suspect*, computed across suspects. The current implementation uses `days_since_case_creation` as an approximation. Once the `suspects` app exposes `Suspect.wanted_since`, `calculate_tracking_threshold` will be updated to query `max(suspect.days_wanted for suspect in case.suspects.all())`.

### 3.3 How the Frontend Consumes the Formulas

There are two exposure points:

1. **`GET /api/cases/{id}/calculations/`** — A dedicated read-only endpoint that returns the four values as a flat JSON object. Ideal for a "Case Stats" sidebar widget.

2. **Inside `CaseDetailSerializer`** — A `SerializerMethodField` named `calculations` calls `CaseCalculationService.get_calculations_dict(obj)` and nests the result. This means the full case detail endpoint already includes the formulas with zero extra API calls — the Next.js page can render everything from a single `GET /api/cases/{id}/`.

### 3.4 Most-Wanted Page Aggregation

The per-case threshold from this service is an input to the Most-Wanted ranking computed in the `suspects` app. The suspects app will receive `max(threshold across all open cases for this suspect)` by calling `CaseCalculationService.calculate_tracking_threshold(case)` for each relevant case.

---

## 4. Filter Parameters Reference

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

## 5. File Inventory

| File | Role |
|------|------|
| `backend/cases/models.py` | Existing data models (unchanged) |
| `backend/cases/serializers.py` | Request/Response serializers, filter serializers, action request bodies |
| `backend/cases/services.py` | Fat service layer — state machine, workflow, assignment, calculations |
| `backend/cases/views.py` | Thin `CaseViewSet` — 26 endpoints via standard CRUD + `@action` methods |
| `backend/cases/urls.py` | DRF `DefaultRouter` registration |
| `md-files/cases_api_report.md` | This document |

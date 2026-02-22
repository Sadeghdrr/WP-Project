# Gap Analysis Report

> **Scope**: Django REST Framework backend vs. `project-doc.md` requirements  
> **Date**: Auto-generated  
> **Status**: All source code across 6 apps inspected; every finding is evidence-based.

---

## Executive Summary

The codebase has a **well-designed structural scaffold** — models are fully defined, URLs are routed, service / view / serializer layers exist for every app, and a comprehensive RBAC system is in place. However, **almost no business logic is implemented**. Every service method, every serializer validation, and every view handler (except login) raises `NotImplementedError`. Beyond the stub issue, there are several architectural gaps, a missing URL registration, a reward-formula inconsistency, no tests, no Docker configuration, no payment-gateway integration, and missing Swagger examples.

### By-the-Numbers

| Metric                                       | Count                                          |
| -------------------------------------------- | ---------------------------------------------- |
| Fully implemented service methods            | 3 (all in `accounts`)                          |
| Stub service methods (`NotImplementedError`) | ~85+                                           |
| Fully implemented view actions               | 1 (`LoginView.post`)                           |
| Stub view actions                            | ~60+                                           |
| Fully implemented serializer validations     | 1 (`CustomTokenObtainPairSerializer.validate`) |
| Stub serializer validations                  | ~40+                                           |
| Tests written                                | 0                                              |
| Docker configuration                         | Empty file                                     |

---

## Table of Contents

1. [CRITICAL — URL Registration](#1-critical--url-registration)
2. [CRITICAL — Service Layer (NotImplementedError Stubs)](#2-critical--service-layer-notimplementederror-stubs)
3. [CRITICAL — View Layer (NotImplementedError Stubs)](#3-critical--view-layer-notimplementederror-stubs)
4. [CRITICAL — Serializer Layer (NotImplementedError Stubs)](#4-critical--serializer-layer-notimplementederror-stubs)
5. [Database and Infrastructure](#5-database-and-infrastructure)
6. [Data Model Gaps](#6-data-model-gaps)
7. [Authentication and Registration](#7-authentication-and-registration)
8. [RBAC and Permissions](#8-rbac-and-permissions)
9. [Case Workflow](#9-case-workflow)
10. [Evidence Registration](#10-evidence-registration)
11. [Suspects, Interrogation, and Trials](#11-suspects-interrogation-and-trials)
12. [Bounty System](#12-bounty-system)
13. [Bail and Payments](#13-bail-and-payments)
14. [Detective Board](#14-detective-board)
15. [Dashboard, Search, and Reporting](#15-dashboard-search-and-reporting)
16. [Notifications](#16-notifications)
17. [Swagger / API Documentation](#17-swagger--api-documentation)
18. [Testing](#18-testing)
19. [Docker](#19-docker)
20. [Settings and Middleware](#20-settings-and-middleware)
21. [Summary Matrix](#21-summary-matrix)

---

## 1. CRITICAL — URL Registration

| #   | Issue                                                                                                                                                                                                                                                                      | Location                                                 | Requirement                                                        | Action Required                                                                     |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| 1.1 | **`suspects` app URLs are NOT registered** in `backend/urls.py`. The main URL configuration includes `accounts`, `evidence`, `board`, `core`, and `cases` but **omits `suspects`**. All suspect, interrogation, trial, bail, and bounty-tip endpoints will return **404**. | `backend/urls.py` — only 5 `path()` entries, no suspects | §4.4–§4.9 require suspect CRUD, interrogation, trial, bounty, bail | Add `path('api/', include('suspects.urls'))` to `urlpatterns` in `backend/urls.py`. |

---

## 2. CRITICAL — Service Layer (NotImplementedError Stubs)

Every service method below is structurally defined with detailed docstrings and "Implementation Contract" comments but raises `NotImplementedError`. These are the **core business logic** required by the project-doc.

### 2.1 Accounts App (`accounts/services.py` — 666 lines)

| #     | Service Class             | Method                                                                                                                 | Requirement                                                                       | Pts Impact |
| ----- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ---------- |
| 2.1.1 | `UserRegistrationService` | `register_user()`                                                                                                      | §4.1 — user registration with username, password, email, phone, name, national_id | 100        |
| 2.1.2 | `AuthenticationService`   | `authenticate()`                                                                                                       | §4.1 — login via username/national_id/phone/email + password                      | 100        |
| 2.1.3 | `UserManagementService`   | `list_users()`, `get_user_detail()`, `assign_role_to_user()`, `activate_user()`, `deactivate_user()`                   | §2.2, §4.1 — admin manages users/roles                                            | 200        |
| 2.1.4 | `RoleManagementService`   | `list_roles()`, `create_role()`, `get_role_detail()`, `update_role()`, `delete_role()`, `assign_permissions_to_role()` | §2.2 — "without changing code, admin must be able to add/delete/modify roles"     | 150        |
| 2.1.5 | `CurrentUserService`      | `get_profile()`, `update_profile()`                                                                                    | §4.1 — user can view/edit own profile                                             | —          |
| 2.1.6 | (module-level)            | `list_all_permissions()`                                                                                               | RBAC — enumerate available permissions for role assignment UI                     | —          |

**Note**: `AuthenticationService.resolve_user()` and `generate_tokens()` ARE implemented. `LoginView.post()` works.

### 2.2 Cases App (`cases/services.py` — 1159 lines)

| #     | Service Class            | Method                                                                                                                                                                            | Requirement                                                 | Pts Impact |
| ----- | ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ---------- |
| 2.2.1 | `CaseCreationService`    | `create_complaint_case()`                                                                                                                                                         | §4.2.1 — complainant registers complaint                    | 100        |
| 2.2.2 | `CaseCreationService`    | `create_crime_scene_case()`                                                                                                                                                       | §4.2.2 — police rank registers crime scene                  | 100        |
| 2.2.3 | `CaseWorkflowService`    | `transition_state()`                                                                                                                                                              | §4.2–§4.6 — state machine for 16+ case statuses             | 400        |
| 2.2.4 | `CaseWorkflowService`    | `submit_for_review()`, `cadet_review()`, `officer_review()`, `approve_crime_scene()`, `sergeant_review()`, `declare_suspects()`, `forward_to_judiciary()`, `resubmit_complaint()` | §4.2, §4.4, §4.5, §4.6 — role-specific workflow transitions | 400        |
| 2.2.5 | `CaseAssignmentService`  | `assign_detective()`, `unassign_detective()`, `assign_sergeant()`, `assign_captain()`, `assign_judge()`                                                                           | §4.4, §4.5, §4.6 — personnel assignment                     | 200        |
| 2.2.6 | `CaseComplainantService` | `add_complainant()`, `review_complainant()`                                                                                                                                       | §4.2.1 — multiple complainants, cadet review                | 100        |
| 2.2.7 | `CaseWitnessService`     | `add_witness()`                                                                                                                                                                   | §4.2.2 — witness recording with phone/national_id           | 100        |
| 2.2.8 | `CaseCalculationService` | `get_case_calculations()`                                                                                                                                                         | §4.7 — computed fields for most-wanted formula              | 300        |
| 2.2.9 | `CaseQueryService`       | `get_filtered_queryset()`, `get_case_detail()`                                                                                                                                    | §5.6 — role-scoped case listing and detail                  | 200        |

**Note**: The `ALLOWED_TRANSITIONS` dict IS defined and looks correct (covers all 16 statuses with permission-gated transitions).

### 2.3 Evidence App (`evidence/services.py` — 755 lines)

| #     | Service Class               | Method                                                             | Requirement                                        | Pts Impact |
| ----- | --------------------------- | ------------------------------------------------------------------ | -------------------------------------------------- | ---------- |
| 2.3.1 | `EvidenceQueryService`      | `get_filtered_queryset()`, `get_evidence_detail()`                 | §4.3, §5.8 — filtered listing                      | 100        |
| 2.3.2 | `EvidenceProcessingService` | `process_new_evidence()`, `update_evidence()`, `delete_evidence()` | §4.3.1–§4.3.5 — polymorphic create/update per type | 100        |
| 2.3.3 | `MedicalExaminerService`    | `verify_biological_evidence()`, `register_forensic_result()`       | §4.3.2 — coroner verifies bio evidence             | 100        |
| 2.3.4 | `EvidenceFileService`       | `list_files()`, `upload_file()`                                    | §4.3.1, §4.3.2 — media attachments                 | 100        |
| 2.3.5 | `ChainOfCustodyService`     | `get_chain_of_custody()`                                           | Evidence audit trail                               | —          |

### 2.4 Suspects App (`suspects/services.py` — 1238 lines)

| #     | Service Class             | Method                                                                                                              | Requirement                                                          | Pts Impact |
| ----- | ------------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- | ---------- |
| 2.4.1 | `SuspectProfileService`   | `create_suspect()`, `update_suspect()`, `get_most_wanted_list()`, `get_filtered_queryset()`, `get_suspect_detail()` | §4.4, §4.7 — suspect CRUD + most-wanted                              | 100        |
| 2.4.2 | `ArrestAndWarrantService` | `approve_or_reject_suspect()`, `issue_arrest_warrant()`, `execute_arrest()`, `transition_status()`                  | §4.4, §4.5 — suspect approval/arrest workflow                        | 100        |
| 2.4.3 | `InterrogationService`    | `create_interrogation()`, `list_interrogations()`, `get_interrogation_detail()`                                     | §4.5 — detective+sergeant guilt scoring 1–10                         | 100        |
| 2.4.4 | `TrialService`            | `create_trial()`, `list_trials()`, `get_trial_detail()`                                                             | §4.6 — judge records verdict + punishment                            | 100        |
| 2.4.5 | `BountyTipService`        | `submit_tip()`, `officer_review_tip()`, `detective_verify_tip()`, `lookup_reward()`                                 | §4.8 — citizen tip → officer review → detective verify → reward code | 100        |
| 2.4.6 | `BailService`             | `create_bail()`, `process_payment()`, `list_bails()`, `get_bail_detail()`                                           | §4.9 — bail/fine payment                                             | 200        |

### 2.5 Board App (`board/services.py` — 614 lines)

| #     | Service Class            | Method                                                                              | Requirement                                      | Pts Impact |
| ----- | ------------------------ | ----------------------------------------------------------------------------------- | ------------------------------------------------ | ---------- |
| 2.5.1 | `BoardWorkspaceService`  | `get_or_create_board()`, `get_board_snapshot()`                                     | §4.4, §5.4 — detective board per case            | 200        |
| 2.5.2 | `BoardItemService`       | `add_item()`, `update_item_position()`, `batch_update_positions()`, `remove_item()` | §5.4 — drag-drop placement of evidence/documents | 200        |
| 2.5.3 | `BoardConnectionService` | `add_connection()`, `remove_connection()`, `list_connections()`                     | §5.4 — red lines between items                   | 200        |
| 2.5.4 | `BoardNoteService`       | `create_note()`, `update_note()`, `delete_note()`, `list_notes()`                   | §5.4 — free-form notes on board                  | 200        |

### 2.6 Core App (`core/services.py` — 634 lines)

| #     | Service Class                 | Method            | Requirement                                          | Pts Impact |
| ----- | ----------------------------- | ----------------- | ---------------------------------------------------- | ---------- |
| 2.6.1 | `DashboardAggregationService` | `get_stats()`     | §5.1, §5.3 — role-aware dashboard statistics         | 200        |
| 2.6.2 | `GlobalSearchService`         | `search()`        | §5.6 — unified search across cases/suspects/evidence | —          |
| 2.6.3 | `SystemConstantsService`      | `get_constants()` | Frontend dropdowns: crime levels, statuses, roles    | —          |

---

## 3. CRITICAL — View Layer (NotImplementedError Stubs)

Every view action below is defined but raises `NotImplementedError`.

### 3.1 Accounts Views (`accounts/views.py` — 519 lines)

| Method                                                                                    | Endpoint                         | Requirement              |
| ----------------------------------------------------------------------------------------- | -------------------------------- | ------------------------ |
| `RegisterView.create()`                                                                   | `POST /api/accounts/register/`   | §4.1                     |
| `MeView.get()` / `MeView.patch()`                                                         | `GET/PATCH /api/accounts/me/`    | §4.1 — user profile      |
| `UserViewSet.list()` / `.retrieve()` / `.assign_role()` / `.activate()` / `.deactivate()` | `/api/accounts/users/`           | §2.2 — admin user mgmt   |
| `RoleViewSet` (all CRUD + `assign_permissions`)                                           | `/api/accounts/roles/`           | §2.2 — dynamic role CRUD |
| `PermissionListView.get_queryset()`                                                       | `GET /api/accounts/permissions/` | RBAC UI                  |

**Implemented**: `LoginView.post()` — works correctly with `CustomTokenObtainPairSerializer`.

### 3.2 Cases Views (`cases/views.py` — 540 lines)

All 18 actions are stubs: `list`, `create`, `retrieve`, `partial_update`, `destroy`, `submit`, `resubmit`, `cadet_review`, `officer_review`, `approve_crime_scene`, `sergeant_review`, `declare_suspects`, `forward_judiciary`, `transition`, `assign_detective`, `unassign_detective`, `assign_sergeant`, `assign_captain`, `assign_judge`, `complainants` (list/create), `review_complainant`, `witnesses` (list/create), `status_log`, `calculations`.

### 3.3 Evidence Views (`evidence/views.py` — 529 lines)

All 8 actions are stubs: `list`, `create`, `retrieve`, `partial_update`, `destroy`, `verify`, `link_case`, `unlink_case`, `files` (list/upload), `chain_of_custody`.

### 3.4 Suspects Views (`suspects/views.py` — 984 lines)

All actions across 5 ViewSets are stubs: `SuspectViewSet` (list/create/retrieve/partial_update + approve/issue-warrant/arrest/transition-status/most-wanted), `InterrogationViewSet` (list/create/retrieve), `TrialViewSet` (list/create/retrieve), `BailViewSet` (list/create/retrieve/pay), `BountyTipViewSet` (list/create/retrieve + review/verify/lookup-reward).

### 3.5 Board Views (`board/views.py` — 448 lines)

All actions are stubs: board retrieve/snapshot, item CRUD + batch-update, connection CRUD, note CRUD.

### 3.6 Core Views (`core/views.py` — 200 lines)

`DashboardStatsView.get()`, `GlobalSearchView.get()`, and `SystemConstantsView.get()` all call their respective services, which raise `NotImplementedError`. The views themselves are structurally complete (e.g., `GlobalSearchView` validates `q`, `category`, `limit` params properly), but will fail because the service layer is not implemented.

---

## 4. CRITICAL — Serializer Layer (NotImplementedError Stubs)

### 4.1 Accounts Serializers (`accounts/serializers.py` — 479 lines)

| Serializer                        | Stub Method                                                        | Impact                             |
| --------------------------------- | ------------------------------------------------------------------ | ---------------------------------- |
| `RegisterRequestSerializer`       | `validate()` — needs to enforce unique constraints, password rules | Registration will fail             |
| `RoleDetailSerializer`            | `get_permissions_display()`                                        | Role detail response incomplete    |
| `RoleAssignPermissionsSerializer` | `validate_permission_ids()`                                        | Cannot assign permissions to roles |
| `AssignRoleSerializer`            | `validate_role_id()`                                               | Cannot assign role to user         |
| `MeUpdateSerializer`              | `validate_email()`, `validate_phone_number()`                      | Profile update validation missing  |
| `TokenResponseSerializer`         | `get_user()`                                                       | Login response may be incomplete   |
| `PermissionSerializer`            | `get_full_codename()`                                              | Permission listing incomplete      |

**Implemented**: `CustomTokenObtainPairSerializer.validate()` — correctly injects role, hierarchy, and permissions into JWT.

### 4.2 Cases Serializers (`cases/serializers.py` — 582 lines)

`CaseFilterSerializer.validate()`, `ComplaintCaseCreateSerializer.validate()`, `CrimeSceneCaseCreateSerializer.validate()`, `CaseUpdateSerializer.validate()`, all workflow serializer `validate()` methods — all stubs.

### 4.3 Evidence Serializers (`evidence/serializers.py`)

`EvidencePolymorphicCreateSerializer` and all type-specific serializer `validate()` methods — stubs.

### 4.4 Suspects Serializers (`suspects/serializers.py` — 1309 lines)

All `validate()` methods across 20+ serializers — stubs.

### 4.5 Board Serializers (`board/serializers.py` — 499 lines)

`GenericObjectRelatedField.to_representation()` / `to_internal_value()` and all serializer `validate()` methods — stubs.

---

## 5. Database and Infrastructure

| #   | Issue                                         | Location                                                     | Requirement                                                 | Action Required                                                                                                             |
| --- | --------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| 5.1 | **SQLite3 in use** instead of PostgreSQL      | `settings.py` L93 — `'ENGINE': 'django.db.backends.sqlite3'` | §2.3 — "PostgreSQL as the recommended database"             | Switch `DATABASES` to PostgreSQL (`django.db.backends.postgresql`) with `psycopg2-binary` in `requirements.txt`.            |
| 5.2 | **`db.sqlite3` committed** to repository      | Root `backend/` directory                                    | Best practice                                               | Add `db.sqlite3` to `.gitignore`, remove from VCS.                                                                          |
| 5.3 | **No `MEDIA_ROOT` serving** in dev URL config | `backend/urls.py` — no `static(settings.MEDIA_URL, ...)`     | Evidence files, suspect photos require file upload/download | Add `if settings.DEBUG: urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` to `backend/urls.py`. |

---

## 6. Data Model Gaps

| #   | Issue                                                                                                                                                                              | Location                                               | Requirement                                                                      | Action Required                                                                                                                                                |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 6.1 | **No `Warrant` model** exists. `ArrestAndWarrantService.issue_arrest_warrant()` references warrant logic but has no model to persist warrant data (reason, issued_by, issued_at).  | `suspects/models.py` — no Warrant class                | §4.4 — "Sergeant issues arrest warrants"                                         | Either add a `Warrant` model or add warrant fields (`warrant_reason`, `warrant_issued_by`, `warrant_issued_at`) directly to `Suspect`.                         |
| 6.2 | **`reward_amount` multiplier inconsistency** — `Suspect.reward_amount` property uses `10_000_000` (10M) but `CaseCalculationService._REWARD_MULTIPLIER` uses `20_000_000` (20M).   | `suspects/models.py` L249 vs `cases/services.py` L1125 | §4.7 Note 2 — formula was an embedded image, exact multiplier unclear            | Standardize to a single value. Best to define `REWARD_MULTIPLIER` as a constant in one place (e.g., `core/constants.py`) and reference it from both locations. |
| 6.3 | **`CaseComplainant.status` uses plain `ComplainantStatus` choices** but the Cadet approval/rejection workflow (§4.2.1) requires tracking _who_ reviewed and _when_.                | `cases/models.py` L246–L263                            | §4.2.1 — cadet approves/rejects each complainant                                 | Fields `reviewed_by` and timestamps exist. Acceptable as-is.                                                                                                   |
| 6.4 | **No `Notification` CRUD endpoints** — `Notification` model is defined in `core/models.py` but no views/serializers/urls expose notification management (list, mark-read, delete). | `core/urls.py` — only has dashboard, search, constants | §4.4 — "a notification must be sent to the Detective" when new evidence is added | Add notification endpoints: `GET /api/core/notifications/`, `PATCH .../mark-read/`, etc.                                                                       |
| 6.5 | **`BountyTip.suspect` is nullable** — allows tips without linking to either suspect or case, which may not match the requirement that tips are "regarding a case or a suspect."    | `suspects/models.py` L390–L395                         | §4.8 — "registers information regarding a case or a suspect"                     | Add validation (in service or serializer) that at least one of `suspect` or `case` must be provided.                                                           |
| 6.6 | **No `ChainOfCustody` model** — `ChainOfCustodyService` is referenced in evidence views but there's no model to store the audit trail.                                             | `evidence/services.py`, `evidence/views.py`            | Evidence integrity tracking                                                      | Either create a `CustodyEntry` model or derive the chain from `CaseStatusLog` / Django's built-in `LogEntry`.                                                  |

---

## 7. Authentication and Registration

| #   | Issue                                                                                                                                                                                     | Location                                          | Requirement                                                                               | Action Required                                                                                  |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| 7.1 | **Registration endpoint is a stub** — `RegisterView.create()` raises `NotImplementedError`.                                                                                               | `accounts/views.py`                               | §4.1 — user creates account with username, password, email, phone, full name, national_id | Implement `UserRegistrationService.register_user()` and wire it through `RegisterView.create()`. |
| 7.2 | **Login works** (only implemented flow). Multi-field auth via `MultiFieldAuthBackend` correctly supports username/national_id/phone/email. JWT token includes role/hierarchy/permissions. | `accounts/backends.py`, `accounts/serializers.py` | §4.1                                                                                      | ✅ Complete.                                                                                     |
| 7.3 | **No token refresh endpoint** in `accounts/urls.py` — `TokenRefreshView` is imported but verify there's a corresponding URL pattern.                                                      | `accounts/urls.py`                                | JWT best practice — access tokens expire in 30min                                         | Verify `token/refresh/` path exists (it does per the URLs file).                                 |
| 7.4 | **Default role assignment on registration** — the registration service contract says "assign Base User role" but implementation is missing.                                               | `accounts/services.py` L95–L160                   | §4.1 — "every user creates an account with a 'base user' role"                            | Ensure `register_user()` sets `role` to the "Base User" `Role` instance.                         |

---

## 8. RBAC and Permissions

| #   | Issue                                                                                                                                                                                                                                                   | Location                                   | Requirement                                                                                                                                           | Action Required                                                                                                                        |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| 8.1 | **RBAC model design is sound** — `Role` with M2M to `Permission`, `User.has_perm()` overridden, `setup_rbac` command is idempotent.                                                                                                                     | `accounts/models.py`, `setup_rbac.py`      | §2.2 — dynamic role management without code changes                                                                                                   | ✅ Design is correct.                                                                                                                  |
| 8.2 | **Custom workflow permissions are NOT mapped to all required roles** — e.g., `CAN_REVIEW_COMPLAINT` is assigned to Cadet and System Admin but the `ALLOWED_TRANSITIONS` in `cases/services.py` references it for `COMPLAINT_REGISTERED → CADET_REVIEW`. | `setup_rbac.py` vs `cases/services.py`     | Cross-reference all workflow permissions with role assignments                                                                                        | Audit each custom permission in `ALLOWED_TRANSITIONS` against `ROLE_PERMISSIONS_MAP` to ensure the correct roles have each permission. |
| 8.3 | **Police Chief has `CAN_FORWARD_TO_JUDICIARY`** but not `CAN_APPROVE_CRITICAL_CASE` check enforced at the service level                                                                                                                                 | `setup_rbac.py` L134 — Chiefs do have both | §3.1.7, §4.5 — "In critical crimes, the Police Chief must also approve"                                                                               | The permission mapping looks correct. Implementation in `CaseWorkflowService` (stub) must enforce this gating.                         |
| 8.4 | **Patrol Officer** lacks `CAN_APPROVE_CASE`\*\* — per §4.2.2, Patrol Officers can create crime-scene cases but the requirement for superior approval means they don't need this. Police Officer has `CAN_APPROVE_CASE` which is correct per §4.2.1.     | `setup_rbac.py` L378                       | §4.2.1                                                                                                                                                | Acceptable as-is.                                                                                                                      |
| 8.5 | **RoleManagementService CRUD is stubbed** — admin cannot actually create/modify/delete roles at runtime.                                                                                                                                                | `accounts/services.py` L323–L508           | §2.2 — "without needing to change the code, the system administrator must be able to add a new role, delete existing roles, or modify them" (150 pts) | Implement all `RoleManagementService` methods.                                                                                         |

---

## 9. Case Workflow

| #   | Issue                                                                                                                                                                                                   | Location                                                       | Requirement                                                                                       | Action Required                                                                                                                          |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 9.1 | **16-stage state machine defined but not enforced** — `ALLOWED_TRANSITIONS` maps all valid transitions with required permissions, but `CaseWorkflowService.transition_state()` is a stub.               | `cases/services.py` L1–L120                                    | §4.2–§4.6 — full case lifecycle (1100 pts combined)                                               | Implement `transition_state()` using the defined `ALLOWED_TRANSITIONS` map.                                                              |
| 9.2 | **3-rejection voiding logic not implemented** — `Case.rejection_count` field exists but no service logic increments it or auto-voids the case.                                                          | `cases/models.py` L113, `cases/services.py`                    | §4.2.1 — "If the complainant submits incomplete or false information 3 times, the case is voided" | Implement in `CaseWorkflowService.cadet_review()` — increment `rejection_count` on rejection, auto-void if ≥ 3.                          |
| 9.3 | **Crime-scene approval hierarchy not enforced** — §4.2.2 says "if the Police Chief registers it, no one's approval is needed."                                                                          | `cases/services.py`                                            | §4.2.2 — Police Chief bypass                                                                      | Implement condition check in `CaseCreationService.create_crime_scene_case()`: if creator is Police Chief, set status directly to `OPEN`. |
| 9.4 | **Cadet error message on return** — §4.2.1 says "When returning the case to the complainant, it must include an error message written by the Cadet." The `CaseStatusLog.message` field exists for this. | `cases/models.py` L327                                         | §4.2.1                                                                                            | Ensure `cadet_review()` implementation requires a message when decision is "return".                                                     |
| 9.5 | **No notification dispatch** when case status changes — §4.4 says "for each [new evidence], a notification must be sent to the Detective."                                                              | `core/models.py` — `Notification` exists but no creation logic | §4.4                                                                                              | Implement notification creation in workflow service methods (evidence added, status changed, etc.).                                      |

---

## 10. Evidence Registration

| #    | Issue                                                                                                                                                                                | Location                       | Requirement                                                         | Action Required                                                                                       |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------ | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 10.1 | **Polymorphic creation logic is stubbed** — `EvidenceProcessingService._MODEL_MAP` is defined mapping types to child model classes, but `process_new_evidence()` is not implemented. | `evidence/services.py`         | §4.3.1–§4.3.5 — 5 evidence types with type-specific fields          | Implement `process_new_evidence()` using `_MODEL_MAP` for dispatch.                                   |
| 10.2 | **XOR constraint is correctly in place** — `VehicleEvidence` has a `CheckConstraint` ensuring exactly one of `license_plate` / `serial_number` is set.                               | `evidence/models.py` L236–L244 | §4.3.3 — "license plate and serial number cannot both have a value" | ✅ Correct.                                                                                           |
| 10.3 | **Coroner verification is stubbed** — `MedicalExaminerService.verify_biological_evidence()` and `register_forensic_result()` are not implemented.                                    | `evidence/services.py`         | §4.3.2 — "examined and verified either by the coroner"              | Implement both methods with `CAN_VERIFY_EVIDENCE` / `CAN_REGISTER_FORENSIC_RESULT` permission checks. |
| 10.4 | **`EvidenceFile` upload is stubbed** — File upload endpoint exists in URL routing but `EvidenceFileService.upload_file()` raises `NotImplementedError`.                              | `evidence/services.py`         | §4.3.1 — "images, videos, or audio related to the incident"         | Implement file upload with `FileType` validation.                                                     |
| 10.5 | **Evidence `link-case` / `unlink-case` actions** are defined but have no clear requirement in the project-doc. Evidence already has a `case` FK on creation.                         | `evidence/views.py` L355–L420  | Not explicitly in project-doc                                       | Evaluate if these actions are necessary; if so, implement.                                            |
| 10.6 | **`IdentityEvidence.document_details`** uses `JSONField` — correct for the "key-value format with no fixed quantity" requirement.                                                    | `evidence/models.py` L261–L268 | §4.3.4                                                              | ✅ Correct.                                                                                           |

---

## 11. Suspects, Interrogation, and Trials

| #    | Issue                                                                                                                                                                                                                                                                                            | Location                                             | Requirement                                                                                            | Action Required                                                                                                                                              |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 11.1 | **Suspect creation flow is stubbed** — Detective identifies suspects, reports to Sergeant for approval.                                                                                                                                                                                          | `suspects/services.py`                               | §4.4 — "the Detective declares the main suspects of the case to the Sergeant"                          | Implement `SuspectProfileService.create_suspect()` with pending approval status.                                                                             |
| 11.2 | **Sergeant approval/rejection is stubbed** — confirmation/objection message back to Detective.                                                                                                                                                                                                   | `suspects/services.py` L360–L410                     | §4.4 — "If the Sergeant objects, the objection is returned as a message"                               | Implement `ArrestAndWarrantService.approve_or_reject_suspect()`.                                                                                             |
| 11.3 | **Interrogation dual-scoring is modeled correctly** — `detective_guilt_score` and `sergeant_guilt_score` both have `MinValueValidator(1)` and `MaxValueValidator(10)`.                                                                                                                           | `suspects/models.py` L284–L295                       | §4.5 — "both the Sergeant and the Detective assign a probability of the suspect's guilt from 1 to 10"  | ✅ Model is correct. Implementation is stubbed.                                                                                                              |
| 11.4 | **Captain/Chief final verdict flow for critical cases** — Captain decides, Police Chief must also approve for critical crimes. This logic is described in service docstrings but not implemented.                                                                                                | `suspects/services.py`                               | §4.5 — "In critical level crimes, the Police Chief must also approve or reject the Captain's decision" | Implement in `CaseWorkflowService` and/or `ArrestAndWarrantService` with crime_level check.                                                                  |
| 11.5 | **Trial model** — Judge records verdict + punishment (title + description). Model is correct with `verdict`, `punishment_title`, `punishment_description`.                                                                                                                                       | `suspects/models.py` L336–L371                       | §4.6                                                                                                   | ✅ Model correct. `TrialService` is stubbed.                                                                                                                 |
| 11.6 | **Judge access to full case file** — §4.6 says Judge must see "the entire case file, the evidence, and all police members involved." No dedicated endpoint aggregates this.                                                                                                                      | —                                                    | §4.6, §5.7                                                                                             | Either enhance case detail serializer to include all nested data (evidence, suspects, personnel) or create a dedicated reporting endpoint.                   |
| 11.7 | **`most_wanted_score` computation is correct** — aggregates across same `national_id`, uses `max(days_wanted_in_open_cases) × max(crime_degree_across_all_cases)`.                                                                                                                               | `suspects/models.py` L203–L237                       | §4.7 Note 1                                                                                            | ✅ Algorithm matches requirement. **BUT** no DB-level annotation possible (Python property), so ordering for large datasets will be slow.                    |
| 11.8 | **`is_most_wanted` threshold is correct** — `> 30 days` maps to "over a month."                                                                                                                                                                                                                  | `suspects/models.py` L198–L200                       | §4.7 — "Suspects who have been wanted for over a month"                                                | ✅ Correct.                                                                                                                                                  |
| 11.9 | **Suspect status state machine** — 7 statuses defined (`WANTED`, `ARRESTED`, `UNDER_INTERROGATION`, `UNDER_TRIAL`, `CONVICTED`, `ACQUITTED`, `RELEASED`). Service has a `transition_status()` method (stubbed) but the valid transitions are not explicitly defined like the case state machine. | `suspects/models.py` L34–L41, `suspects/services.py` | §4.4–§4.6                                                                                              | Define explicit suspect status transitions (e.g., `WANTED → ARRESTED → UNDER_INTERROGATION → UNDER_TRIAL → CONVICTED/ACQUITTED`, with `RELEASED` from bail). |

---

## 12. Bounty System

| #    | Issue                                                                                                                                                                                                                                                                           | Location                                               | Requirement                 | Action Required                                                                                                             |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ | --------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| 12.1 | **Full bounty workflow is modeled** — `BountyTip` with 4-stage pipeline (PENDING → OFFICER_REVIEWED → VERIFIED → REJECTED), unique_code generation, reward_amount. But all service/view logic is stubbed.                                                                       | `suspects/models.py` L382–L476, `suspects/services.py` | §4.8                        | Implement `BountyTipService` methods: `submit_tip()`, `officer_review_tip()`, `detective_verify_tip()`, `lookup_reward()`.  |
| 12.2 | **Reward lookup endpoint** — §4.8 says "all police ranks must be able to enter the person's national_id and unique_code to view the bounty amount along with the related user's information." Endpoint is planned (`POST /api/bounty-tips/lookup-reward/`) but not implemented. | `suspects/urls.py` L48, `suspects/views.py`            | §4.8                        | Implement `BountyTipViewSet.lookup_reward()` — search by `national_id` + `unique_code`, return reward amount and user info. |
| 12.3 | **`BountyTip.generate_unique_code()`** uses `uuid.uuid4().hex[:12].upper()` — 12-char hex string. This is functionally fine but could collide in theory (no retry logic).                                                                                                       | `suspects/models.py` L474                              | §4.8 — unique ID for reward | Low risk. Consider adding uniqueness retry or using full UUID.                                                              |

---

## 13. Bail and Payments

| #    | Issue                                                                                                                                                                                                                                       | Location                                               | Requirement                                                           | Action Required                                                                                                                   |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ | --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| 13.1 | **No payment gateway integration** — the Bail model exists with `amount`, `is_paid`, `payment_reference`, `paid_at` fields, and a `pay` endpoint is routed (`POST /api/suspects/{suspect_pk}/bails/{id}/pay/`), but no gateway code exists. | `suspects/models.py` L490–L542, `suspects/services.py` | §4.9 — "your system must be connected to a payment gateway" (200 pts) | Integrate with a test payment gateway (ZarinPal / IDPay / BitPay recommended in §8.7). Create payment initiation + callback flow. |
| 13.2 | **No payment callback page** — §6 says "Presence of a payment gateway callback page (using Django Templates is recommended) (100 pts)."                                                                                                     | Nowhere in codebase                                    | §6 evaluation criteria                                                | Create a Django Template-based callback view that receives gateway callback, verifies payment, updates `Bail.is_paid`.            |
| 13.3 | **Bail eligibility not enforced** — §4.9 says bail applies only to "Level 2 and Level 3 crimes suspects, as well as Level 3 criminals." No validation exists.                                                                               | `suspects/services.py`                                 | §4.9                                                                  | Implement crime-level check in `BailService.create_bail()` — reject bail for Level 1 and Critical cases.                          |
| 13.4 | **`BailService` entirely stubbed** — create, payment processing, listing, detail.                                                                                                                                                           | `suspects/services.py`                                 | §4.9                                                                  | Implement all `BailService` methods.                                                                                              |

---

## 14. Detective Board

| #    | Issue                                                                                                                                                                                                           | Location                             | Requirement                                                                       | Action Required                                                                                                                                                                 |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 14.1 | **Board model design is sound** — `DetectiveBoard` (OneToOne with Case), `BoardNote`, `BoardItem` (GenericForeignKey to any content), `BoardConnection` (from_item → to_item with label).                       | `board/models.py`                    | §4.4, §5.4                                                                        | ✅ Design is correct for detective board.                                                                                                                                       |
| 14.2 | **All board services are stubbed** — workspace, items, connections, notes.                                                                                                                                      | `board/services.py` (614 lines)      | §4.4, §5.4 — "Detective Board backend so minimal changes needed in CP2" (200 pts) | Implement all `BoardWorkspaceService`, `BoardItemService`, `BoardConnectionService`, `BoardNoteService` methods.                                                                |
| 14.3 | **Batch position update designed** — `BoardItemService.batch_update_positions()` accepts a list of `{item_id, x, y}` for drag-drop optimization. Not implemented.                                               | `board/services.py`                  | §5.4 — drag-and-drop                                                              | Implement with `bulk_update()` for performance.                                                                                                                                 |
| 14.4 | **Board export (`CAN_EXPORT_BOARD`)** — permission defined but no export endpoint exists in views or URLs. §5.4 says "it must be possible to export it as an image." This is primarily a frontend concern.      | `core/permissions_constants.py` L249 | §5.4                                                                              | Backend may only need to return a JSON snapshot. The image rendering can be done client-side (html2canvas). No backend endpoint needed unless server-side rendering is planned. |
| 14.5 | **`BoardItem` content linkage** — `GenericForeignKey` with `ALLOWED_CONTENT_TYPES` frozenset defined in serializer (evidence, suspect, case). Correct approach but serializer `to_representation()` is stubbed. | `board/serializers.py`               | §4.4 — "documents and evidence are placed on the board"                           | Implement `GenericObjectRelatedField` serializer methods.                                                                                                                       |

---

## 15. Dashboard, Search, and Reporting

| #    | Issue                                                                                                                                                                                                                        | Location                                    | Requirement                                                                                                       | Action Required                                                                                                                                              |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 15.1 | **Dashboard stats endpoint exists** but service is stubbed.                                                                                                                                                                  | `core/views.py` L40–L80, `core/services.py` | §5.1 — "display several statistics (at least three): total solved cases, total employees, active cases" (200 pts) | Implement `DashboardAggregationService.get_stats()` with role-aware aggregation.                                                                             |
| 15.2 | **Global search exists** — view has proper parameter validation (`q`, `category`, `limit`). Service is stubbed.                                                                                                              | `core/views.py` L85–L165                    | §5.6 — search across cases/suspects/evidence                                                                      | Implement `GlobalSearchService.search()` with cross-model Q lookups.                                                                                         |
| 15.3 | **No dedicated "General Reporting" endpoint** — §5.7 says "a complete report of every case, including creation date, evidence and testimonies, suspects, criminal, complainant(s), and the names and ranks of all involved." | No endpoint exists                          | §5.7 — "primarily for the Judge, Captain, and Police Chief"                                                       | Create a comprehensive case-report endpoint that aggregates all sub-resources into a single response. Could be a queryset parameter on the case detail view. |
| 15.4 | **System constants endpoint** works structurally but the service returns nothing.                                                                                                                                            | `core/views.py` L170–L200                   | Frontend dropdowns                                                                                                | Implement `SystemConstantsService.get_constants()` to return all TextChoices/IntegerChoices enums.                                                           |

---

## 16. Notifications

| #    | Issue                                                                                                                                                                                                                      | Location                          | Requirement                                          | Action Required                                                                                                     |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| 16.1 | **`Notification` model exists** — recipient FK, title, message, is_read, GenericForeignKey for related_object.                                                                                                             | `core/models.py`                  | §4.4 — notification to Detective when evidence added | ✅ Model correct.                                                                                                   |
| 16.2 | **No notification endpoints** — no views, serializers, or URLs for listing/reading/marking notifications.                                                                                                                  | `core/urls.py` — only 3 endpoints | §4.4                                                 | Add `NotificationViewSet` or API views: `GET /api/core/notifications/`, `PATCH .../mark-read/`, `DELETE .../{id}/`. |
| 16.3 | **No notification dispatch logic** — notifications are never created anywhere. They should be created in service methods (e.g., when evidence is added to a case, when status changes, when suspect is approved/rejected). | All services are stubs            | §4.4                                                 | When implementing services, add `Notification.objects.create(...)` calls at appropriate points.                     |

---

## 17. Swagger / API Documentation

| #    | Issue                                                                                                                                                                                                                                                                                | Location                | Requirement                                                                            | Action Required                                                                                                                                                       |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 17.1 | **drf-spectacular is installed and configured** — `SPECTACULAR_SETTINGS` with title/description/version.                                                                                                                                                                             | `settings.py` L169–L177 | §6 — "your backend must have Swagger documentation (otherwise, it will not be graded)" | ✅ Basic setup exists.                                                                                                                                                |
| 17.2 | **No Swagger URL routes** — `SpectacularAPIView`, `SpectacularSwaggerView`, `SpectacularRedocView` are not registered in `backend/urls.py`.                                                                                                                                          | `backend/urls.py`       | §6 — Swagger docs must be accessible                                                   | Add: `path('api/schema/', SpectacularAPIView.as_view(), name='schema')` and `path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui')` |
| 17.3 | **No request/response examples** — §6 evaluation says "Completeness and reliability of Swagger docs (having proper request/response examples and full descriptions) (250 pts)." Views have docstrings with example payloads but no `@extend_schema` decorators with formal examples. | All views               | §6 — 250 pts                                                                           | Add `@extend_schema(request=..., responses=..., examples=[...])` decorators to views, or use `drf-spectacular`'s `OpenApiExample` objects.                            |
| 17.4 | **All views use `viewsets.ViewSet`** (not `ModelViewSet`) — drf-spectacular cannot auto-infer schema from these. Each action needs explicit `@extend_schema` annotations for proper docs.                                                                                            | All 6 apps              | §6                                                                                     | Annotate every action method with `@extend_schema()` specifying request/response serializers.                                                                         |

---

## 18. Testing

| #    | Issue                                                                                | Location                       | Requirement                                                                                   | Action Required                                                                                                                |
| ---- | ------------------------------------------------------------------------------------ | ------------------------------ | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 18.1 | **Zero tests exist** — all `tests.py` files are empty or default Django boilerplate. | `*/tests.py` across all 6 apps | §6 — "Presence of at least 5 tests in two different apps (at least 10 tests total) (100 pts)" | Write at minimum 5 tests each in 2 different apps. Recommended: accounts (auth/registration) and cases (workflow transitions). |

---

## 19. Docker

| #    | Issue                                                                | Location                        | Requirement                                                                | Action Required                                                                                                               |
| ---- | -------------------------------------------------------------------- | ------------------------------- | -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| 19.1 | **`docker-compose.yaml` is empty** — no Docker configuration exists. | `docker-compose.yaml` (0 bytes) | §6 — "Dockerizing the backend project and its utilized services (200 pts)" | Create `Dockerfile` for the Django backend, add PostgreSQL service to `docker-compose.yaml`, configure environment variables. |
| 19.2 | **No `Dockerfile`** exists for the backend.                          | `backend/` directory            | §6                                                                         | Create a `Dockerfile` with Python 3.12+, `pip install -r requirements.txt`, `gunicorn` or `daphne` for serving.               |

---

## 20. Settings and Middleware

| #    | Issue                                                                                                                                                                                                            | Location                                      | Requirement                       | Action Required                                                                                                                                             |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 20.1 | **CORS middleware not in `MIDDLEWARE`** — `corsheaders` is in `INSTALLED_APPS` but `corsheaders.middleware.CorsMiddleware` is not listed in the `MIDDLEWARE` array. CORS will NOT work for frontend connections. | `settings.py` L56–L64                         | Frontend needs CORS               | Add `'corsheaders.middleware.CorsMiddleware'` as the **first** item in `MIDDLEWARE`. Add `CORS_ALLOWED_ORIGINS` or `CORS_ALLOW_ALL_ORIGINS = True` for dev. |
| 20.2 | **`SECRET_KEY` is hardcoded and insecure** — `'django-insecure-...'`.                                                                                                                                            | `settings.py` L23                             | Security best practice            | Move to environment variable. Critical for Docker deployment.                                                                                               |
| 20.3 | **`DEBUG = True` and `ALLOWED_HOSTS = ['*']`** — insecure for production.                                                                                                                                        | `settings.py` L26–L28                         | Production readiness              | Use environment variables; restrict `ALLOWED_HOSTS` in production.                                                                                          |
| 20.4 | **No Swagger/Schema URLs** registered                                                                                                                                                                            | `backend/urls.py`                             | §6 — Swagger required for grading | See item 17.2.                                                                                                                                              |
| 20.5 | **`Pillow` missing from `requirements.txt`** (likely) — `Suspect.photo` uses `ImageField` which requires Pillow.                                                                                                 | `suspects/models.py` L115, `requirements.txt` | ImageField dependency             | Add `Pillow` to `requirements.txt`.                                                                                                                         |

---

## 21. Summary Matrix

### By Evaluation Criteria (§6 — 4750 pts total)

| Criterion                      | Points | Status  | Notes                                                                                  |
| ------------------------------ | ------ | ------- | -------------------------------------------------------------------------------------- |
| Logical/precise entity models  | 750    | 🟢 ~90% | Models are well-designed. Missing Warrant model, reward multiplier inconsistency.      |
| Appropriate endpoints          | 1000   | 🟡 ~70% | URL routing is complete for 5/6 apps. Suspects URLs missing. All views are stubs.      |
| Necessary CRUD APIs            | 250    | 🟡 ~60% | All CRUD defined but not implemented. Missing notification CRUD.                       |
| REST principles                | 100    | 🟢 ~80% | Good REST design. `ViewSet` actions follow standard patterns.                          |
| Access level verification      | 250    | 🔴 ~10% | RBAC model + permissions defined. Zero enforcement (all service stubs).                |
| Flow endpoint implementation   | 400    | 🔴 0%   | All workflow methods raise `NotImplementedError`.                                      |
| RBAC implementation            | 200    | 🟡 ~50% | Model + `setup_rbac` command complete. No runtime enforcement.                         |
| Role modifiability             | 150    | 🔴 ~20% | Model supports it. CRUD services are stubs.                                            |
| Registration & Login           | 100    | 🟡 ~50% | Login works. Registration is stubbed.                                                  |
| Case Creation                  | 100    | 🔴 0%   | Stubbed.                                                                               |
| Evidence Registration          | 100    | 🔴 0%   | Stubbed.                                                                               |
| Case Solving (Detective Board) | 200    | 🔴 ~15% | Models complete. Services stubbed.                                                     |
| Suspect ID & Interrogation     | 100    | 🔴 0%   | Stubbed.                                                                               |
| Trial                          | 100    | 🔴 0%   | Stubbed.                                                                               |
| Suspect Status                 | 100    | 🔴 ~15% | Model properties implemented (`most_wanted_score`, `is_most_wanted`). Service stubbed. |
| Bounty                         | 100    | 🔴 0%   | Stubbed.                                                                               |
| Payment (gateway)              | 200    | 🔴 0%   | No gateway integration.                                                                |
| Aggregated statistics          | 200    | 🔴 0%   | Stubbed.                                                                               |
| Suspect/criminal ranking       | 300    | 🟡 ~30% | Model property correct. No endpoint implementation.                                    |
| Payment callback page          | 100    | 🔴 0%   | Does not exist.                                                                        |
| Docker                         | 200    | 🔴 0%   | Empty file.                                                                            |
| Swagger docs                   | 250    | 🔴 ~10% | drf-spectacular configured, no URL routes, no examples.                                |
| Tests (10 minimum)             | 100    | 🔴 0%   | Zero tests.                                                                            |
| Clean code / best practices    | 100    | 🟢 ~80% | Architecture is clean (fat models, service layer). Docstrings thorough.                |
| Reasonable app separation      | 100    | 🟢 ~90% | 6 apps is well-organized.                                                              |
| Django/DRF built-in usage      | 100    | 🟡 ~60% | Uses SimpleJWT, filters, spectacular. `ViewSet` over `ModelViewSet` adds boilerplate.  |
| Code modifiability             | 100    | 🟢 ~80% | Service layer pattern enables easy modification.                                       |

### Estimated Score: ~800–1000 / 4750 (~17–21%)

The structural foundation (models, URL routing, architecture patterns, RBAC design) is solid and accounts for the earned points. The **critical gap** is that **no business logic is implemented** — over 85 service methods, 60 view actions, and 40 serializer validations all raise `NotImplementedError`.

---

## Priority Action Plan

### Phase 1 — Blockers (must fix immediately)

1. Register `suspects` URLs in `backend/urls.py`
2. Add CORS middleware to `MIDDLEWARE` list
3. Add Swagger URL routes (`/api/schema/`, `/api/docs/`)
4. Add media file serving in dev

### Phase 2 — Core Authoring (~60% of grade)

5. Implement `accounts` services: registration, user/role CRUD
6. Implement `cases` services: both creation flows, full state machine
7. Implement `evidence` services: polymorphic CRUD, coroner verification
8. Implement `suspects` services: CRUD, approval, arrest, interrogation, trial
9. Implement `board` services: workspace, items, connections, notes
10. Implement `core` services: dashboard stats, search, constants

### Phase 3 — High-Value Items

11. Payment gateway integration (ZarinPal/IDPay) + callback page
12. Notification system: endpoints + dispatch logic in services
13. Dockerize: `Dockerfile` + `docker-compose.yaml` with PostgreSQL
14. Switch database to PostgreSQL

### Phase 4 — Polish

15. Add `@extend_schema` decorators to all views with examples
16. Write 10+ tests across 2 apps
17. Standardize `reward_amount` multiplier
18. Add `Warrant` model or fields
19. Security: environment-variable secrets, restrict `ALLOWED_HOSTS`

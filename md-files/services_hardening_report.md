# Services Hardening Report

**Branch:** `chore/services-hardening`  
**Date:** 2025-07-15  
**Scope:** Backend service layer — stub removal, exception mapping, wiring verification, ORM optimization.

---

## 1. Unblocked Endpoints

Four `raise NotImplementedError` stubs were the only remaining blockers across the entire backend. All have been replaced with working implementations.

| App | Location | Endpoint / Method | Fix Applied |
|-----|----------|--------------------|-------------|
| `cases` | `CaseViewSet.partial_update` | `PATCH /cases/{id}/` | Wired to `CaseUpdateSerializer(case, data=…, partial=True)` + `.save()`. |
| `cases` | `CaseViewSet.destroy` | `DELETE /cases/{id}/` | Added `system_admin`-only gate via `get_user_role_name()`, then `case.delete()`. |
| `suspects` | `BailViewSet.pay` | `POST /suspects/{id}/bail/{bail_id}/pay/` | Wired to new `BailService.process_bail_payment()` with full exception handling. |
| `suspects` | `BailService.process_bail_payment` | _(service)_ | Implemented: sets `is_paid`, `payment_reference`, `paid_at`; auto-transitions CONVICTED suspect to RELEASED. |

---

## 2. Exception Handling Strategy

### 2.1 Domain Exception Hierarchy

```
DomainError (400)
├── PermissionDenied (403)
├── NotFound (404)
└── Conflict (409)
    └── InvalidTransition (409)
```

All domain exceptions flow through the global handler registered in settings:

```python
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "core.domain.exception_handler.domain_exception_handler",
}
```

The handler maps each exception to the correct HTTP status. Views that **don't** catch exceptions explicitly still get correct HTTP codes because the global handler processes them.

### 2.2 Explicit Exception Ordering Fixes

Seven view methods in `suspects/views.py` had misordered `except` blocks that would swallow `NotFound` (a subclass of `DomainError`) as a generic 400 instead of returning 404. Fixed ordering:

```python
except PermissionDenied as exc:   # 403
    ...
except NotFound as exc:           # 404
    ...
except InvalidTransition as exc:  # 409
    ...
except DomainError as exc:        # 400 (catch-all)
    ...
```

| ViewSet | Method | Issue | Fix |
|---------|--------|-------|-----|
| `SuspectViewSet` | `issue_warrant` | `NotFound` swallowed as 400 | Reordered: `NotFound` → 404 before `DomainError` → 400 |
| `SuspectViewSet` | `arrest` | Same | Same |
| `SuspectViewSet` | `transition_status` | Same | Same |
| `InterrogationViewSet` | `captain_verdict` | Same | Same |
| `InterrogationViewSet` | `chief_approval` | Same | Same |
| `BountyTipViewSet` | `review` | `InvalidTransition` grouped with `DomainError` as 400 | Separated: `InvalidTransition` → 409 |
| `BountyTipViewSet` | `verify` | Same | Same |

### 2.3 Missing Exception Catches Added

| ViewSet | Method | Missing | Fix |
|---------|--------|---------|-----|
| `BountyTipViewSet` | `create` | `PermissionDenied` | Added `PermissionDenied` → 403 catch |
| `BountyTipViewSet` | `lookup_reward` | `PermissionDenied` | Added `PermissionDenied` → 403 catch |

### 2.4 Coverage Summary

92 total service calls across 6 apps. After this hardening pass:

- **72 calls** rely on the global exception handler (correct — no explicit catches needed).
- **20 calls** have explicit `try/except` blocks in views (all verified for proper ordering).
- **0 calls** have mismatched or missing exception handling.

---

## 3. End-to-End Wiring Verification

### 3.1 Flow A — Complaint Case Lifecycle

Verified: `CaseViewSet.create(complaint)` → `CaseViewSet.submit` → `CaseViewSet.cadet_review` → `CaseViewSet.officer_review`

| Step | View → Serializer → Service | `request.user` | Kwargs Match | Status |
|------|------------------------------|-----------------|--------------|--------|
| 1. Create complaint | `ComplaintCaseCreateSerializer` → `CaseCreationService.create_complaint_case(validated_data, request.user)` | ✅ | ✅ | PASS |
| 2. Submit for review | _(no body)_ → `CaseWorkflowService.submit_for_review(case, request.user)` | ✅ | ✅ | PASS |
| 3. Cadet review | `CadetReviewSerializer` → `CaseWorkflowService.process_cadet_review(case, decision, message, request.user)` | ✅ | ✅ | PASS |
| 4. Officer review | `OfficerReviewSerializer` → `CaseWorkflowService.process_officer_review(case, decision, message, request.user)` | ✅ | ✅ | PASS |

### 3.2 Flow B — Suspect → Arrest → Interrogation

Verified: `SuspectViewSet.create` → `SuspectViewSet.approve` → `SuspectViewSet.issue_warrant` → `SuspectViewSet.arrest` → `InterrogationViewSet.create`

| Step | View → Serializer → Service | `request.user` | Kwargs Match | Status |
|------|------------------------------|-----------------|--------------|--------|
| 1. Create suspect | `SuspectCreateSerializer` → `SuspectProfileService.create_suspect(validated_data, request.user)` | ✅ | ✅ | PASS |
| 2. Approve suspect | `SuspectApprovalSerializer` → `ArrestAndWarrantService.approve_or_reject_suspect(pk, request.user, decision, message)` | ✅ | ✅ | PASS |
| 3. Issue warrant | `ArrestWarrantSerializer` → `ArrestAndWarrantService.issue_arrest_warrant(pk, request.user, reason, priority)` | ✅ | ✅ | PASS* |
| 4. Execute arrest | `ArrestPayloadSerializer` → `ArrestAndWarrantService.execute_arrest(pk, request.user, location, notes, override)` | ✅ | ✅ | PASS |
| 5. Create interrogation | `InterrogationCreateSerializer` → `InterrogationService.create_interrogation(suspect_pk, validated_data, request.user)` | ✅ | ✅ | PASS |

> **\*Note (Step 3):** The `priority` field is accepted by the serializer and passed to the service but is only used in the notification payload — the `Warrant` model has no `priority` column, so the value is not persisted. This is a known schema gap, not a wiring defect.

---

## 4. Performance Improvements (ORM)

### 4.1 Changes Applied

| File | Method | Before | After | Impact |
|------|--------|--------|-------|--------|
| `core/services.py` | `_get_top_wanted_suspects` | Python loop calling `suspect.most_wanted_score` (N+1: 1 query/suspect) | Delegates to `SuspectProfileService.get_most_wanted_list()` which annotates `computed_score` / `computed_reward` at DB level | **Eliminates N+1** — from O(N) queries to 1 |
| `suspects/services.py` | `detective_verify_tip` | `SuspectModel.objects.filter(…)` without `select_related` → `s.reward_amount` triggers per-suspect query via `case.crime_level` | Added `select_related("case")` | **Eliminates N+1** on reward fallback path |
| `evidence/services.py` | `get_evidence_detail` | 4 sequential OneToOne accessor queries to resolve child type | Added `select_related("testimonyevidence", "biologicalevidence", "vehicleevidence", "identityevidence")` → single LEFT JOIN | **Saves 1–4 queries** per detail fetch |
| `evidence/services.py` | `get_chain_of_custody` (lookup) | Bare `Evidence.objects.get(pk=…)` with no FK pre-load | Added `select_related("registered_by").prefetch_related("files")` | **Saves 2 queries** |
| `evidence/services.py` | `get_custody_trail` | Accessed `evidence.registered_by`, `files`, `biologicalevidence.verified_by` without ensuring they were loaded | Added defensive re-fetch with `select_related` + `prefetch_related`; biological path loads `verified_by` | **Saves up to 4 queries** per trail build |
| `cases/services.py` | `transition_state` | `select_for_update()` without FK pre-load; `_dispatch_notifications` then accesses 5 FK fields | Added `select_related("created_by", "assigned_detective", "assigned_sergeant", "assigned_captain", "assigned_judge")` | **Saves up to 5 queries** per transition |
| `cases/services.py` | `get_case_report` | `select_related("created_by", …)` without `__role`; `_user_summary()` accesses `.role.name` on every user | Added `__role` suffix to all user FK chains + all `Prefetch` querysets | **Eliminates ~30 extra queries** on report endpoint |
| `core/services.py` | `list_notifications` | Bare filter without `select_related` | Added `select_related("content_type")` | **Saves 1 query per notification** (GenericFK resolution) |

### 4.2 Already Well-Optimized (No Changes Needed)

The following were audited and found to already have proper `select_related`/`prefetch_related`:

- `CaseQueryService.get_filtered_queryset()` / `get_case_detail()`
- `SuspectProfileService.get_filtered_queryset()` / `get_suspect_detail()`
- `EvidenceQueryService.get_filtered_queryset()`
- `BoardWorkspaceService.get_full_board_graph()` / `list_boards()`
- `InterrogationService.get_interrogations_for_suspect()` / `list_interrogations()`
- `TrialService.list_trials()` / `get_trial_detail()`
- `DashboardAggregationService._get_recent_activity()`
- `MedicalExaminerService.get_pending_verifications()`
- `ChainOfCustodyService.get_chain_of_custody()`
- `UserManagementService.list_users()`

---

## 5. Files Modified

| File | Changes |
|------|---------|
| `cases/views.py` | `partial_update`, `destroy` — unblocked |
| `suspects/views.py` | `BailViewSet.pay` — unblocked; 7 exception reorders; 2 missing catches added |
| `suspects/services.py` | `BailService.process_bail_payment` — implemented; `detective_verify_tip` — `select_related("case")` |
| `cases/services.py` | `transition_state` — `select_related` on lock; `get_case_report` — `__role` across all FK chains |
| `evidence/services.py` | `get_evidence_detail` — child type `select_related`; `get_chain_of_custody` — `select_related`; `get_custody_trail` — defensive re-fetch |
| `core/services.py` | `_get_top_wanted_suspects` — uses annotated queryset; `list_notifications` — `select_related("content_type")` |

---

## 6. Known Remaining Items (Out of Scope)

| Item | Severity | Reason |
|------|----------|--------|
| `Suspect.most_wanted_score` property fires per-instance query | Medium | Architectural — requires model-level refactor (add cached field or remove property in favor of annotation-only access). Mitigated by ensuring all hot paths use the annotated queryset instead. |
| `Warrant` model lacks `priority` column | Low | Schema gap — `ArrestWarrantSerializer` accepts `priority` but the model doesn't persist it. The value is used in notification payloads only. Requires migration to fix. |

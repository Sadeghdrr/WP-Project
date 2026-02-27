# Cases Services — Query Layer Report

**Scope:** `CaseQueryService` (list & detail) + supporting serializer / view wiring  
**Branch:** `feat/cases-services`  
**Status:** Implemented — read/list access with role-scoped filtering

---

## 1. Visibility Matrix

The list and detail endpoints return **only** the cases that the requesting user's role allows. Scoping is applied **before** any explicit query-parameter filters via `core.domain.access.apply_role_filter`.

| Role | Visible Cases | Implementation |
|------|---------------|----------------|
| **Complainant** | Cases where the user is linked as a `CaseComplainant` | `qs.filter(complainants__user=user)` |
| **Base User** | Same as Complainant (own cases only) | `qs.filter(complainants__user=user)` |
| **Cadet** | Cases in `COMPLAINT_REGISTERED`, `CADET_REVIEW`, `RETURNED_TO_COMPLAINANT`, or `RETURNED_TO_CADET` | `qs.filter(status__in=CADET_VISIBLE_STATUSES)` |
| **Police Officer** | All cases **except** early complaint stages (`COMPLAINT_REGISTERED`, `CADET_REVIEW`, `RETURNED_TO_COMPLAINANT`, `VOIDED`) | `qs.exclude(status__in=OFFICER_EXCLUDED_STATUSES)` |
| **Patrol Officer** | Same as Police Officer | `qs.exclude(status__in=OFFICER_EXCLUDED_STATUSES)` |
| **Detective** | Cases where `assigned_detective == user` | `qs.filter(assigned_detective=user)` |
| **Sergeant** | Cases where `assigned_sergeant == user` **or** any case with a detective assigned | `qs.filter(Q(assigned_sergeant=u) \| Q(assigned_detective__isnull=False))` |
| **Captain** | All cases (unrestricted) | `qs` (no filter) |
| **Police Chief** | All cases (unrestricted) | `qs` (no filter) |
| **System Admin** | All cases (unrestricted) | `qs` (no filter) |
| **Judge** | Cases in `JUDICIARY` or `CLOSED` status **and** `assigned_judge == user` | `qs.filter(status__in=JUDGE_VISIBLE_STATUSES, assigned_judge=user)` |
| *Any other role* | No cases (empty queryset) | `default="none"` in `apply_role_filter` |

---

## 2. Query Optimisations

### 2.1 List Endpoint (`get_filtered_queryset`)

| Technique | Fields / Relations | Rationale |
|-----------|--------------------|-----------|
| `select_related` | `created_by`, `assigned_detective`, `assigned_sergeant`, `assigned_captain` | `CaseListSerializer` reads FK names; avoids N+1 on each row |
| `annotate` | `Count("complainants")` → `complainant_count` | `CaseListSerializer` expects annotated `complainant_count` field |
| `.distinct()` | — | Guards against row duplication from `complainants__user` join in Complainant/Base User scoping |

### 2.2 Detail Endpoint (`get_case_detail`)

| Technique | Fields / Relations | Rationale |
|-----------|--------------------|-----------|
| `select_related` | `created_by`, `approved_by`, `assigned_detective`, `assigned_sergeant`, `assigned_captain`, `assigned_judge` | Full detail page shows all personnel names |
| `prefetch_related` | `complainants` → `CaseComplainant.objects.select_related("user", "reviewed_by")` | Nested `CaseComplainantSerializer` renders `user_display` and `reviewed_by` |
| `prefetch_related` | `witnesses` | Nested `CaseWitnessSerializer` |
| `prefetch_related` | `status_logs` → `CaseStatusLog.objects.select_related("changed_by")` | Nested `CaseStatusLogSerializer` renders `changed_by_name` |

### 2.3 Filter Application

Explicit filters are applied **after** role scoping, using the following mapping:

| Query Parameter | QuerySet Filter |
|-----------------|-----------------|
| `status` | `.filter(status=value)` |
| `crime_level` | `.filter(crime_level=value)` |
| `detective` | `.filter(assigned_detective_id=value)` |
| `creation_type` | `.filter(creation_type=value)` |
| `created_after` | `.filter(created_at__date__gte=value)` |
| `created_before` | `.filter(created_at__date__lte=value)` |
| `search` | `.filter(Q(title__icontains=value) \| Q(description__icontains=value))` |

---

## 3. Shared Helpers

No new helpers were added to `core/domain/access.py`. The existing utilities were sufficient:

| Helper | Module | Usage |
|--------|--------|-------|
| `apply_role_filter(qs, user, scope_config, default)` | `core.domain.access` | Applies the `CASE_SCOPE_CONFIG` dict to scope the queryset by role |
| `get_user_role_name(user)` | `core.domain.access` | Resolves user → lowercased role name (used internally by `apply_role_filter`) |

---

## 4. Domain Exceptions

| Scenario | Exception Raised | HTTP Status |
|----------|------------------|-------------|
| Case not found or not visible to user (detail) | `core.domain.exceptions.NotFound` | 404 |

The global DRF exception handler (`core.domain.exception_handler.domain_exception_handler`) automatically maps domain exceptions to HTTP responses — no try/except needed in views.

---

## 5. Serializer Stubs Implemented

The following serializer methods were implemented to support the read layer:

| Serializer | Method | Purpose |
|------------|--------|---------|
| `CaseFilterSerializer` | `validate()` | Ensures `created_after <= created_before` |
| `CaseListSerializer` | `get_assigned_detective_name()` | Returns detective's full name |
| `CaseStatusLogSerializer` | `get_changed_by_name()` | Returns actor's full name |
| `CaseComplainantSerializer` | `get_user_display()` | Returns complainant's full name |
| `CaseDetailSerializer` | `get_calculations()` | Delegates to `CaseCalculationService.get_calculations_dict` |

---

## 6. `CaseCalculationService` (bonus — required by detail serializer)

The three calculation methods were also implemented since the detail serializer depends on them:

- `calculate_tracking_threshold(case)` → `crime_level × max(days_since_creation, 0)`
- `calculate_reward(case)` → `threshold × 20,000,000 Rials`
- `get_calculations_dict(case)` → combined dict with all four fields

---

## 7. Files Changed

| File | Change |
|------|--------|
| `backend/cases/services.py` | `CaseQueryService.get_filtered_queryset()`, `get_case_detail()` implemented; `CaseCalculationService` methods implemented; role-scope constants + config added; imports updated |
| `backend/cases/views.py` | `list()`, `retrieve()`, `_get_case()`, `_get_complainant()` implemented; domain exception imports added |
| `backend/cases/serializers.py` | Five serializer method stubs replaced with implementations |
| `md-files/cases_services_query_report.md` | This document |

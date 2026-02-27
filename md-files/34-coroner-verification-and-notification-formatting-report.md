# Step 34 — Coroner Verification Scope, Notification Formatting & Hierarchy Enforcement

**Date:** 2026-02-25
**Type:** Backend feature implementation (services, permissions, views)

---

## Objectives

| # | Feature | Status |
|---|---------|--------|
| 1 | Refactor `NotificationService` to format messages using `payload` dict and safe templates | ✅ Done |
| 2 | Make `DashboardStatsView` publicly accessible (remove authentication requirement) | ✅ Done |
| 3 | Add coroner scope rule to `CASE_SCOPE_RULES` for cases with unverified biological evidence | ✅ Done |
| 4 | Enforce rank hierarchy in `approve_crime_scene_case` (approver ≥ creator) | ✅ Done |

---

## Files Created / Changed

| File | Action | Purpose |
|------|--------|---------|
| `backend/core/domain/notifications.py` | Modified | Added `_SafeDict`, `_safe_format()`, updated `_EVENT_TEMPLATES` with `{placeholder}` templates, wired payload formatting into `NotificationService.create()` |
| `backend/core/views.py` | Modified | Changed `DashboardStatsView.permission_classes` to `[AllowAny]`, added `authentication_classes = []` |
| `backend/core/permissions_constants.py` | Modified | Added `CAN_SCOPE_CORONER_CASES` permission constant |
| `backend/cases/models.py` | Modified | Added coroner scope permission to `Case.Meta.permissions` |
| `backend/cases/services.py` | Modified | Added coroner scope rule in `CASE_SCOPE_RULES`; added hierarchy enforcement in `approve_crime_scene_case` |
| `backend/cases/migrations/0004_add_coroner_scope_permission.py` | Created | Django migration to register new `can_scope_coroner_cases` permission |
| `backend/tests/test_step34_features.py` | Created | 26 new tests covering all 4 features |
| `backend/tests/test_core_endpoints.py` | Modified | Updated 2 existing tests to align with public dashboard behaviour |

---

## Feature Details

### 1. NotificationService Payload Formatting

**Problem:** `NotificationService.create()` accepted a `payload` dict but never used it for message formatting. All notification titles and messages were static strings.

**Solution:**

- **`_SafeDict`** — A `dict` subclass whose `__missing__` method returns `"{key}"` instead of raising `KeyError`, ensuring missing placeholders are left as literal text rather than crashing.

- **`_safe_format(template, payload)`** — Uses `string.Formatter().vformat()` with `_SafeDict` to interpolate `payload` values into templates. Returns the raw template if `payload` is `None`/empty or if formatting fails for any reason.

- **`_EVENT_TEMPLATES`** — Upgraded from static strings to parameterised templates:
  ```
  "evidence_added":  ("New Evidence Added", "New evidence has been registered for case #{case_id}.")
  "case_approved":   ("Case Approved",      "Case #{case_id} has been approved by {actor_name}.")
  "bail_payment":    ("Bail Payment",        "A bail payment of {amount} has been processed for case #{case_id}.")
  ```
  18 event types now have `{placeholder}` templates.

- **Auto-injected `actor_name`** — `NotificationService.create()` auto-populates `actor_name` from `actor.get_full_name() or actor.username` if not already present in `payload`. This means any template can reference `{actor_name}` without callers needing to supply it.

- **Graceful degradation** — If `payload` is `None`, empty, or causes a formatting error, the raw template is returned unchanged. The service never raises on formatting failures.

### 2. DashboardStatsView — Public Access

**Problem:** The dashboard endpoint (`/api/dashboard/stats/`) required JWT authentication, preventing public/anonymous access to department-wide aggregate statistics.

**Solution:**

- Changed `permission_classes` from `[IsAuthenticated]` to `[AllowAny]`
- Added `authentication_classes = []` to skip JWT token processing entirely
- Updated the OpenAPI description to reflect the public access policy
- Anonymous users hit the `default="all"` fallback in `apply_permission_scope`, receiving department-wide aggregates (total cases, open cases, etc.)

### 3. Coroner Case Scope Rule

**Problem:** Coroner users had no way to see cases where biological evidence was pending their verification.

**Solution:**

- **Permission constant:** Added `CAN_SCOPE_CORONER_CASES = "can_scope_coroner_cases"` to `CasesPerms` in `core/permissions_constants.py`.

- **Model registration:** Added the permission to `Case.Meta.permissions` so Django's migration framework registers it in the database.

- **Migration:** Created `cases/migrations/0004_add_coroner_scope_permission.py` (`AlterModelOptions` on Case).

- **Scope rule:** Added a new rule in `CASE_SCOPE_RULES` between the cadet and judge rules:
  ```python
  (f"cases.{CasesPerms.CAN_SCOPE_CORONER_CASES}",
   lambda qs, u: qs.filter(
       evidences__biologicalevidence__is_verified=False,
   ).distinct()),
  ```
  This uses Django's multi-table inheritance join: `Case → Evidence (reverse: evidences) → BiologicalEvidence` to find cases with at least one unverified biological evidence item. `.distinct()` prevents duplicates when multiple bio evidence items exist.

- **Verify action:** `MedicalExaminerService.verify_biological_evidence()` already existed in `evidence/services.py` — no new code needed.

### 4. Rank Hierarchy Enforcement in `approve_crime_scene_case`

**Problem:** Any user with `CAN_APPROVE_CASE` permission could approve a crime-scene case, regardless of their rank relative to the case creator. This allowed lower-ranking officers to approve cases created by their superiors.

**Solution:** Added two guard checks to `CaseWorkflowService.approve_crime_scene_case()`:

1. **Explicit permission check:** Verifies `requesting_user.has_perm("cases.can_approve_case")` and raises `PermissionDenied` if missing.

2. **Hierarchy enforcement:**
   ```python
   approver_level = getattr(requesting_user, "hierarchy_level", 0)
   creator_level = getattr(case.created_by, "hierarchy_level", 0)
   if approver_level < creator_level:
       raise PermissionDenied(
           "Your rank is insufficient to approve a case created by a higher-ranking officer."
       )
   ```
   The `hierarchy_level` property on `User` resolves through the user's assigned `Role.hierarchy_level`. Higher numerical values indicate higher rank (e.g., Police Chief = 100, Captain = 80, Officer = 40).

---

## Test Coverage

### New Tests — `tests/test_step34_features.py` (26 tests)

| Class | Tests | Description |
|-------|-------|-------------|
| `TestSafeFormat` | 6 | Unit tests for `_safe_format()`: basic substitution, missing keys left as-is, `None` payload returns raw template, empty dict returns raw template, extra keys ignored, bad format string returns raw |
| `TestNotificationServiceFormatting` | 6 | DB integration tests: payload values appear in message, `bio_evidence_verified` template, missing keys left as placeholders, `None` payload produces raw template, unknown event type uses fallback, `actor_name` auto-injected from actor |
| `TestDashboardAnonymousAccess` | 3 | Anonymous GET returns 200, response contains aggregate stats, no user-specific data leaked |
| `TestCoronerCaseScope` | 3 | Coroner sees cases with unverified bio evidence, excludes cases where bio evidence is verified, excludes cases with only non-bio evidence |
| `TestApproveCrimeSceneHierarchy` | 8 | Captain approves Officer case (✓), equal rank approval (✓), Captain cannot approve Chief case (✗ hierarchy), Chief approves any (✓), user without permission blocked (✗), Chief auto-approves own case (✓), non-crime-scene rejected (✗), wrong status rejected (✗) |

### Updated Tests — `tests/test_core_endpoints.py` (2 tests)

| Original Test | Updated To | Reason |
|---------------|-----------|--------|
| `test_dashboard_requires_authentication` | `test_dashboard_allows_anonymous_access` | Dashboard is now public; anonymous GET should return 200 not 401 |
| `test_dashboard_detective_scope_shows_only_assigned_cases` | Updated assertions | Without auth classes, JWT is not processed; detective sees department-wide aggregates |

### Full Suite Results

```
tests/test_core_endpoints.py       — 14 passed
tests/test_notifications_flow.py   —  6 passed
tests/test_cases_crime_scene_flow.py — 16 passed
tests/test_evidence_flows.py       — 32 passed
tests/test_step34_features.py      — 26 passed
─────────────────────────────────────────────
TOTAL                                78 + 32 = 110 passed, 0 failed
```

---

## Migration

| Migration | App | Operation |
|-----------|-----|-----------|
| `cases/migrations/0004_add_coroner_scope_permission.py` | cases | `AlterModelOptions` — adds `can_scope_coroner_cases` permission to `Case.Meta.permissions` |

Dependency chain: `0003_alter_case_options` → `0004_add_coroner_scope_permission`.

---

## Design Decisions

1. **Safe formatting over f-strings** — Using `string.Formatter` with `_SafeDict` ensures that notification creation never crashes due to missing payload keys. Templates degrade gracefully by leaving `{placeholder}` literals when values are absent.

2. **`authentication_classes = []` on DashboardStatsView** — Setting this to an empty list prevents DRF from attempting JWT token validation on anonymous requests. Without this, an expired or malformed `Authorization` header would cause a 401 even though `AllowAny` is set.

3. **Coroner scope between cadet and judge** — `CASE_SCOPE_RULES` is evaluated in order (first matching permission wins). Placing the coroner rule after cadet but before judge reflects the coroner's organisational position and ensures they only see cases where their forensic expertise is needed.

4. **`getattr(user, "hierarchy_level", 0)` fallback** — Defensive coding in case a user has no `Role` assigned. Defaults to 0 (lowest rank), preventing unranked users from approving any case.

5. **No new verify endpoint** — `MedicalExaminerService.verify_biological_evidence()` was already fully implemented in `evidence/services.py` with proper permission checks, so no additional code was required for objective 3's verify action.

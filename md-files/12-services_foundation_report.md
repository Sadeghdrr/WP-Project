# Services Foundation Report

**Branch:** `feat/services-foundation`  
**Date:** February 2026  
**Scope:** Routing fixes, shared domain utilities, pytest scaffolding.

---

## 1. Routing Fix

### Problem (Before)

`backend/backend/urls.py` included only 5 apps — **`suspects` was missing**:

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
    path('api/', include('evidence.urls')),
    path('api/', include('board.urls')),
    path('api/core/', include('core.urls')),
    path('api/', include('cases.urls')),
]
```

All suspect, interrogation, trial, bail, and bounty-tip endpoints returned **404**.

### Fix (After)

Added `suspects.urls` to `urlpatterns`:

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
    path('api/', include('evidence.urls')),
    path('api/', include('board.urls')),
    path('api/core/', include('core.urls')),
    path('api/', include('cases.urls')),
    path('api/', include('suspects.urls')),   # ← NEW
]
```

### Routes now resolving

| Name | Path |
|------|------|
| `suspect-list` | `/api/suspects/` |
| `suspect-detail` | `/api/suspects/{id}/` |
| `bounty-tip-list` | `/api/bounty-tips/` |
| `bounty-tip-detail` | `/api/bounty-tips/{id}/` |
| Nested interrogations | `/api/suspects/{id}/interrogations/` |
| Nested trials | `/api/suspects/{id}/trials/` |
| Nested bails | `/api/suspects/{id}/bails/` |

---

## 2. New Shared Modules — `core.domain`

A new package `backend/core/domain/` provides cross-app utilities that all service layers should use. This keeps service implementations consistent and avoids duplicating error handling, notification logic, and transaction patterns.

### 2.1 `core.domain.exceptions`

Domain-specific exception hierarchy, **decoupled from DRF**:

| Exception | HTTP status | When to use |
|-----------|-------------|-------------|
| `DomainError` | 400 | Generic business-rule violation |
| `PermissionDenied` | 403 | User lacks required role/permission |
| `NotFound` | 404 | Resource doesn't exist or is out of scope |
| `Conflict` | 409 | Duplicate / optimistic-lock failure |
| `InvalidTransition` | 409 | State-machine transition not allowed |

**Import:**
```python
from core.domain.exceptions import InvalidTransition, PermissionDenied
```

### 2.2 `core.domain.exception_handler`

A DRF-compatible global exception handler that automatically maps domain exceptions to proper HTTP responses. Registered in `settings.py` → `REST_FRAMEWORK['EXCEPTION_HANDLER']`.

### 2.3 `core.domain.notifications`

`NotificationService.create(...)` — creates `Notification` records linked to any model via `GenericForeignKey`.

**Import:**
```python
from core.domain.notifications import NotificationService

NotificationService.create(
    actor=request.user,
    recipients=case.assigned_detective,
    event_type="evidence_added",
    payload={"case_id": case.id},
    related_object=evidence,
)
```

Supported `event_type` keys (extendable):
`evidence_added`, `case_status_changed`, `suspect_approved`, `suspect_rejected`, `interrogation_created`, `trial_created`, `bounty_tip_submitted`, `bounty_tip_verified`, `bail_payment`, `assignment_changed`, `complaint_returned`, `case_approved`, `case_rejected`.

### 2.4 `core.domain.transactions`

Concurrency-safe helpers for state transitions:

| Function | Purpose |
|----------|---------|
| `atomic_transition(instance, status_field, target_status, allowed_sources)` | Lock row → validate current status → update → save |
| `run_in_atomic(fn, *args, **kwargs)` | Execute any callable inside `transaction.atomic()` |
| `lock_for_update(model_class, pk)` | Acquire row-level lock (must be inside `atomic()`) |

**Import:**
```python
from core.domain.transactions import atomic_transition

updated_case = atomic_transition(
    instance=case,
    status_field="status",
    target_status="under_investigation",
    allowed_sources={"pending_review", "returned_for_revision"},
)
```

### 2.5 `core.domain.access`

Role-scoped queryset selectors (placeholder hooks):

| Function | Purpose |
|----------|---------|
| `get_user_role_name(user)` | Returns lowercased role name or `"system_admin"` for superusers |
| `apply_role_filter(qs, user, scope_config, default)` | Apply per-role queryset filters using a config dict |
| `require_role(user, *allowed_roles)` | Guard that raises `PermissionDenied` if role doesn't match |

Apps define their own `SCOPE_CONFIG` dict and pass it in:

```python
from core.domain.access import apply_role_filter

CASE_SCOPE_CONFIG = {
    "detective": lambda qs, u: qs.filter(assigned_detective=u),
    "sergeant":  lambda qs, u: qs.filter(assigned_sergeant=u),
    "captain":   lambda qs, u: qs.all(),
    "police_chief": lambda qs, u: qs.all(),
    "system_admin": lambda qs, u: qs.all(),
}

qs = apply_role_filter(Case.objects.all(), user, scope_config=CASE_SCOPE_CONFIG)
```

---

## 3. Pytest Scaffolding

### Files Added

| File | Purpose |
|------|---------|
| `backend/pytest.ini` | Pytest configuration (settings module, test paths) |
| `backend/conftest.py` | Shared fixtures: `api_client`, `create_user`, `auth_header` |
| `backend/tests/__init__.py` | Tests package |
| `backend/tests/test_smoke.py` | 21 smoke tests: routing, imports, exception behaviour, access helpers |

### How to Run Tests

```bash
# From backend/ directory, with virtualenv activated:

# Run all tests
python -m pytest

# Run smoke tests only
python -m pytest tests/test_smoke.py

# Run with verbose output
python -m pytest -v

# Run a specific test class
python -m pytest tests/test_smoke.py::TestURLRouting

# Run tests matching a keyword
python -m pytest -k "routing"
```

### Dependencies Added to `requirements.txt`

```
pytest>=8.0
pytest-django>=4.8
```

---

## 4. Settings Change

Registered the domain exception handler in `REST_FRAMEWORK`:

```python
REST_FRAMEWORK = {
    ...
    'EXCEPTION_HANDLER': 'core.domain.exception_handler.domain_exception_handler',
}
```

---

## 5. Assumptions

1. **No per-app business logic implemented** — only shared utilities and hooks. Each app's `services.py` will import from `core.domain.*` when implementing its own logic.
2. **Notifications are synchronous** — can be swapped to `transaction.on_commit()` or Celery later without changing the public API.
3. **Role names are matched case-insensitively** with spaces replaced by underscores (e.g. `"Police Chief"` → `"police_chief"`).
4. **Superusers are treated as `"system_admin"`** in role-scoped access helpers.
5. **`venv/` directory** was created locally for dependency installation; it is `.gitignore`d and not committed.

---

## 6. File Summary

```
Modified:
  backend/backend/urls.py           — Added suspects URL registration
  backend/backend/settings.py       — Added EXCEPTION_HANDLER to REST_FRAMEWORK
  backend/requirements.txt          — Added pytest, pytest-django

Created:
  backend/core/domain/__init__.py
  backend/core/domain/exceptions.py
  backend/core/domain/exception_handler.py
  backend/core/domain/notifications.py
  backend/core/domain/transactions.py
  backend/core/domain/access.py
  backend/pytest.ini
  backend/conftest.py
  backend/tests/__init__.py
  backend/tests/test_smoke.py
```

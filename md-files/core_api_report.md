# Core App — API Design Report

> **Branch**: `feat/core-api-drafts`  
> **App**: `backend/core/`  
> **Date**: 2026-02-22

---

## 1. Endpoint Summary

| HTTP Method | URL | Purpose | Access Level |
|---|---|---|---|
| `GET` | `/api/core/dashboard/` | Aggregated dashboard statistics — total cases, breakdowns by status/crime-level, top wanted suspects, recent activity, employee count, unassigned evidence. Data is **role-scoped**. | **Authenticated** — Captain/Chief/Admin see department-wide stats; Detective/Sergeant see their own case stats; others see limited public metrics. |
| `GET` | `/api/core/search/?q=<term>[&category=][&limit=]` | Unified global search across Cases, Suspects, and Evidence. Returns categorised results. | **Authenticated** — results filtered by the user's accessible cases based on role. |
| `GET` | `/api/core/constants/` | System choice enumerations (crime levels, case statuses, evidence types, suspect statuses, verdict choices, bounty tip statuses, complainant statuses, role hierarchy). Used by the frontend to build dropdowns dynamically. | **Public** (`AllowAny`) — configuration data, no sensitive information. |

---

## 2. File Structure

```
backend/core/
├── urls.py              # Route definitions for /dashboard/, /search/, /constants/
├── views.py             # Thin APIViews — parameter validation + service delegation
├── serializers.py       # Response-only serializers defining output schemas
├── services.py          # Business logic — cross-app aggregation & search
├── models.py            # TimeStampedModel, Notification (unchanged)
├── permissions_constants.py  # Permission codenames (unchanged)
├── admin.py             # Django admin registration (unchanged)
└── apps.py              # AppConfig (unchanged)
```

---

## 3. GlobalSearchService — Architecture & Performance

### 3.1 Design Overview

The `GlobalSearchService` implements a **category-parallel, role-scoped** search pattern:

```
Request → View (param validation) → GlobalSearchService
                                        ├── _search_cases()
                                        ├── _search_suspects()
                                        └── _search_evidence()
                                    → Unified response dict
```

### 3.2 Search Strategy

| Aspect | Implementation |
|---|---|
| **Query method** | Django ORM `icontains` (case-insensitive substring matching) as the initial implementation. |
| **Fields searched** | Cases: `title`, `description`. Suspects: `full_name`, `national_id`, `description`. Evidence: `title`, `description`. |
| **Per-category cap** | Each category is independently limited (`limit` param, default 10, max 50) to prevent runaway queries. |
| **Category filtering** | Optional `category` parameter restricts search to one entity type. |
| **Role-based scoping** | `_get_accessible_case_ids()` returns a queryset of Case PKs the user may access; suspect and evidence results are filtered via their Case FK. |

### 3.3 Scalability Path

The current `icontains` approach is suitable for datasets up to ~100K rows per entity. Beyond that, the service is designed to be **swappable**:

1. **Phase 1 (current)**: `icontains` via Django ORM.
2. **Phase 2**: PostgreSQL full-text search using `SearchVector` / `SearchQuery` / `SearchRank` — requires adding `GIN` indexes.
3. **Phase 3**: External search engine (Elasticsearch / Meilisearch) — the service methods become thin clients that query the search index and return the same dict format.

The **view and serializer contracts remain unchanged** regardless of the backend.

### 3.4 Security Model

- The search endpoint requires authentication (`IsAuthenticated`).
- Results are filtered through `_get_accessible_case_ids()` which applies role-based scoping:
  - **Captain / Police Chief / Superuser**: unrestricted access (all cases).
  - **Detective**: only cases where `assigned_detective = user`.
  - **Sergeant**: only cases where `assigned_sergeant = user`.
  - **Others**: only open/public cases.
- Suspects and evidence inherit case-level access control via their ForeignKey to Case.

---

## 4. Cross-App Import Rulebook

### 4.1 The Problem

The `core` app is the **aggregation hub** — it needs to query models from `cases`, `suspects`, `evidence`, and `accounts`. However, those apps already import from `core` (e.g., `TimeStampedModel`, `permissions_constants`). Standard top-level imports would create **circular import chains** that crash at startup.

### 4.2 Rules

| # | Rule | Rationale |
|---|---|---|
| 1 | **Never import models from other apps at the module level** in `core/services.py` or `core/views.py`. | Prevents circular import errors at module-load time. |
| 2 | **Use `django.apps.apps.get_model()` inside methods** as the primary lazy-loading mechanism: `Case = apps.get_model("cases", "Case")`. | Django's app registry is guaranteed to be populated by the time any view/service code runs. |
| 3 | **Import choice enums lazily inside methods** too: `from cases.models import CrimeLevel`. | Choice classes are defined in the same module as models; importing them at the top level would trigger the model file to load. |
| 4 | **For type hints only**, use `TYPE_CHECKING` guards: `from __future__ import annotations` + `if TYPE_CHECKING: from cases.models import Case`. | Gives IDE autocompletion and `mypy` support without runtime imports. |
| 5 | **Views never import models directly** — they only import serializers and services from the core app itself. | Keeps views truly thin; all cross-app awareness lives in the service layer. |
| 6 | **Serializers work with plain dicts**, not model instances. | Services produce dicts; serializers validate/format them. No model coupling in the serializer layer. |

### 4.3 Import Flow Diagram

```
core/views.py
  └── imports core/serializers.py    (same app — safe)
  └── imports core/services.py       (same app — safe)

core/services.py
  └── at runtime (inside methods):
        ├── apps.get_model("cases", "Case")
        ├── apps.get_model("cases", "CaseStatusLog")
        ├── apps.get_model("suspects", "Suspect")
        ├── apps.get_model("evidence", "Evidence")
        ├── apps.get_model("accounts", "User")
        ├── apps.get_model("accounts", "Role")
        └── from cases.models import CrimeLevel, CaseStatus, ...  (lazy)

core/serializers.py
  └── imports ONLY from rest_framework  (no app models)
```

### 4.4 Anti-Patterns to Avoid

```python
# ❌ NEVER do this in core/services.py at module level:
from cases.models import Case          # circular import!
from suspects.models import Suspect    # circular import!

# ✅ ALWAYS do this inside methods:
def _search_cases(self):
    from django.apps import apps
    Case = apps.get_model("cases", "Case")
    ...
```

---

## 5. Dashboard Statistics — Role Scoping Matrix

| User Role | Cases Scope | Suspects/Evidence Scope | Employee Count | Recent Activity |
|---|---|---|---|---|
| **System Admin / Superuser** | All cases | All | Yes | All |
| **Police Chief** | All cases | All | Yes | All |
| **Captain** | All cases | All | Yes | All |
| **Sergeant** | `assigned_sergeant = user` | Linked to scoped cases | Yes | Scoped |
| **Detective** | `assigned_detective = user` | Linked to scoped cases | Yes | Scoped |
| **Other roles** | Public counts only | Public counts only | Yes | Limited |

---

## 6. Response Schema Examples

### 6.1 Dashboard (`GET /api/core/dashboard/`)

```json
{
    "total_cases": 150,
    "active_cases": 42,
    "closed_cases": 95,
    "voided_cases": 13,
    "total_suspects": 87,
    "total_evidence": 320,
    "total_employees": 55,
    "unassigned_evidence_count": 12,
    "cases_by_status": [
        {"status": "open", "label": "Open", "count": 30},
        {"status": "investigation", "label": "Under Investigation", "count": 12}
    ],
    "cases_by_crime_level": [
        {"crime_level": 1, "label": "Level 3 (Minor)", "count": 60},
        {"crime_level": 4, "label": "Critical", "count": 3}
    ],
    "top_wanted_suspects": [
        {
            "id": 42,
            "full_name": "John Doe",
            "national_id": "1234567890",
            "photo_url": "/media/suspect_photos/2025/01/john.jpg",
            "most_wanted_score": 120,
            "reward_amount": 1200000000,
            "days_wanted": 45,
            "case_id": 7,
            "case_title": "Downtown Heist"
        }
    ],
    "recent_activity": [
        {
            "timestamp": "2025-06-15T10:30:00Z",
            "type": "case_status_change",
            "description": "Case #12 moved to Investigation",
            "actor": "det.smith"
        }
    ]
}
```

### 6.2 Global Search (`GET /api/core/search/?q=john&limit=5`)

```json
{
    "query": "john",
    "total_results": 8,
    "cases": [
        {
            "id": 7,
            "title": "John's Disappearance",
            "status": "investigation",
            "crime_level": 3,
            "crime_level_label": "Level 1 (Major)",
            "created_at": "2025-05-01T09:00:00Z"
        }
    ],
    "suspects": [
        {
            "id": 42,
            "full_name": "John Doe",
            "national_id": "1234567890",
            "status": "wanted",
            "case_id": 7,
            "case_title": "John's Disappearance"
        }
    ],
    "evidence": [
        {
            "id": 88,
            "title": "John's ID card",
            "evidence_type": "identity",
            "evidence_type_label": "Identity Document",
            "case_id": 7,
            "case_title": "John's Disappearance"
        }
    ]
}
```

### 6.3 System Constants (`GET /api/core/constants/`)

```json
{
    "crime_levels": [
        {"value": "1", "label": "Level 3 (Minor)"},
        {"value": "2", "label": "Level 2 (Medium)"},
        {"value": "3", "label": "Level 1 (Major)"},
        {"value": "4", "label": "Critical"}
    ],
    "case_statuses": [
        {"value": "complaint_registered", "label": "Complaint Registered"},
        {"value": "open", "label": "Open"}
    ],
    "case_creation_types": [
        {"value": "complaint", "label": "Via Complaint"},
        {"value": "crime_scene", "label": "Via Crime-Scene Report"}
    ],
    "evidence_types": [
        {"value": "testimony", "label": "Witness / Local Testimony"},
        {"value": "biological", "label": "Biological / Medical"},
        {"value": "vehicle", "label": "Vehicle"},
        {"value": "identity", "label": "Identity Document"},
        {"value": "other", "label": "Other Item"}
    ],
    "evidence_file_types": [
        {"value": "image", "label": "Image"},
        {"value": "video", "label": "Video"},
        {"value": "audio", "label": "Audio"},
        {"value": "document", "label": "Document"}
    ],
    "suspect_statuses": [
        {"value": "wanted", "label": "Wanted"},
        {"value": "arrested", "label": "Arrested"},
        {"value": "convicted", "label": "Convicted"},
        {"value": "acquitted", "label": "Acquitted"}
    ],
    "verdict_choices": [
        {"value": "guilty", "label": "Guilty"},
        {"value": "innocent", "label": "Innocent"}
    ],
    "bounty_tip_statuses": [
        {"value": "pending", "label": "Pending Review"},
        {"value": "verified", "label": "Verified by Detective"}
    ],
    "complainant_statuses": [
        {"value": "pending", "label": "Pending"},
        {"value": "approved", "label": "Approved"},
        {"value": "rejected", "label": "Rejected"}
    ],
    "role_hierarchy": [
        {"id": 1, "name": "Police Chief", "hierarchy_level": 10},
        {"id": 2, "name": "Captain", "hierarchy_level": 8},
        {"id": 3, "name": "Sergeant", "hierarchy_level": 6},
        {"id": 4, "name": "Detective", "hierarchy_level": 5},
        {"id": 5, "name": "Cadet", "hierarchy_level": 1}
    ]
}
```

# Core Services — Aggregation, Search & Constants Report

> **Branch**: `feat/core-dashboard-search`  
> **App**: `backend/core/`  
> **Date**: 2026-02-23

---

## 1. Query Strategy

### 1.1 DashboardAggregationService

The dashboard computes all scalar case counters (`total_cases`, `active_cases`, `closed_cases`, `voided_cases`) in a **single aggregate query** using Django's `Count` with `Q` filters:

```python
case_qs.aggregate(
    total_cases=Count("id"),
    active_cases=Count("id", filter=~Q(status__in=[CaseStatus.CLOSED, CaseStatus.VOIDED])),
    closed_cases=Count("id", filter=Q(status=CaseStatus.CLOSED)),
    voided_cases=Count("id", filter=Q(status=CaseStatus.VOIDED)),
)
```

Grouped breakdowns (`cases_by_status`, `cases_by_crime_level`) use `.values().annotate(count=Count("id"))` to produce grouped counts in a single SQL `GROUP BY` query per breakdown.

**N+1 avoidance**: Suspect and evidence totals use `filter(case_id__in=case_ids_qs)` where `case_ids_qs` is a lazy subquery — Django evaluates it as a SQL subselect rather than materialising IDs. Top-wanted suspects use `select_related("case")` to prefetch the case title in the same query.

### 1.2 GlobalSearchService

Each category (Cases, Suspects, Evidence) is searched via `icontains` with `Q` objects for **OR-based multi-field matching**:

| Category   | Fields Searched                                              |
|------------|--------------------------------------------------------------|
| Cases      | `title__icontains`, `description__icontains`                 |
| Suspects   | `full_name__icontains`, `national_id__icontains`, `description__icontains` |
| Evidence   | `title__icontains`, `description__icontains`                 |

**N+1 avoidance**: Suspect and evidence queries use `select_related("case")` so the `case.title` field is fetched in a single joined SQL query. Each category is capped by the `limit` parameter (default 10, max 50) via Python slicing, which translates to a SQL `LIMIT`.

**Category filtering**: An optional `category` query parameter skips unnecessary queries entirely (e.g., `category=suspects` only executes `_search_suspects()`).

### 1.3 SystemConstantsService

Constants are extracted directly from Django `TextChoices` / `IntegerChoices` classes using a generic `_choices_to_list()` helper. The role hierarchy is fetched from the `Role` table via `.values("id", "name", "hierarchy_level")`, producing a minimal SQL query with no joins. No N+1 issues — single query for roles, zero queries for choice enums (they are Python class attributes).

---

## 2. Role Scoping Approach

### 2.1 Shared Infrastructure

Both `DashboardAggregationService` and `GlobalSearchService` reuse the `apply_role_filter()` function from `core.domain.access`, which maps the user's lowercased role name to a queryset filter callable.

### 2.2 Scope Configuration

```python
_SCOPE_CONFIG = {
    "captain":       lambda qs, u: qs,                             # unrestricted
    "police_chief":  lambda qs, u: qs,                             # unrestricted
    "system_admin":  lambda qs, u: qs,                             # unrestricted
    "detective":     lambda qs, u: qs.filter(assigned_detective=u), # own cases only
    "sergeant":      lambda qs, u: qs.filter(                       # supervised cases
        Q(assigned_sergeant=u) | Q(assigned_detective__isnull=False)),
}
# Any other role → default="all" (public counts only)
```

### 2.3 Search Security

The `GlobalSearchService._get_accessible_case_ids()` method returns:

| Role               | Case Access                                              |
|--------------------|----------------------------------------------------------|
| Captain / Chief / Admin | `None` (unrestricted — no filter applied)           |
| Detective          | Cases where `assigned_detective = user`                  |
| Sergeant           | Cases where `assigned_sergeant = user` OR case has a detective |
| Other              | All non-closed, non-voided cases (public visibility)     |

Suspect and evidence results inherit case-level access by filtering `case_id__in=accessible_case_ids`. This ensures a user **never** sees a suspect or evidence item linked to a case they cannot access.

---

## 3. API Payloads

### 3.1 Dashboard Stats (Detective Role)

```http
GET /api/core/dashboard/
Authorization: Bearer <detective-token>
```

```json
{
    "total_cases": 8,
    "active_cases": 5,
    "closed_cases": 2,
    "voided_cases": 1,
    "total_suspects": 12,
    "total_evidence": 34,
    "total_employees": 55,
    "unassigned_evidence_count": 3,
    "cases_by_status": [
        {"status": "investigation", "label": "Under Investigation", "count": 3},
        {"status": "suspect_identified", "label": "Suspect Identified", "count": 2},
        {"status": "closed", "label": "Closed", "count": 2},
        {"status": "voided", "label": "Voided", "count": 1}
    ],
    "cases_by_crime_level": [
        {"crime_level": 1, "label": "Level 3 (Minor)", "count": 3},
        {"crime_level": 2, "label": "Level 2 (Medium)", "count": 2},
        {"crime_level": 3, "label": "Level 1 (Major)", "count": 2},
        {"crime_level": 4, "label": "Critical", "count": 1}
    ],
    "top_wanted_suspects": [
        {
            "id": 42,
            "full_name": "John Doe",
            "national_id": "1234567890",
            "photo_url": "/media/suspect_photos/2025/01/john.jpg",
            "most_wanted_score": 120,
            "reward_amount": 2400000000,
            "days_wanted": 45,
            "case_id": 7,
            "case_title": "Downtown Heist"
        }
    ],
    "recent_activity": [
        {
            "timestamp": "2026-02-20T10:30:00Z",
            "type": "case_status_change",
            "description": "Case #7 moved from investigation to suspect_identified",
            "actor": "det.smith"
        }
    ]
}
```

### 3.2 Global Search Results

```http
GET /api/core/search/?q=john&limit=5
Authorization: Bearer <token>
```

```json
{
    "query": "john",
    "total_results": 3,
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

### 3.3 System Constants

```http
GET /api/core/constants/
```

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
        {"value": "cadet_review", "label": "Under Cadet Review"},
        {"value": "returned_to_complainant", "label": "Returned to Complainant"},
        {"value": "officer_review", "label": "Under Officer Review"},
        {"value": "returned_to_cadet", "label": "Returned to Cadet"},
        {"value": "voided", "label": "Voided"},
        {"value": "pending_approval", "label": "Pending Superior Approval"},
        {"value": "open", "label": "Open"},
        {"value": "investigation", "label": "Under Investigation"},
        {"value": "suspect_identified", "label": "Suspect Identified"},
        {"value": "sergeant_review", "label": "Under Sergeant Review"},
        {"value": "arrest_ordered", "label": "Arrest Ordered"},
        {"value": "interrogation", "label": "Under Interrogation"},
        {"value": "captain_review", "label": "Under Captain Review"},
        {"value": "chief_review", "label": "Under Chief Review"},
        {"value": "judiciary", "label": "Referred to Judiciary"},
        {"value": "closed", "label": "Closed"}
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
        {"value": "under_interrogation", "label": "Under Interrogation"},
        {"value": "pending_captain_verdict", "label": "Pending Captain Verdict"},
        {"value": "pending_chief_approval", "label": "Pending Chief Approval"},
        {"value": "under_trial", "label": "Under Trial"},
        {"value": "convicted", "label": "Convicted"},
        {"value": "acquitted", "label": "Acquitted"},
        {"value": "released", "label": "Released on Bail"}
    ],
    "verdict_choices": [
        {"value": "guilty", "label": "Guilty"},
        {"value": "innocent", "label": "Innocent"}
    ],
    "bounty_tip_statuses": [
        {"value": "pending", "label": "Pending Review"},
        {"value": "officer_reviewed", "label": "Reviewed by Officer"},
        {"value": "verified", "label": "Verified by Detective"},
        {"value": "rejected", "label": "Rejected"}
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
        {"id": 5, "name": "Police Officer", "hierarchy_level": 4},
        {"id": 6, "name": "Cadet", "hierarchy_level": 1}
    ]
}
```

---

## 4. Files Modified

| File | Change |
|---|---|
| `backend/core/services.py` | Implemented `DashboardAggregationService.get_stats()`, `GlobalSearchService.search()`, `SystemConstantsService.get_constants()`, and `NotificationService` methods. |
| `md-files/core_services_aggregation_report.md` | This report. |

> Views (`core/views.py`), serializers (`core/serializers.py`), and URLs (`core/urls.py`) were already correctly wired from the API drafts branch — no changes required.

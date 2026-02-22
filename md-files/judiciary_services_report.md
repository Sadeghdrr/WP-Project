# Judiciary Services Report

> **Generated:** 2026-02-23  
> **Branch:** `feat/judiciary-flow-services`  
> **Scope:** `CaseReportingService` (cases app) · `TrialService` (suspects app) · Views / Serializers wiring

---

## 1. Report Payload Schema

`GET /api/cases/{id}/report/` returns the following aggregated JSON structure.
All date-time values are ISO 8601 strings.  Nullable fields may be `null`.

```jsonc
{
  "case": {
    "id": 42,
    "title": "Armed Robbery — District 7",
    "description": "Armed robbery at commercial bank branch on Azadi St.",
    "crime_level": 3,
    "crime_level_display": "Felony",
    "status": "judiciary",
    "status_display": "Judiciary",
    "creation_type": "crime_scene",
    "rejection_count": 0,
    "incident_date": "2025-12-01T18:30:00+03:30",
    "location": "Azadi Street, Branch 14",
    "created_at": "2025-12-02T08:15:00+03:30",
    "updated_at": "2026-01-20T14:00:00+03:30"
  },

  "personnel": {
    "created_by":          { "id": 5,  "full_name": "Cadet Ali Moradi",       "role": "Cadet" },
    "approved_by":         { "id": 8,  "full_name": "Officer Reza Karimi",    "role": "Officer" },
    "assigned_detective":  { "id": 12, "full_name": "Det. Sara Hosseini",     "role": "Detective" },
    "assigned_sergeant":   { "id": 15, "full_name": "Sgt. Mehdi Tavakoli",    "role": "Sergeant" },
    "assigned_captain":    { "id": 20, "full_name": "Cpt. Fatemeh Ahmadi",    "role": "Captain" },
    "assigned_judge":      { "id": 30, "full_name": "Judge Mohammad Jafari",  "role": "Judge" }
  },

  "complainants": [
    {
      "id": 1,
      "user": { "id": 100, "full_name": "Naser Salehi", "role": null },
      "is_primary": true,
      "status": "approved",
      "reviewed_by": { "id": 5, "full_name": "Cadet Ali Moradi", "role": "Cadet" }
    }
  ],

  "witnesses": [
    {
      "id": 1,
      "full_name": "Maryam Rezaei",
      "phone_number": "+989121234567",
      "national_id": "0012345678"
    }
  ],

  "evidence": [
    {
      "id": 10,
      "evidence_type": "photo",
      "title": "Security camera still — entrance",
      "description": "Frame capture at 18:32 showing suspect entering.",
      "registered_by": { "id": 12, "full_name": "Det. Sara Hosseini", "role": "Detective" },
      "created_at": "2025-12-03T10:00:00+03:30"
    },
    {
      "id": 11,
      "evidence_type": "document",
      "title": "Witness sworn statement",
      "description": null,
      "registered_by": { "id": 12, "full_name": "Det. Sara Hosseini", "role": "Detective" },
      "created_at": "2025-12-04T09:00:00+03:30"
    }
  ],

  "suspects": [
    {
      "id": 7,
      "full_name": "Hamid Noori",
      "national_id": "0087654321",
      "status": "under_trial",
      "status_display": "Under Trial",
      "wanted_since": "2025-12-10T00:00:00+03:30",
      "days_wanted": 75,
      "identified_by": { "id": 12, "full_name": "Det. Sara Hosseini", "role": "Detective" },
      "sergeant_approval_status": "approved",
      "approved_by_sergeant": { "id": 15, "full_name": "Sgt. Mehdi Tavakoli", "role": "Sergeant" },
      "sergeant_rejection_message": null,

      "interrogations": [
        {
          "id": 3,
          "detective": { "id": 12, "full_name": "Det. Sara Hosseini", "role": "Detective" },
          "sergeant": { "id": 15, "full_name": "Sgt. Mehdi Tavakoli", "role": "Sergeant" },
          "detective_guilt_score": 8,
          "sergeant_guilt_score": 7,
          "notes": "Suspect admitted to planning the heist.",
          "created_at": "2025-12-20T11:00:00+03:30"
        }
      ],

      "trials": [
        {
          "id": 1,
          "judge": { "id": 30, "full_name": "Judge Mohammad Jafari", "role": "Judge" },
          "verdict": "guilty",
          "punishment_title": "Armed Robbery",
          "punishment_description": "15 years imprisonment and full restitution.",
          "created_at": "2026-01-20T14:00:00+03:30"
        }
      ]
    }
  ],

  "status_history": [
    {
      "id": 1,
      "from_status": null,
      "to_status": "draft",
      "changed_by": { "id": 5, "full_name": "Cadet Ali Moradi", "role": "Cadet" },
      "message": "Case created.",
      "created_at": "2025-12-02T08:15:00+03:30"
    },
    {
      "id": 2,
      "from_status": "draft",
      "to_status": "pending_cadet_review",
      "changed_by": { "id": 5, "full_name": "Cadet Ali Moradi", "role": "Cadet" },
      "message": "Submitted for review.",
      "created_at": "2025-12-02T09:00:00+03:30"
    }
  ],

  "calculations": {
    "crime_level_degree": 3,
    "days_since_creation": 83,
    "tracking_threshold": 249,
    "reward_rials": 4980000000
  }
}
```

---

## 2. Access Rules

### Case Report — `GET /api/cases/{id}/report/`

| Role                   | Allowed | Notes |
|------------------------|:-------:|-------|
| **Judge**              | ✅      | Needs the full report before rendering a verdict. |
| **Captain**            | ✅      | Reviews case completeness before forwarding to judiciary. |
| **Police Chief**       | ✅      | Senior oversight; approves critical-level cases. |
| **System Administrator** | ✅   | Administrative access. |
| Superuser (`is_superuser`) | ✅ | Django superuser bypass. |
| Detective              | ❌      | Uses detail view; no access to aggregated report. |
| Sergeant               | ❌      | — |
| Officer / Cadet        | ❌      | — |
| Complainant / Public   | ❌      | — |

Enforcement: `CaseReportingService._REPORT_ALLOWED_ROLES` frozen-set + `get_user_role_name()` check.

### Trial Creation — `POST /api/suspects/{suspect_pk}/trials/`

| Role      | Allowed | Constraint |
|-----------|:-------:|------------|
| **Judge** | ✅      | Must hold `suspects.can_judge_trial` permission **AND** be the `assigned_judge` on the case. |
| All other | ❌      | `PermissionDenied` (HTTP 403). |

Additional guards enforced by `TrialService.create_trial()`:
- Suspect must be in `UNDER_TRIAL` status.
- If verdict is `guilty`, `punishment_title` and `punishment_description` are required.
- If verdict is `innocent`, punishment fields are cleared automatically.

---

## 3. API Sequences — Trial Creation Payloads

### 3.1 Successful Trial — Guilty Verdict with Punishment

**Request**

```http
POST /api/suspects/7/trials/
Content-Type: application/json
Authorization: Bearer <judge-jwt>
```

```json
{
  "verdict": "guilty",
  "punishment_title": "Armed Robbery",
  "punishment_description": "15 years imprisonment without parole and full restitution of stolen assets."
}
```

**Response** — `201 Created`

```json
{
  "id": 1,
  "suspect": 7,
  "suspect_name": "Hamid Noori",
  "case": 42,
  "judge": 30,
  "judge_name": "Judge Mohammad Jafari",
  "verdict": "guilty",
  "verdict_display": "Guilty",
  "punishment_title": "Armed Robbery",
  "punishment_description": "15 years imprisonment without parole and full restitution of stolen assets.",
  "created_at": "2026-01-20T14:00:00+03:30",
  "updated_at": "2026-01-20T14:00:00+03:30"
}
```

**Side effects:**
1. Suspect status transitions from `under_trial` → `convicted`.
2. `SuspectStatusLog` audit entry created.
3. If all suspects in the case are resolved (convicted / acquitted / released), the case transitions to `closed` and a `CaseStatusLog` entry is written.
4. `NotificationService` dispatches a `trial_created` notification to the assigned detective and captain.

---

### 3.2 Failed Trial — Guilty Verdict Missing Punishment

**Request**

```http
POST /api/suspects/7/trials/
Content-Type: application/json
Authorization: Bearer <judge-jwt>
```

```json
{
  "verdict": "guilty",
  "punishment_title": "",
  "punishment_description": ""
}
```

**Response** — `400 Bad Request`

```json
{
  "punishment_title": [
    "Required when verdict is guilty."
  ]
}
```

This validation fires at the **serializer layer** (`TrialCreateSerializer.validate`), preventing the request from reaching the service. The service has a redundant guard that raises `DomainError` (also mapped to HTTP 400) for defence-in-depth.

---

## 4. Domain Exception → HTTP Status Mapping

| Exception class                       | HTTP Status | Used in |
|---------------------------------------|:-----------:|---------|
| `core.domain.exceptions.PermissionDenied` | **403** Forbidden | Trial create, Case report |
| `core.domain.exceptions.NotFound`         | **404** Not Found  | Trial list/detail/create, Case report |
| `core.domain.exceptions.DomainError`      | **400** Bad Request | Trial create (status guard, punishment validation) |

---

## 5. Files Modified

| File | Change |
|------|--------|
| `cases/services.py` | Added `CaseReportingService` class + `_user_summary()` helper. |
| `cases/serializers.py` | Added `CaseReportSerializer` and nested sub-serializers for the full report schema. |
| `cases/views.py` | Added `report` action on `CaseViewSet` wired to `CaseReportingService`. |
| `suspects/services.py` | Replaced `TrialService` stubs with full implementations (`get_trials_for_suspect`, `list_trials`, `get_trial_detail`, `create_trial`). |
| `suspects/serializers.py` | Implemented `TrialCreateSerializer.validate`, `TrialListSerializer.get_judge_name`, `TrialDetailSerializer.get_judge_name`, `TrialDetailSerializer.get_suspect_name`. |
| `suspects/views.py` | Replaced `TrialViewSet` stubs (`list`, `create`, `retrieve`) with service-delegating implementations. |

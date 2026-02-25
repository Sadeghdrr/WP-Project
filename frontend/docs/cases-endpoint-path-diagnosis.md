# Cases Endpoint Path Diagnosis

## Problem Statement

The Cases page fails at runtime. Browser network tab shows a request to `/api/cases/cases/` returning HTTP 500.

## Root Cause Analysis

### A. Frontend Endpoint Construction — BUG CONFIRMED

| Layer | Value |
|-------|-------|
| `BASE_URL` (`client.ts`) | `/api` |
| `API.CASES` (`endpoints.ts`, before fix) | `/cases/cases/` |
| Constructed URL (`apiFetch`) | `/api` + `/cases/cases/` = **`/api/cases/cases/`** |

The frontend endpoint constant had a **duplicated `cases/` segment**. The first `/cases/` in the path is redundant because the backend project-level `urls.py` mounts the cases app at `api/` (not `api/cases/`), and the router inside `cases/urls.py` registers under prefix `cases`. So the actual backend route is `/api/cases/`, not `/api/cases/cases/`.

All 20+ cases endpoint paths in `endpoints.ts` had this duplication.

**Likely origin**: Copy-paste from the suspects section, which legitimately uses double-prefix (`/suspects/suspects/`) because the suspects app is mounted at `api/suspects/` at the project level AND registers with router prefix `suspects`.

### B. Backend Routing Reality (read-only diagnosis)

| Config File | Mount Point | Router Prefix | Combined Runtime Path |
|-------------|-------------|---------------|----------------------|
| `backend/urls.py` → `cases.urls` | `api/` | `cases` | `/api/cases/` |
| `backend/urls.py` → `suspects.urls` | `api/suspects/` | `suspects` | `/api/suspects/suspects/` |
| `backend/urls.py` → `evidence.urls` | `api/` | `evidence` | `/api/evidence/` |

- **Cases**: Project mounts at `api/`, router adds `cases/` → runtime path `/api/cases/`
- **Suspects**: Project mounts at `api/suspects/`, router adds `suspects/` → runtime path `/api/suspects/suspects/` (genuine double prefix)
- **Evidence**: Project mounts at `api/`, router adds `evidence/` → runtime path `/api/evidence/`

**Backend routes are correctly configured.** There is no backend routing bug for cases.

### C. Runtime Failure Classification — HTTP 500

When Django receives `/api/cases/cases/`:
1. Project URL dispatcher strips `api/` prefix, passes `cases/cases/` to cases router
2. `DefaultRouter` pattern `^cases/(?P<pk>[^/.]+)/$` matches with `pk="cases"`
3. `CaseViewSet.retrieve()` attempts to look up a Case with pk=`"cases"` (non-integer)
4. This causes an unhandled `ValueError` or `DoesNotExist` → **HTTP 500**

The 500 is a **consequence of the wrong path**, not a separate backend bug. However, the backend ideally should validate PK format and return 404 for non-integer PKs — this is a minor backend robustness gap (reported only, not fixed).

## Swagger / OpenAPI Documented Paths

From `md-files/swagger_documentation_report.md`:

```
GET  /api/cases/         → CaseViewSet.list
POST /api/cases/         → CaseViewSet.create
GET  /api/cases/{id}/    → CaseViewSet.retrieve
...
```

All documented paths use `/api/cases/` (single segment), consistent with backend routing.

## Frontend Endpoint Paths — Before / After

| Endpoint Constant | Before (wrong) | After (fixed) |
|---|---|---|
| `CASES` | `/cases/cases/` | `/cases/` |
| `case(id)` | `/cases/cases/${id}/` | `/cases/${id}/` |
| `CASE_STATUS_LOG(id)` | `/cases/cases/${id}/status-log/` | `/cases/${id}/status-log/` |
| `CASE_CALCULATIONS(id)` | `/cases/cases/${id}/calculations/` | `/cases/${id}/calculations/` |
| `CASE_REPORT(id)` | `/cases/cases/${id}/report/` | `/cases/${id}/report/` |
| `COMPLAINANTS(id)` | `/cases/cases/${id}/complainants/` | `/cases/${id}/complainants/` |
| `COMPLAINANT_REVIEW(id, cid)` | `/cases/cases/${id}/complainants/${cid}/review/` | `/cases/${id}/complainants/${cid}/review/` |
| `WITNESSES(id)` | `/cases/cases/${id}/witnesses/` | `/cases/${id}/witnesses/` |
| `CASE_SUBMIT(id)` | `/cases/cases/${id}/submit/` | `/cases/${id}/submit/` |
| `CASE_RESUBMIT(id)` | `/cases/cases/${id}/resubmit/` | `/cases/${id}/resubmit/` |
| `CASE_CADET_REVIEW(id)` | `/cases/cases/${id}/cadet-review/` | `/cases/${id}/cadet-review/` |
| `CASE_OFFICER_REVIEW(id)` | `/cases/cases/${id}/officer-review/` | `/cases/${id}/officer-review/` |
| `CASE_APPROVE_CRIME_SCENE(id)` | `/cases/cases/${id}/approve-crime-scene/` | `/cases/${id}/approve-crime-scene/` |
| `CASE_DECLARE_SUSPECTS(id)` | `/cases/cases/${id}/declare-suspects/` | `/cases/${id}/declare-suspects/` |
| `CASE_SERGEANT_REVIEW(id)` | `/cases/cases/${id}/sergeant-review/` | `/cases/${id}/sergeant-review/` |
| `CASE_FORWARD_JUDICIARY(id)` | `/cases/cases/${id}/forward-judiciary/` | `/cases/${id}/forward-judiciary/` |
| `CASE_TRANSITION(id)` | `/cases/cases/${id}/transition/` | `/cases/${id}/transition/` |
| `CASE_ASSIGN_DETECTIVE(id)` | `/cases/cases/${id}/assign-detective/` | `/cases/${id}/assign-detective/` |
| `CASE_UNASSIGN_DETECTIVE(id)` | `/cases/cases/${id}/unassign-detective/` | `/cases/${id}/unassign-detective/` |
| `CASE_ASSIGN_SERGEANT(id)` | `/cases/cases/${id}/assign-sergeant/` | `/cases/${id}/assign-sergeant/` |
| `CASE_ASSIGN_CAPTAIN(id)` | `/cases/cases/${id}/assign-captain/` | `/cases/${id}/assign-captain/` |
| `CASE_ASSIGN_JUDGE(id)` | `/cases/cases/${id}/assign-judge/` | `/cases/${id}/assign-judge/` |

## Evidence Endpoints — Same Bug (also fixed)

Evidence had the same duplicated-segment issue:

| Endpoint | Before | After |
|---|---|---|
| `EVIDENCE` | `/evidence/evidence/` | `/evidence/` |
| `evidence(id)` | `/evidence/evidence/${id}/` | `/evidence/${id}/` |

## Classification Summary

| Category | Finding |
|---|---|
| **Frontend bug?** | ✅ Yes — duplicated path segment in 22+ endpoint constants |
| **Backend routing mismatch?** | ❌ No — backend routes are correct (`/api/cases/`) |
| **Backend runtime 500?** | ⚠️ Consequence of wrong path hitting detail view with pk="cases"; not a standalone backend bug, but backend could improve PK validation |

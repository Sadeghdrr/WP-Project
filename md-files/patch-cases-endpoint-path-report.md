# Patch Report: Cases Endpoint Path Construction

**Date**: 2025-02-25  
**Branch**: `agent/step-13-cases-complaints-workspace`  
**Type**: Corrective frontend patch (diagnosis + fix)

## Files Created / Changed

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/api/endpoints.ts` | Modified | Fixed 22 cases endpoint paths + 2 evidence endpoint paths (removed duplicated segment) |
| `frontend/docs/cases-endpoint-path-diagnosis.md` | Created | Detailed root-cause analysis with before/after paths |
| `md-files/patch-cases-endpoint-path-report.md` | Created | This report |

## Root Cause Classification

| Category | Status | Details |
|---|---|---|
| **Frontend bug** | ✅ CONFIRMED | All cases endpoint constants in `endpoints.ts` had a duplicated `/cases/cases/` segment. Correct path: `/cases/`. Same issue existed for evidence (`/evidence/evidence/` → `/evidence/`). |
| **Backend routing mismatch** | ❌ NOT PRESENT | Backend routes are correctly configured: project mounts cases app at `api/` and router uses prefix `cases` → runtime path `/api/cases/` matches Swagger docs. |
| **Backend runtime 500** | ⚠️ CONSEQUENCE | The 500 is caused by Django matching `/api/cases/cases/` as the detail endpoint with `pk="cases"`, which fails on integer conversion. Not a standalone backend issue. |

## Frontend Patch Applied

**What**: Removed duplicated path segment from all cases and evidence endpoint constants in `frontend/src/api/endpoints.ts`.

**Why**: The `apiFetch` wrapper prepends `BASE_URL` (`/api`) to endpoint paths. The cases app is mounted at `api/` in Django's project `urls.py`, and the router registers prefix `cases`. So the correct endpoint path (relative to `/api`) is `/cases/`, not `/cases/cases/`.

The bug likely originated from copy-pasting the suspects pattern, which genuinely has double prefix because its project-level mount is `api/suspects/` AND its router prefix is `suspects`.

**Scope**:
- 22 cases endpoint paths: `/cases/cases/...` → `/cases/...`
- 2 evidence endpoint paths: `/evidence/evidence/...` → `/evidence/...`
- No other files or logic changed

## Backend Anomalies / Problems Found (report only)

1. **Non-integer PK returns 500 instead of 404**: When `DefaultRouter` detail endpoint receives a non-integer PK like `"cases"`, Django returns HTTP 500 instead of 404. The backend should validate PK format. (NOT FIXED — backend change required.)

2. **Inconsistent app URL mounting pattern**: The suspects app is mounted at `api/suspects/` then registers router prefix `suspects`, producing a double-segment path `/api/suspects/suspects/`. All other apps (cases, evidence, board) are mounted at `api/` with only the router prefix producing the path. This inconsistency is confusing and led to the frontend bug. (NOT FIXED — backend change required.)

## Confirmation

- ✅ No backend files were modified
- ✅ `tsc --noEmit` passes with zero errors
- ✅ `vite build` succeeds
- ✅ Frontend cases page requirement (§5.6) remains aligned with project-doc.md
- ⚠️ Runtime verification against live backend blocked until backend 500 / PK validation is resolved (or until request hits correct path — the path fix itself should resolve the 500 since the correct endpoint will be called)

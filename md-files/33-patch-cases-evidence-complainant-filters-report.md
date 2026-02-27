# Patch Report: Case Detail Evidence Entry, Complainant Display & Clear Filters

**Date:** 2026-02-25
**Branch:** `agent/patch-cases-evidence-complainant-filters`
**Type:** Corrective frontend patch (post Steps 13 & 14)

---

## Files Created / Changed

| File | Action |
|------|--------|
| `frontend/src/types/cases.ts` | Modified — fixed `CaseComplainant` and `CaseStatusLog` types |
| `frontend/src/pages/Cases/CaseDetailPage.tsx` | Modified — added evidence section, fixed name rendering |
| `frontend/src/pages/Cases/CaseListPage.tsx` | Modified — fixed clear-filter debounce bypass |
| `frontend/docs/cases-evidence-complainant-filter-patch-notes.md` | Created — patch notes |
| `md-files/patch-cases-evidence-complainant-filters-report.md` | Created — this report |

---

## Root Cause Classification

### A) Evidence integration gap → **A1**

**Evidence feature exists, but Case Detail has no integration entry point.**

- Routes exist: `/cases/:caseId/evidence`, `/cases/:caseId/evidence/new`, `/cases/:caseId/evidence/:evidenceId`
- Pages exist: `EvidenceListPage`, `AddEvidencePage`, `EvidenceDetailPage`
- `AddEvidencePage` correctly reads `caseId` from URL params
- But `CaseDetailPage.tsx` (Step 13 output) had zero references to evidence — no button, link, or section

### B) Complainant undefined undefined → **B1 + B2**

**Frontend type/interface mismatch + UI renderer ignores `user_display`.**

- Backend `CaseComplainantSerializer` returns:
  - `user`: numeric FK (int) — default ModelSerializer behavior
  - `user_display`: string — from `SerializerMethodField`
- Frontend `CaseComplainant` type defined `user: UserRef` (expects `{id, username, first_name, last_name}`)
- Frontend did NOT have `user_display` field in the type
- UI code: `(c.user as {first_name, last_name}).first_name` → accessing `.first_name` on a number → `undefined`
- Same mismatch for `CaseStatusLog.changed_by` (backend: numeric + `changed_by_name` string)

### C) Clear filter not reloading → **C4**

**Debounced search state remains stale after clear.**

- `clearFilters()` resets `searchInput` to `""` (immediate state update)
- `debouncedSearch = useDebounce(searchInput, 400)` — retains old value for 400ms
- `filters.search = debouncedSearch` — query key includes stale search term
- Query key `["cases", {search: "old"}]` unchanged → no refetch for up to 400ms
- Clear button disappears immediately (checks raw `searchInput`) but data shows filtered results

---

## What Was Fixed

### Problem 1: Evidence integration in Case Detail

- Added `EvidenceSection` sub-component to `CaseDetailPage.tsx`
- Fetches related evidence via `useEvidence({ case: caseId })` hook
- Displays compact table (up to 5 items) with title, type, date
- Each evidence title is a link to its detail page
- "Register Evidence" button navigates to `/cases/${caseId}/evidence/new`
- "View All Evidence" button navigates to `/cases/${caseId}/evidence`
- Permission-aware: register button shown based on permission set presence

### Problem 2: Complainant name rendering

- Updated `CaseComplainant` type: `user: number` (was `UserRef`), added `user_display: string`
- Updated `CaseStatusLog` type: `changed_by: number | null` (was `UserRef | null`), added `changed_by_name: string | null`
- Complainant rendering now uses: `c.user_display || \`User #\${c.user}\``
- Status timeline rendering now uses: `log.changed_by_name || \`User #\${log.changed_by}\``
- Display name source priority:
  1. `user_display` / `changed_by_name` (from backend SerializerMethodField)
  2. Fallback: `User #<id>` (safe fallback if display field is empty)

### Problem 3: Clear filter reload

- Added `effectiveSearch` computation: `searchInput ? debouncedSearch : ""`
- When `searchInput` is empty (after clear), `effectiveSearch` is immediately `""`
- Filters object drops `search` key immediately → query key changes → TanStack Query refetches
- Debounce still works normally during typing (searchInput is non-empty, uses debouncedSearch)

---

## How Evidence Integration Connects to Step 14

- The evidence pages (list, form, detail) were created in Step 14
- Routes were already registered in `Router.tsx` under `/cases/:caseId/evidence/*`
- `AddEvidencePage` reads `caseId` from `useParams()` and includes it in the API payload
- This patch simply adds the navigation entry point from Case Detail to those existing pages
- No new routes, pages, or API endpoints were created

---

## Backend Anomalies / Problems Detected (report only)

1. **Personnel fields return numeric IDs only:** `CaseDetailSerializer` returns `created_by`, `approved_by`, `assigned_detective`, `assigned_sergeant`, `assigned_captain`, `assigned_judge` as plain integer FK values without display names. The frontend shows them as `User #N`. Fixing this would require adding `SerializerMethodField` display name fields in the backend serializer (similar to `user_display` on complainants).  
   **Impact:** Low — personnel display is functional but not user-friendly.

2. **No evidence count in CaseDetail response:** The `CaseDetailSerializer` does not include an evidence count or evidence list. The frontend must make a separate API call to fetch evidence for the case.  
   **Impact:** Low — the extra API call is acceptable.

---

## Confirmation: No Backend Files Modified

✅ All changes are limited to `frontend/` directory and `md-files/` report.  
✅ No backend Python files were created, modified, or deleted.

---

## Validation Checklist

| Check | Status |
|-------|--------|
| Evidence entry/action visible in Case Detail (when authorized) | ✅ |
| Navigation to evidence create works with case context (`caseId` in URL) | ✅ |
| Navigation to evidence list works with case context | ✅ |
| Complainant name displays correctly from `user_display` field | ✅ |
| Status log names display correctly from `changed_by_name` field | ✅ |
| Safe fallback when display field is missing/empty | ✅ |
| Clear filter triggers data reload (query key changes immediately) | ✅ |
| Debounce still works for search typing | ✅ |
| No layout regressions (uses existing CSS classes) | ✅ |
| No backend changes | ✅ |
| App compiles without TypeScript errors | ✅ |

---

## Post-Check: Alignment with project-doc.md

- **§4.3 Evidence Registration:** Case Detail now provides access path to evidence registration — aligns with requirement that evidence can be registered for cases
- **§5.6 Case and Complaint Status:** Cases workspace filtering works correctly — clear filter reliably shows unfiltered list
- **§5.8 Evidence Registration and Review:** Evidence section in case detail provides contextual access to evidence workspace

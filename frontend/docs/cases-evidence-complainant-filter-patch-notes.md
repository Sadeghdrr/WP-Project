# Patch Notes: Case Detail Evidence Entry, Complainant Display & Clear Filters

**Date:** 2026-02-25
**Type:** Corrective patch (post Steps 13 & 14)
**Branch:** `agent/patch-cases-evidence-complainant-filters`

---

## Issues Addressed

### 1. Case Detail missing evidence registration entry (ثبت شواهد)

**Root Cause:** A1 — Evidence feature exists (routes, pages, form at `/cases/:caseId/evidence/new`), but CaseDetailPage had no integration entry point (no button, link, or section).

**Fix:**
- Added `EvidenceSection` component to CaseDetailPage
- Shows compact list of up to 5 related evidence items (via `useEvidence({ case: caseId })`)
- Includes "Register Evidence" button (links to `/cases/:caseId/evidence/new`)
- Includes "View All Evidence" link (links to `/cases/:caseId/evidence`)
- Permission-aware: register button shown to authenticated users (backend enforces actual permissions)

### 2. Complainant name renders as `undefined undefined`

**Root Cause:** B1 + B2 — Frontend type/interface mismatch AND UI renderer ignores `user_display`.

- Backend `CaseComplainantSerializer` returns `user` as numeric ID + `user_display` as display name string
- Frontend `CaseComplainant` type had `user: UserRef` (nested object with `first_name`, `last_name`)
- UI code cast `user` to `{first_name, last_name}` → accessing properties on a number → `undefined undefined`
- Same pattern for `CaseStatusLog.changed_by` (backend returns numeric + `changed_by_name` string)

**Fix:**
- Updated `CaseComplainant` type: `user: number`, added `user_display: string`, `reviewed_by: number | null`
- Updated `CaseStatusLog` type: `changed_by: number | null`, added `changed_by_name: string | null`
- Updated complainant rendering: `c.user_display || \`User #\${c.user}\``
- Updated status timeline: `log.changed_by_name || \`User #\${log.changed_by}\``

### 3. Cases "Clear filter" does not reload data

**Root Cause:** C4 — Debounced search state remains stale.

- `clearFilters()` reset `searchInput` to `""` immediately
- But `debouncedSearch` (from `useDebounce(searchInput, 400)`) retained old value for 400ms
- The `filters` object used `debouncedSearch` → query key unchanged → no immediate refetch
- Clear button disappeared (checked raw `searchInput`) but data stayed filtered

**Fix:**
- Added `effectiveSearch` computation: `searchInput ? debouncedSearch : ""`
- When `searchInput` is cleared, `effectiveSearch` is immediately `""`, bypassing debounce delay
- Query key changes immediately → TanStack Query triggers fresh fetch with empty filters

---

## Files Changed

| File | Change |
|------|--------|
| `src/types/cases.ts` | Fixed `CaseComplainant` and `CaseStatusLog` types to match backend response shape |
| `src/pages/Cases/CaseDetailPage.tsx` | Added `EvidenceSection`, fixed complainant/status-log name rendering |
| `src/pages/Cases/CaseListPage.tsx` | Fixed clear-filter debounce bypass |

---

## Evidence Integration Details

- Reuses existing Step 14 evidence infrastructure (routes, pages, hooks)
- `EvidenceSection` uses `useEvidence({ case: caseId })` to fetch related evidence
- "Register Evidence" navigates to `/cases/:caseId/evidence/new` (existing `AddEvidencePage`)
- `AddEvidencePage` already reads `caseId` from URL params and prefills the case field
- No new routes or pages were created

---

## Permission Behavior

- Evidence registration button is shown to any authenticated user
- Backend enforces actual permission checks on the evidence creation endpoint
- No hardcoded role-based visibility beyond what the permission set provides

---

## Deferred Items

- Personnel display names (created_by, assigned_detective, etc.) still show as `User #N` because backend returns numeric IDs without display names for these fields; fixing would require backend changes or additional API calls
- Evidence section does not show pagination (only first 5 items); "View All Evidence" links to full list page

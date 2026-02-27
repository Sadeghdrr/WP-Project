# Evidence Workspace — Polymorphic Create & Case Integration Report

## Summary

Implemented production-grade improvements to the Evidence create form, list page,
and case integration. The existing codebase (from Steps 13/14) already had a
functional Evidence workspace; this step hardened error handling, fixed payload
construction, and corrected the debounce-on-clear bug.

---

## Backend Source Inspection (Authoritative)

### Files Inspected

| File | Lines | Purpose |
|------|-------|---------|
| `backend/evidence/models.py` | 351 | Multi-table inheritance hierarchy, DB constraints |
| `backend/evidence/serializers.py` | 970 | Polymorphic create dispatcher, per-type validation |
| `backend/evidence/views.py` | 378 | ViewSet with polymorphic create, verify, link/unlink |

### Key Findings

1. **Multi-table inheritance**: `Evidence` base → `TestimonyEvidence`,
   `BiologicalEvidence`, `VehicleEvidence`, `IdentityEvidence` (Other uses base).

2. **Polymorphic create dispatch**: `EvidencePolymorphicCreateSerializer.create()`
   reads `evidence_type` from validated data, looks up child serializer from
   `_SERIALIZER_MAP`, validates child-specific fields, then delegates to
   `EvidenceProcessingService`.

3. **Vehicle XOR constraint**:
   - DB: `CheckConstraint("vehicle_plate_xor_serial")` —
     `(license_plate == "" AND serial_number != "") OR (license_plate != "" AND serial_number == "")`
   - Serializer: `VehicleEvidenceCreateSerializer.validate()` raises
     `non_field_errors` with exact messages:
     - Both filled: `"Provide either a license plate or a serial number, not both."`
     - Neither filled: `"Either a license plate or a serial number must be provided."`
   - Extra kwargs: both fields have `required=False, allow_blank=True, default=""`

4. **Identity document_details**: JSONField validated in
   `IdentityEvidenceCreateSerializer.validate_document_details()` — must be a
   flat `dict[str, str]`. Error: `"document_details must be a flat dictionary of string→string."`

5. **No anomalies found** in the backend that would block frontend implementation.

---

## Changes Made

### 1. AddEvidencePage — Error Handling Improvement

**Problem**: The mutation threw `new Error(message)` which lost `fieldErrors`
from the `ApiResponse`. Backend validation errors (e.g., title uniqueness,
vehicle XOR) were only shown as a generic toast — not inline on the relevant
form field.

**Fix**: Bypassed the React Query mutation for create and called
`createEvidence()` from `api/evidence.ts` directly. On error response:
- Maps `fieldErrors` (from `normaliseError()`) into inline `setFieldErrors()`
- Filters out `non_field_errors` key (handled as `generalError`)
- Shows `error.message` (which includes `non_field_errors[0]`) as the
  form-level general error

**Files changed**: `frontend/src/pages/Evidence/AddEvidencePage.tsx`

### 2. AddEvidencePage — Vehicle Payload Fix

**Problem**: The vehicle payload sent `undefined` for the non-selected XOR field
(e.g., if "License Plate" mode was active, `serial_number` was `undefined`).
The backend expects `""` (empty string) since both fields have `default=""`.

**Fix**: Both `license_plate` and `serial_number` are always sent as
`field.trim()` — the empty one becomes `""` naturally. The radio toggle clears
the non-selected field, so after trimming it becomes `""`.

### 3. AddEvidencePage — Vehicle XOR Client Validation

**Problem**: Client-side validation only checked whether the selected mode's
field was empty. It did not catch the case where both fields are filled
(which shouldn't happen via radio toggle but could happen via programmatic
manipulation).

**Fix**: Added XOR validation matching backend error messages:
- Both filled → `_xor: "Provide either a license plate or a serial number, not both."`
- Neither filled → points at the active radio mode's field

### 4. EvidenceListPage — Clear Filter Debounce Fix

**Problem**: Same issue as CaseListPage (fixed in previous patch). Clicking
"Clear" resets `search` to `""` but `debouncedSearch` retains the stale value
for 300ms, causing the old filtered query to persist briefly.

**Fix**: Added `effectiveSearch = search ? debouncedSearch : ""` — when search
is explicitly cleared, the debounced value is bypassed immediately.

**File changed**: `frontend/src/pages/Evidence/EvidenceListPage.tsx`

### 5. Test Infrastructure

- Installed `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`
- Configured Vitest in `vite.config.ts` with jsdom environment
- Added `test` and `test:watch` scripts to `package.json`
- Created `src/test/setup.ts` (jest-dom matchers)

### 6. Unit Tests

| File | Tests |
|------|-------|
| `src/test/AddEvidencePage.test.tsx` | 9 tests: type selector, title validation, vehicle XOR, payload construction, backend field error mapping, navigation on success, identity KV pairs |
| `src/test/EvidenceListPage.test.tsx` | 6 tests: list rendering, clear button visibility, filter reset, case filter passed, loading state, error state |

### 7. Documentation

| File | Contents |
|------|----------|
| `frontend/docs/evidence-polymorphic.md` | Field matrix, example payloads, error mapping guide, file inventory |
| `md-files/evidence-polymorphic-report.md` | This report |

---

## File Inventory

| File | Action |
|------|--------|
| `frontend/src/pages/Evidence/AddEvidencePage.tsx` | Modified (error handling, payload, validation) |
| `frontend/src/pages/Evidence/EvidenceListPage.tsx` | Modified (debounce fix) |
| `frontend/vite.config.ts` | Modified (vitest config) |
| `frontend/package.json` | Modified (test scripts, dev deps) |
| `frontend/src/test/setup.ts` | Created |
| `frontend/src/test/AddEvidencePage.test.tsx` | Created |
| `frontend/src/test/EvidenceListPage.test.tsx` | Created |
| `frontend/docs/evidence-polymorphic.md` | Created |
| `md-files/evidence-polymorphic-report.md` | Created |

---

## Pre-existing (Unmodified) Evidence Files

These files were already complete and correct from Steps 13/14:

| File | Status |
|------|--------|
| `frontend/src/types/evidence.ts` | ✅ Types match backend serializers |
| `frontend/src/api/evidence.ts` | ✅ Complete API layer |
| `frontend/src/hooks/useEvidence.ts` | ✅ All queries + mutations |
| `frontend/src/pages/Evidence/EvidenceDetailPage.tsx` | ✅ Full detail view |
| `frontend/src/lib/evidenceHelpers.ts` | ✅ Labels, colors, icons |
| `frontend/src/pages/Cases/CaseDetailPage.tsx` | ✅ EvidenceSection present |
| `frontend/src/router/Router.tsx` | ✅ Routes configured |

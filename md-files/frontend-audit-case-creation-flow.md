# Frontend Audit: Case Creation Flow (§4.2)

**Date**: 2025-07-24
**Scope**: Comprehensive audit of the Case Creation flow in the frontend against Chapter 4.2 (§4.2.1 Complaint Registration, §4.2.2 Crime Scene Registration) of `project-doc.md`.
**Backend**: Read-only (not modified).

---

## Executive Summary

The audit uncovered **4 critical bugs** that made all review endpoints non-functional and **5 structural gaps** between the frontend and the backend API / project specification. All issues have been fixed. Zero TypeScript errors after fixes (`tsc -b` clean).

---

## Audit Methodology

1. Read project-doc.md Chapter 4.2 (both sub-sections) and Chapter 2 (roles/user levels).
2. Read Swagger YAML (`LA Noire Police Department API.yaml`) for all `/api/cases/` endpoints and their request schemas.
3. Read all backend source code: `models.py`, `views.py`, `serializers.py`, `services.py` (4,400+ lines).
4. Read all frontend case-related source code: 11 files spanning pages, features, services, types, and config.
5. Performed rule-by-rule compliance check.
6. Applied fixes and validated with `tsc -b`.

---

## Critical Bugs Fixed

### BUG-1: API field name mismatch — `action` vs `decision` (CRITICAL)

**Files**: `cases.api.ts`, `CaseReviewActions.tsx`, `ComplainantManager.tsx`

| Component | Frontend sent | Backend expects |
|-----------|---------------|-----------------|
| `cadetReview()` | `{ action: '...' }` | `{ decision: '...' }` |
| `officerReview()` | `{ action: '...' }` | `{ decision: '...' }` |
| `sergeantReview()` | `{ action: '...' }` | `{ decision: '...' }` |
| `reviewComplainant()` | `{ action: '...' }` | `{ decision: '...' }` |
| `transition()` | `{ action: '...' }` | `{ target_status: '...' }` |

**Impact**: Every single review endpoint would return a 400 validation error because the backend `CadetReviewSerializer`, `OfficerReviewSerializer`, `SergeantReviewSerializer`, and `ComplainantReviewSerializer` all define a `decision` field, not `action`. The `CaseTransitionSerializer` defines a `target_status` field.

**Fix**: Changed all `action` keys to `decision` in API service and all calling components. Changed `transition()` to use `target_status`.

### BUG-2: Wrong action value — `'return'` vs `'reject'` (CRITICAL)

**File**: `CaseReviewActions.tsx`

The cadet "Return" and officer "Return" buttons sent `{ action: 'return' }` but the backend serializers only accept `'approve'` or `'reject'` as valid choices.

**Fix**: Changed all `'return'` values to `'reject'`.

### BUG-3: Phantom `'draft'` status (MODERATE)

**Files**: `case.types.ts`, `CasesListPage.tsx`, `CaseReviewActions.tsx`

The frontend defined `CaseStatus.DRAFT = 'draft'` and used it in the status filter dropdown and as a submit trigger. However, the backend `CaseStatus` model has **no `DRAFT` status**. Cases start at `COMPLAINT_REGISTERED` (complaint path) or `PENDING_APPROVAL` (crime-scene path).

**Fix**: Removed `DRAFT` from the `CaseStatus` const object. Removed `'draft'` from `STATUS_OPTIONS`. Changed submit trigger from `status === 'draft' || status === 'complaint_registered'` to just `status === 'complaint_registered'`.

### BUG-4: `CaseCalculations` type wrong (MODERATE)

**File**: `case.types.ts`, `CaseDetailsPage.tsx`

Frontend defined `CaseCalculations` with `total_evidence`, `total_suspects`, `total_witnesses`, `total_complainants`. But the backend `CaseCalculationsSerializer` returns `crime_level_degree`, `days_since_creation`, `tracking_threshold`, `reward_rials`. The detail page rendered completely wrong fields.

**Fix**: Updated the `CaseCalculations` interface to match the backend schema. Updated `CaseDetailsPage.tsx` to render the correct fields: Crime Degree, Days Since Creation, Tracking Threshold, and Reward (Rials).

---

## Structural Gaps Fixed

### GAP-1: No witness input in CaseForm for crime-scene path (§4.2.2)

**Requirement** (§4.2.2): "The officer logs key details — time, date, crime-scene location — and records the national ID and phone number of any witnesses."

**Backend support**: `CrimeSceneCaseCreateSerializer` accepts a `witnesses` nested array with `full_name`, `phone_number`, `national_id` fields.

**Gap**: `CaseForm.tsx` had no witness input fields whatsoever.

**Fix**: Added dynamic witness rows (add/remove) that appear only when `creation_type === 'crime_scene'`. Witnesses are sent as part of the create payload.

### GAP-2: No conditional validation for crime-scene required fields (§4.2.2)

**Requirement**: Crime-scene cases require `incident_date` and `location` (backend enforces via `CrimeSceneCaseCreateSerializer` with `required=True`).

**Gap**: `CaseForm.tsx` treated `incident_date` and `location` as optional for all creation types.

**Fix**: Added client-side validation that enforces `incident_date` and `location` when `creation_type === 'crime_scene'`. Added `required` prop to the corresponding inputs.

### GAP-3: No WitnessManager for post-creation witness management

**Requirement** (§4.2.2): "Witnesses are recorded for crime-scene cases."

**Backend support**: `POST /api/cases/{id}/witnesses/` and `GET /api/cases/{id}/witnesses/` endpoints exist.

**Gap**: No UI component to add/view witnesses on an existing case. The detail page only showed a static read-only list.

**Fix**: Created `WitnessManager.tsx` — a full CRUD component with query fetching, add form, and read-only mode for closed/voided cases. Integrated into `CaseDetailsPage.tsx`.

### GAP-4: Missing `returned_to_cadet` handler in review actions

**Requirement** (§4.2.1): "If the Police Officer rejects, the case goes back to the Cadet (not the complainant)."

**Backend support**: `RETURNED_TO_CADET → OFFICER_REVIEW` is a valid transition in `ALLOWED_TRANSITIONS`.

**Gap**: `CaseReviewActions.tsx` had no action for `returned_to_cadet` status — the Cadet had no button to re-forward the corrected case.

**Fix**: Added "Re-forward to Officer" button that appears when `status === 'returned_to_cadet'` and the user has `CAN_REVIEW_COMPLAINT`. Uses the generic `transition()` endpoint.

### GAP-5: Missing `chief_review` handler for critical cases

**Requirement** (§4.4): "For critical cases, the Captain review forwards to Chief Review before Judiciary."

**Backend support**: `forward_to_judiciary()` service method handles the `CAPTAIN_REVIEW → CHIEF_REVIEW → JUDICIARY` chain for critical cases.

**Gap**: `CaseReviewActions.tsx` had no action for `chief_review` status.

**Fix**: Added "Approve & Forward to Judiciary" button for `chief_review` status, gated by `CAN_APPROVE_CRITICAL_CASE`.

---

## Additional Fixes

### Missing status filter options

**File**: `CasesListPage.tsx`

Added `returned_to_complainant`, `returned_to_cadet`, and `pending_approval` to the filter dropdown. These are real statuses from the backend that were missing from the filter UI.

### Missing permission constants

**File**: `permissions.ts`

Added `VIEW_CASECOMPLAINANT`, `ADD_CASECOMPLAINANT`, `VIEW_CASEWITNESS`, `ADD_CASEWITNESS` to mirror the backend's `CasesPerms` class. These are used by the backend for sub-resource access control.

### Resubmit API signature

**File**: `cases.api.ts`

The `resubmit()` method only accepted `{ description }` but the backend `ResubmitComplaintSerializer` accepts `title`, `description`, `incident_date`, and `location`. Updated to accept all four.

### `ComplainantReviewRequest` type

**File**: `case.types.ts`

Changed field from `action` to `decision` to match backend `ComplainantReviewSerializer`.

---

## Compliance Checklist: §4.2.1 (Complaint Registration)

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| 1 | Complainant submits a complaint form | PASS | `CaseForm` creates with `creation_type: 'complaint'` |
| 2 | Initial status is `complaint_registered` | PASS | Backend sets; frontend `CaseStatus` now correct (no phantom `draft`) |
| 3 | Cadet reviews the complaint | PASS | `cadetReview()` with `{ decision: 'approve'/'reject' }` — **FIXED** |
| 4 | If Cadet finds defects, returns to complainant WITH error message | PASS | `{ decision: 'reject', message }` — **FIXED** from `'return'` |
| 5 | Complainant edits and re-submits | PASS | Resubmit button at `returned_to_complainant` status |
| 6 | If OK, Cadet forwards to Police Officer | PASS | `decision: 'approve'` → `OFFICER_REVIEW` |
| 7 | Officer approves → case opens | PASS | `officerReview({ decision: 'approve' })` — **FIXED** |
| 8 | Officer rejects → returns to CADET (not complainant) | PASS | `officerReview({ decision: 'reject' })` → `RETURNED_TO_CADET` — **FIXED** |
| 9 | Returned-to-cadet: Cadet can re-forward | PASS | New "Re-forward to Officer" button — **ADDED** |
| 10 | 3 rejections → case VOIDED | PASS | Backend auto-voids; frontend shows warning banner — **ADDED** |
| 11 | Multiple complainants allowed | PASS | `ComplainantManager` handles add/review |
| 12 | Each complainant approved/rejected by Cadet | PASS | Per-complainant approve/reject buttons with `decision` — **FIXED** |

## Compliance Checklist: §4.2.2 (Crime Scene Registration)

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| 1 | Police rank (NOT Cadet) registers | PASS | Backend enforces `_CRIME_SCENE_FORBIDDEN_ROLES` |
| 2 | Logs time, date, location | PASS | `incident_date` + `location` now required for crime scene — **FIXED** |
| 3 | Records witness national ID + phone | PASS | Witness inputs now in `CaseForm` — **ADDED** |
| 4 | Witness add after creation | PASS | `WitnessManager` component — **CREATED** |
| 5 | One superior approval needed | PASS | `approveCrimeScene()` endpoint |
| 6 | Police Chief needs NO approval (auto-opens) | PASS | Backend sets `OPEN` directly if `role == police_chief` |
| 7 | Initially no complainant | PASS | No complainant created for crime-scene cases |
| 8 | Complainants can be added later | PASS | `ComplainantManager` works for all case types |

---

## Files Modified

| File | Change Type |
|------|-------------|
| `src/types/case.types.ts` | Removed phantom `DRAFT`, fixed `CaseCalculations`, fixed request DTOs |
| `src/services/api/cases.api.ts` | Fixed `action→decision`, `action→target_status`, expanded resubmit signature |
| `src/features/cases/CaseForm.tsx` | Added witness inputs, conditional validation, crime-scene required fields |
| `src/features/cases/CaseReviewActions.tsx` | Fixed all `action→decision`, `return→reject`, added returned_to_cadet + chief_review handlers |
| `src/features/cases/ComplainantManager.tsx` | Fixed `action→decision` in mutation calls |
| `src/features/cases/WitnessManager.tsx` | **NEW** — full witness management component |
| `src/pages/cases/CaseDetailsPage.tsx` | Integrated WitnessManager, fixed calculations display, added rejection/voided warnings |
| `src/pages/cases/CasesListPage.tsx` | Fixed status filter options |
| `src/config/permissions.ts` | Added missing sub-resource permission constants |

## Validation

- `tsc -b`: **0 errors**
- `get_errors`: **0 errors** across all 9 modified files

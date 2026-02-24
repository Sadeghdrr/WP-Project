# Frontend Audit — Evidence Registration Flow & Entry Routing

**Audit date:** 2025-01-XX  
**Scope:** Chapter 4.3 (Evidence Registration — all five types) + Chapter 5.1 (Application Entry / Home Page)  
**Status:** ✅ All issues resolved — `tsc -b` clean build

---

## 1. Executive Summary

A comprehensive audit of the frontend Evidence Registration flow uncovered **9 bugs** and **2 structural gaps** between the frontend TypeScript code and the backend Django REST Framework serializers. The most critical issue was the Coroner Verification form sending completely wrong fields (`is_verified: boolean` instead of `decision: "approve"|"reject"`), which would cause every verify request to return HTTP 400. All issues have been corrected and validated with a clean TypeScript build.

The entry routing audit (§5.1) confirmed the route configuration is correct (`/` → HomePage via PublicLayout), but identified two UX issues: (1) the home page attempted to fetch authenticated-only stats for anonymous visitors (causing 401 errors), and (2) the PublicLayout navbar lacked a Logout button for authenticated users. Both have been fixed.

---

## 2. Files Modified

| # | File | Changes |
|---|------|---------|
| 1 | `src/types/evidence.types.ts` | Rewrote entire file — fixed 6 type mismatches |
| 2 | `src/features/evidence/CoronerVerificationForm.tsx` | Fixed verify payload; added `decision` + `notes` fields |
| 3 | `src/features/evidence/EvidenceForm.tsx` | Removed phantom fields; added validations + document_details UI |
| 4 | `src/features/evidence/EvidenceTable.tsx` | Fixed `registered_by` display; removed phantom column |
| 5 | `src/features/evidence/EvidenceCard.tsx` | Fixed all field references; custody_log via prop; added doc_details |
| 6 | `src/pages/evidence/EvidenceDetailPage.tsx` | Added file upload, separate custody log fetch |
| 7 | `src/pages/home/HomePage.tsx` | Conditional stats fetch; auth-aware CTAs |
| 8 | `src/components/layout/PublicLayout.tsx` | Added Logout button for authenticated users |

---

## 3. Bug Register

### BUG-1 — Coroner Verification API Payload Mismatch (CRITICAL)

| Attribute | Detail |
|-----------|--------|
| **Severity** | 🔴 Critical — every verify request would 400 |
| **File** | `CoronerVerificationForm.tsx` |
| **Root Cause** | Frontend sent `{ forensic_result, is_verified: boolean }` but backend `VerifyBiologicalEvidenceSerializer` expects `{ decision: "approve"\|"reject", forensic_result, notes }` |
| **Fix** | Replaced `is_verified` boolean with `decision` string enum; added `notes` textarea (required on reject) |
| **Spec ref** | §4.3.2 |

### BUG-2 — EvidenceListItem Phantom Fields

| Attribute | Detail |
|-----------|--------|
| **Severity** | 🟡 Medium — would render `undefined` values in table/cards |
| **File** | `evidence.types.ts` |
| **Root Cause** | Frontend type had `collection_date`, `verification_status`, `location` — none returned by backend `EvidenceListSerializer` |
| **Fix** | Removed all three fields; added `evidence_type_display`, `registered_by_name`, `updated_at` |

### BUG-3 — registered_by Type Mismatch (CRASH)

| Attribute | Detail |
|-----------|--------|
| **Severity** | 🔴 Critical — runtime crash on any evidence list/detail view |
| **File** | `evidence.types.ts`, `EvidenceTable.tsx`, `EvidenceCard.tsx` |
| **Root Cause** | Frontend expected `registered_by: UserListItem` (object with `first_name`, `last_name`), but backend returns `registered_by: number` (PK) + `registered_by_name: string` |
| **Fix** | Changed type to `registered_by: number` + `registered_by_name: string \| null`. Updated all render sites to use `registered_by_name` |

### BUG-4 — EvidenceCreateRequest Phantom Fields

| Attribute | Detail |
|-----------|--------|
| **Severity** | 🟡 Medium — backend would silently ignore, but form showed non-functional inputs |
| **File** | `evidence.types.ts`, `EvidenceForm.tsx` |
| **Root Cause** | `collection_date` and `location` sent in create payload but not accepted by any backend create serializer |
| **Fix** | Removed from type + form; removed Collection Date and Location inputs |

### BUG-5 — Vehicle Form Missing Required Fields + XOR

| Attribute | Detail |
|-----------|--------|
| **Severity** | 🟠 High — backend would reject incomplete submissions |
| **File** | `EvidenceForm.tsx` |
| **Root Cause** | Backend `VehicleEvidenceCreateSerializer` requires `vehicle_model` (required=True) and `color` (required=True), and enforces XOR on `license_plate`/`serial_number`. Frontend made all optional with no client-side validation. |
| **Fix** | Marked `vehicle_model` and `color` as required; added XOR validation with clear error message |
| **Spec ref** | §4.3.3 |

### BUG-6 — Identity Form Missing document_details UI

| Attribute | Detail |
|-----------|--------|
| **Severity** | 🟠 High — violates documented spec |
| **File** | `EvidenceForm.tsx` |
| **Root Cause** | Backend `IdentityEvidenceCreateSerializer` accepts `document_details` (JSON key-value object). Frontend only showed `owner_full_name` input. |
| **Fix** | Added dynamic key-value pairs UI with Add/Remove functionality |
| **Spec ref** | §4.3.4 |

### BUG-7 — Testimony statement_text Not Required

| Attribute | Detail |
|-----------|--------|
| **Severity** | 🟡 Medium — backend `_validate_testimony` rejects empty statement |
| **File** | `EvidenceForm.tsx` |
| **Root Cause** | Frontend did not mark `statement_text` as required |
| **Fix** | Added `required` prop and client-side validation |
| **Spec ref** | §4.3.1 |

### BUG-8 — EvidenceDetail.custody_log Assumed Inline (CRASH)

| Attribute | Detail |
|-----------|--------|
| **Severity** | 🔴 Critical — `evidence.custody_log.length` on undefined causes crash |
| **File** | `evidence.types.ts`, `EvidenceCard.tsx`, `EvidenceDetailPage.tsx` |
| **Root Cause** | Frontend type included `custody_log: EvidenceCustodyLog[]` on `EvidenceDetail`, but backend detail serializers do NOT embed custody log. It's a separate endpoint `GET /api/evidence/{id}/chain-of-custody/`. |
| **Fix** | Removed `custody_log` from `EvidenceDetail`. `EvidenceCard` now accepts `custodyLog` as optional prop. `EvidenceDetailPage` fetches custody log via separate `useQuery`. |

### BUG-9 — EvidenceCustodyLog Field Name Mismatches

| Attribute | Detail |
|-----------|--------|
| **Severity** | 🟠 High — all custody log rendering would show wrong data |
| **File** | `evidence.types.ts`, `EvidenceCard.tsx` |
| **Root Cause** | Frontend fields: `handled_by: UserListItem`, `action_type: CustodyAction`, `notes: string`. Backend fields: `performed_by: number`, `performer_name: string`, `action: string`, `details: string`. |
| **Fix** | Corrected all field names in type and rendering code |

---

## 4. Structural Gaps Closed

### GAP-1 — No File Upload UI

| Attribute | Detail |
|-----------|--------|
| **Spec ref** | §4.3.1 (testimony: images/videos/audio), §4.3.2 (biological: one or more images) |
| **Problem** | Backend has `POST /api/evidence/{id}/files/` endpoint with multipart support. Frontend had `evidenceApi.uploadFile()` wired but zero UI to invoke it. |
| **Fix** | Added file upload form in `EvidenceDetailPage.tsx` with file picker, file-type selector, caption input, and upload button. Protected behind `CAN_REGISTER_FORENSIC_RESULT` permission. |

### GAP-2 — EvidenceUpdateRequest Phantom Fields

| Attribute | Detail |
|-----------|--------|
| **Problem** | Had `collection_date` and `location` not in any backend update serializer |
| **Fix** | Removed; added type-specific update fields (statement_text, vehicle fields, identity fields) matching backend |

---

## 5. Evidence Type Compliance Checklist (§4.3)

### §4.3.1 — Testimony Evidence

| Requirement | Status | Notes |
|-------------|--------|-------|
| `statement_text` field | ✅ | Now marked required; validated client-side |
| File attachments (image/video/audio) | ✅ | File upload UI added to detail page |
| Create via `POST /api/evidence/` with `evidence_type: "testimony"` | ✅ | Correct endpoint + payload |

### §4.3.2 — Biological Evidence

| Requirement | Status | Notes |
|-------------|--------|-------|
| `forensic_result` set by Coroner | ✅ | Via CoronerVerificationForm → `POST .../verify/` |
| Verify sends `{ decision, forensic_result, notes }` | ✅ | Fixed from `{ is_verified, forensic_result }` |
| `is_verified` boolean on detail response | ✅ | Displayed as badge in EvidenceCard |
| `verified_by` / `verified_by_name` | ✅ | Type corrected from UserListItem to number + string |
| File attachments (one or more images) | ✅ | File upload UI available on detail page |
| Notes required on rejection | ✅ | Client-side validation added |

### §4.3.3 — Vehicle Evidence

| Requirement | Status | Notes |
|-------------|--------|-------|
| `vehicle_model` required | ✅ | Marked required; validated client-side |
| `color` required | ✅ | Marked required; validated client-side |
| `license_plate` XOR `serial_number` | ✅ | Client-side XOR validation with error message |
| Display in EvidenceCard | ✅ | Model, Color, Plate, Serial |

### §4.3.4 — Identity Evidence

| Requirement | Status | Notes |
|-------------|--------|-------|
| `owner_full_name` required | ✅ | Marked required; validated client-side |
| `document_details` dynamic key-value | ✅ | Added key-value pair UI with add/remove |
| Display document_details in EvidenceCard | ✅ | Rendered as definition list |

### §4.3.5 — Other Evidence

| Requirement | Status | Notes |
|-------------|--------|-------|
| Only base fields (title, description, case) | ✅ | No extra type-specific fields |

---

## 6. API Endpoint Mapping

| Frontend Method | HTTP | Path | Status |
|----------------|------|------|--------|
| `evidenceApi.list()` | GET | `/api/evidence/` | ✅ |
| `evidenceApi.detail(id)` | GET | `/api/evidence/{id}/` | ✅ |
| `evidenceApi.create(data)` | POST | `/api/evidence/` | ✅ Fixed payload |
| `evidenceApi.update(id, data)` | PATCH | `/api/evidence/{id}/` | ✅ Fixed type |
| `evidenceApi.delete(id)` | DELETE | `/api/evidence/{id}/` | ✅ |
| `evidenceApi.verify(id, data)` | POST | `/api/evidence/{id}/verify/` | ✅ Fixed payload |
| `evidenceApi.listFiles(id)` | GET | `/api/evidence/{id}/files/` | ✅ |
| `evidenceApi.uploadFile(id, fd)` | POST | `/api/evidence/{id}/files/` | ✅ Added UI |
| `evidenceApi.chainOfCustody(id)` | GET | `/api/evidence/{id}/chain-of-custody/` | ✅ Added query |
| `evidenceApi.linkCase(id, data)` | POST | `/api/evidence/{id}/link-case/` | ✅ |
| `evidenceApi.unlinkCase(id, data)` | POST | `/api/evidence/{id}/unlink-case/` | ✅ |

---

## 7. Entry Routing Corrections (§5.1)

### Route Configuration

| Route | Layout | Component | Status |
|-------|--------|-----------|--------|
| `/` | PublicLayout | HomePage | ✅ Correct — home page is default |
| `/login` | AuthLayout | LoginPage | ✅ |
| `/register` | AuthLayout | RegisterPage | ✅ |
| `/dashboard` | ProtectedRoute → DashboardLayout | DashboardPage | ✅ |

### Fixes Applied

| Issue | Fix |
|-------|-----|
| HomePage fetched stats via authenticated endpoint for all visitors → 401 error for anonymous users | Wrapped stats query with `enabled: isAuthenticated`; show "Sign in to view" for anon |
| PublicLayout showed "Dashboard" link for authenticated users but no Logout | Added Logout button next to Dashboard link |
| Hero CTA always showed "Sign In" even for logged-in users | Now shows "Go to Dashboard" for authenticated, "Sign In" for anonymous |

---

## 8. Type Safety Summary

| Type | Fields Corrected |
|------|-----------------|
| `EvidenceListItem` | Removed `collection_date`, `verification_status`, `location`; changed `registered_by` from UserListItem to number; added `evidence_type_display`, `registered_by_name`, `updated_at` |
| `EvidenceDetail` | Removed `custody_log`; changed `verified_by` from UserListItem to number; added `verified_by_name` |
| `EvidenceCreateRequest` | Removed `collection_date`, `location` |
| `EvidenceUpdateRequest` | Removed `collection_date`, `location`; added type-specific update fields |
| `EvidenceVerifyRequest` | Changed from `{ forensic_result, is_verified }` to `{ decision, forensic_result, notes }` |
| `EvidenceCustodyLog` | Changed `handled_by` → `performed_by`, `action_type` → `action`, `notes` → `details`; added `performer_name` |
| `EvidenceFile` | Added optional `file_type_display` |

---

## 9. Build Validation

```
$ tsc -b
(no output — zero errors)
```

All changes compile cleanly with strict TypeScript. No `UserListItem` import remaining in `evidence.types.ts`.

---

## 10. Remaining Recommendations

1. **Backend public stats endpoint**: The dashboard stats endpoint (`GET /api/core/dashboard/`) requires authentication. To show stats to anonymous visitors on the home page, the backend should expose a public subset endpoint (e.g., `GET /api/core/public-stats/` with `AllowAny` permission).

2. **File upload permission**: Currently gated behind `CAN_REGISTER_FORENSIC_RESULT`. Consider adding a dedicated `CAN_UPLOAD_EVIDENCE_FILE` permission for finer-grained control.

3. **Custody log add entry**: The `POST /api/evidence/{id}/chain-of-custody/` endpoint exists in the backend but has no UI form for adding entries. Consider adding a custody log entry form.

4. **Evidence edit form**: `EvidenceUpdateRequest` now includes type-specific fields but there is no dedicated Edit Evidence form/page — only the create form exists.

5. **Evidence list filters**: The `EvidenceFilterParams` type supports `evidence_type`, `case`, and `is_verified` filters, but the evidence list page does not expose filter controls.

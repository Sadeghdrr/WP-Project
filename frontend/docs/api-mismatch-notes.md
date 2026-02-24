# API Mismatch Notes — Doc vs. Backend Source Code

> When docs and backend code disagree, **backend code wins** for the frontend API contract.
> Generated: 2026-02-25

---

## 1. Accounts App

### 1.1 Login Architecture Contradicts Doc

- **Doc** (`accounts_api_report.md` §3): States custom Django auth backend was explicitly rejected. Describes login as `LoginRequestSerializer` → `AuthenticationService.authenticate()`.
- **Code** (`accounts/views.py`, `accounts/backends.py`): Uses `CustomTokenObtainPairSerializer` (extending SimpleJWT's `TokenObtainPairSerializer`) and a `MultiFieldAuthBackend` custom auth backend.
- **Impact on frontend:** None — the request/response shape is the same (`{ identifier, password }` → `{ access, refresh, user }`). The architectural difference is backend-internal.
- **Source used:** Backend code.

### 1.2 `LoginRequestSerializer` is Dead Code

- **Doc** (`accounts_api_report.md`): Describes `LoginRequestSerializer` as the login serializer.
- **Code** (`accounts/serializers.py`): `LoginRequestSerializer` exists but is never used. `LoginView` uses `CustomTokenObtainPairSerializer`.
- **Impact on frontend:** None — use the actual endpoint behavior, not the unused serializer.
- **Source used:** Backend code.

### 1.3 JWT Claims Not Documented

- **Doc** (`accounts_api_report.md`): Only describes getting permissions via `GET /me/`.
- **Code** (`accounts/serializers.py` L151–164): `CustomTokenObtainPairSerializer.get_token()` injects `role`, `hierarchy_level`, `permissions_list` into the JWT access token payload.
- **Impact on frontend:** Frontend can decode the JWT to get role/permissions without an API call. Useful for client-side routing and guard checks.
- **Source used:** Backend code. **Frontend should use JWT claims for quick auth checks, and `/me/` for full profile data.**

---

## 2. Cases App

### 2.1 Undocumented `GET /api/cases/{id}/report/` Endpoint

- **Doc** (`cases_api_report.md`): Lists 26 endpoints. No `report` endpoint.
- **Code** (`cases/views.py` L1050–1085): A 27th endpoint exists — `@action(detail=True, methods=["get"], url_path="report")` backed by `CaseReportingService`. Returns full aggregated case report (case + personnel + complainants + witnesses + evidence + suspects with interrogations/trials + status history + calculations).
- **Impact on frontend:** Critical for the **General Reporting** page (§5.7). Must use this endpoint.
- **Source used:** Backend code.

### 2.2 Undocumented `CaseReportSerializer` + 10 Nested Serializers

- **Doc**: Lists 19 serializers for cases.
- **Code** (`cases/serializers.py` L607–777): 11 additional serializers for the report endpoint exist in code but not in docs.
- **Impact on frontend:** Must build types matching the actual response shape from code.
- **Source used:** Backend code.

---

## 3. Evidence App

### 3.1 Swagger Filter Param Names Don't Match Actual Fields

- **Swagger/Doc params**: `verification_status`, `collected_after`, `collected_before`
- **Actual filter fields** (`evidence/serializers.py` `EvidenceFilterSerializer`): `is_verified` (bool), `created_after`, `created_before`
- **Impact on frontend:** Use the **actual** field names (`is_verified`, `created_after`, `created_before`), NOT the Swagger-documented ones.
- **Source used:** Backend code.

### 3.2 Undocumented `registered_by` Filter

- **Doc**: Not mentioned.
- **Code** (`evidence/serializers.py` L62): `registered_by` query param accepts a user PK integer.
- **Impact on frontend:** Useful for filtering evidence by registrar on the Evidence Review page.
- **Source used:** Backend code.

### 3.3 Verify Response Example Omits 3 Fields

- **Doc** (`evidence_api_report.md`): Shows 11 fields in verify response.
- **Code** (`evidence/serializers.py` L193–222): `BiologicalEvidenceDetailSerializer` has 14 fields. Missing from doc: `description`, `evidence_type_display`, `registered_by`, `registered_by_name`.
- **Impact on frontend:** These fields are available in the response; use them.
- **Source used:** Backend code.

---

## 4. Suspects App

### 4.1 ⚠ CRITICAL: URL Double-Prefix Bug

- **Doc** (`suspects_api_report.md`): Lists endpoints at `/api/suspects/`, `/api/suspects/{id}/`, etc.
- **Code**: Root `urls.py` mounts suspects at `path('api/suspects/', include('suspects.urls'))`, but `suspects/urls.py` registers the router with `prefix=r"suspects"`. This results in **doubled** prefix.
- **Actual runtime URLs:**
  - `/api/suspects/suspects/` (not `/api/suspects/`)
  - `/api/suspects/suspects/{id}/` (not `/api/suspects/{id}/`)
  - `/api/suspects/suspects/most-wanted/` (not `/api/suspects/most-wanted/`)
  - `/api/suspects/suspects/{suspect_pk}/interrogations/` etc.
  - `/api/suspects/bounty-tips/` (this one is correct — bounty-tips prefix doesn't conflict)
- **Root cause:** Every other app uses `path('api/', include('app.urls'))` and lets the router add the prefix. Suspects uses `path('api/suspects/', ...)` but the router **also** adds `suspects/`.
- **Impact on frontend:** Frontend must use the **doubled** URL paths until backend is fixed. The api-contract.md documents the actual runtime paths.
- **Source used:** Backend code. **This is a backend bug that should be reported and fixed.** Either change root `urls.py` to `path('api/', include('suspects.urls'))` or change the router prefix to `r""`.

### 4.2 Undocumented `POST .../suspects/{id}/captain-verdict/`

- **Doc** (`suspects_api_report.md`): Lists 9 suspect endpoints. No captain-verdict.
- **Code** (`suspects/views.py` L762–819): `@action(detail=True, methods=["post"], url_path="captain-verdict")` backed by `VerdictService.submit_captain_verdict()`.
- **Impact on frontend:** Critical for the Captain's verdict workflow. Documented in api-contract.md §7.
- **Source used:** Backend code.

### 4.3 Undocumented `POST .../suspects/{id}/chief-approval/`

- **Doc**: Not mentioned.
- **Code** (`suspects/views.py` L821–878): `@action(detail=True, methods=["post"], url_path="chief-approval")` backed by `VerdictService.process_chief_approval()`.
- **Impact on frontend:** Critical for critical-crime workflow where Police Chief must approve Captain's verdict.
- **Source used:** Backend code.

### 4.4 Undocumented `VerdictService` + 2 Serializers

- **Doc**: Lists `ArrestAndWarrantService` as the main workflow service. No mention of `VerdictService`.
- **Code** (`suspects/views.py` L85): Imports `VerdictService`, `CaptainVerdictSerializer`, `ChiefApprovalSerializer`.
- **Impact on frontend:** Must build request types matching these serializers.
- **Source used:** Backend code.

### 4.5 Bounty Tips URL — Not Top-Level

- **Doc** (`suspects_api_report.md`): Labels bounty tips as "Top-Level" at `/api/bounty-tips/`.
- **Code**: Due to `path('api/suspects/', include('suspects.urls'))`, bounty tips resolve to `/api/suspects/bounty-tips/`.
- **Impact on frontend:** Use `/api/suspects/bounty-tips/...` for all bounty tip API calls.
- **Source used:** Backend code.

---

## 5. Board App

### 5.1 Undocumented `PUT /api/boards/{id}/`

- **Doc** (`board_api_report.md`): Only documents PATCH for board updates.
- **Code**: `DetectiveBoardViewSet` extends `ModelViewSet`, which exposes both PUT and PATCH.
- **Impact on frontend:** Prefer PATCH (partial updates). PUT is available but undocumented.
- **Source used:** Backend code.

---

## 6. Core App

### 6.1 Undocumented Notification Endpoints

- **Doc** (`core_api_report.md`): Lists 3 endpoints only (dashboard, search, constants).
- **Code** (`core/urls.py`, `core/views.py`): `NotificationViewSet` provides 2 additional endpoints:
  - `GET /api/core/notifications/`
  - `POST /api/core/notifications/{id}/read/`
- **Impact on frontend:** Critical for the notification system required by §4.4 (notify Detective on new evidence).
- **Source used:** Backend code.

---

## Summary of Resolution Approach

| Mismatch Type | Count | Resolution |
|---|---|---|
| Doc describes wrong/unused code | 3 | Use backend code behavior |
| Endpoint exists in code but missing from doc | 7 | Documented in api-contract.md from code |
| Filter/field name mismatch (Swagger vs. actual) | 2 | Use actual serializer field names |
| URL routing bug (double prefix) | 1 | Document actual runtime URLs; report as backend bug |
| **Total mismatches** | **13** | All resolved by using backend code as source of truth |

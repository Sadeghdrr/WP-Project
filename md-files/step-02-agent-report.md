# Step 02 Agent Report — Frontend API Contract Inventory

> Agent run: 2026-02-25 | Branch: `agent/step-02-api-contract-inventory`

---

## 1. Files Created / Changed

| File | Action | Description |
|---|---|---|
| `frontend/docs/api-contract.md` | Created | Frontend-facing API contract inventory organized by feature/page, 101 endpoints documented |
| `frontend/docs/api-mismatch-notes.md` | Created | 13 doc-vs-code mismatches catalogued with resolution approach |
| `md-files/step-02-agent-report.md` | Created | This report |

**No backend files were modified.** ✅

---

## 2. APIs Inventoried (by Feature)

| Feature/Page | Endpoints | Key Endpoints |
|---|---|---|
| Auth & User Profile | 5 | register, login, token refresh, me (get/patch) |
| Admin Panel (User/Role/Permission) | 12 | user CRUD + activate/deactivate/assign-role, role CRUD + assign-permissions, permission list |
| Home Page / Dashboard | 1 | dashboard stats (total cases, employees, active cases, breakdowns) |
| Case & Complaint Management | 27 | case CRUD, 9 workflow actions, 5 assignment actions, sub-resources (complainants, witnesses, status-log, calculations, report) |
| Evidence Registration & Review | 11 | evidence CRUD (polymorphic), verify, link/unlink case, file upload/list, chain-of-custody |
| Detective Board | 15 | board CRUD, full-state, items (pin/remove/batch-coordinates), connections (add/remove), notes CRUD |
| Suspects & Most Wanted | 10 | suspect CRUD, most-wanted list, approve, issue-warrant, arrest, transition, captain-verdict, chief-approval |
| Interrogation & Trial | 6 | interrogation CRUD, trial CRUD (nested under suspects) |
| Bounty Tips | 6 | tip CRUD, officer review, detective verify, reward lookup |
| Bail & Payment (Optional) | 4 | bail CRUD, payment |
| Notifications | 2 | list, mark-as-read |
| System Constants & Search | 2 | constants (public), global search |
| **Total** | **101** | |

---

## 3. Backend Anomalies / Problems Found

### 3.1 ⚠ CRITICAL: Suspects App URL Double-Prefix Bug

Root `urls.py` mounts suspects at `path('api/suspects/', include('suspects.urls'))`, but `suspects/urls.py` registers the router with `prefix=r"suspects"`. This produces doubled URLs:
- **Expected:** `/api/suspects/`, `/api/suspects/{id}/`
- **Actual:** `/api/suspects/suspects/`, `/api/suspects/suspects/{id}/`

All other apps (cases, evidence, board) use `path('api/', ...)` and let the router add the prefix. Suspects is the only one that conflicts.

**Recommendation:** Fix in backend by either changing root `urls.py` to `path('api/', include('suspects.urls'))` OR changing the router prefix in `suspects/urls.py` to `r""`. **Not fixed — reported only.**

### 3.2 Evidence Swagger Params Don't Match Actual Filter Fields

Swagger `@extend_schema` on evidence list declares: `verification_status`, `collected_after`, `collected_before`.
Actual `EvidenceFilterSerializer` uses: `is_verified`, `created_after`, `created_before`.

Frontend must use the actual serializer names. Swagger docs will confuse API consumers.

### 3.3 Dead Code: `LoginRequestSerializer`

`LoginRequestSerializer` is defined in `accounts/serializers.py` and imported in `accounts/views.py` but never actually used by any view. The login view uses `CustomTokenObtainPairSerializer` instead.

### 3.4 Seven Endpoints Missing from md-files/ Docs

| Endpoint | App | Impact |
|---|---|---|
| `GET /api/cases/{id}/report/` | cases | High — needed for General Reporting page |
| `POST .../suspects/{id}/captain-verdict/` | suspects | High — Captain verdict workflow |
| `POST .../suspects/{id}/chief-approval/` | suspects | High — Chief approval for critical cases |
| `GET /api/core/notifications/` | core | High — notification system |
| `POST /api/core/notifications/{id}/read/` | core | High — notification system |
| `PUT /api/boards/{id}/` | board | Low — implicit via ModelViewSet |
| `registered_by` filter on evidence list | evidence | Low — undocumented query param |

---

## 4. Traceability: Frontend Feature → API Endpoints

### Covered ✅

| Frontend Feature (§5/§7) | Mapped Endpoints | Status |
|---|---|---|
| **Home Page** (§5.1) | `GET /api/core/dashboard/` — provides total_cases, active_cases, total_employees + more | ✅ Full coverage |
| **Login & Registration** (§5.2) | `POST .../auth/register/`, `POST .../auth/login/`, `POST .../auth/token/refresh/` | ✅ Full coverage |
| **Modular Dashboard** (§5.3) | `GET /api/accounts/me/` (role detection), `GET /api/core/dashboard/` (stats), `GET /api/core/notifications/` (badge) | ✅ Full coverage |
| **Detective Board** (§5.4) | `GET .../boards/{id}/full/` (full state), items CRUD, connections CRUD, notes CRUD, batch-coordinates | ✅ Full coverage |
| **Most Wanted** (§5.5) | `GET .../suspects/most-wanted/` — ranking + bounty computed server-side | ✅ Full coverage |
| **Case & Complaint Status** (§5.6) | Case CRUD + 9 workflow actions + complainants/witnesses sub-resources + status-log | ✅ Full coverage |
| **General Reporting** (§5.7) | `GET /api/cases/{id}/report/` — full aggregated report | ✅ Full coverage |
| **Evidence Registration & Review** (§5.8) | Evidence CRUD (5 types) + verify + file upload + chain-of-custody | ✅ Full coverage |
| **Admin Panel** (§7) | User management (list/activate/deactivate/assign-role), Role CRUD, Permission assignment | ✅ Full coverage |
| **Registration & Login flow** (§4.1) | Auth endpoints | ✅ |
| **Complaint flow** (§4.2.1) | submit → cadet-review → officer-review (with rejection messages) | ✅ |
| **Crime Scene flow** (§4.2.2) | Create with witnesses → approve-crime-scene | ✅ |
| **Evidence flow** (§4.3) | 5 evidence subtypes + file upload + Coroner verify | ✅ |
| **Case solving flow** (§4.4) | Detective board + declare-suspects + sergeant-review + notifications | ✅ |
| **Suspect identification & interrogation** (§4.5) | Suspect CRUD + interrogation CRUD + captain-verdict + chief-approval | ✅ |
| **Trial** (§4.6) | Trial CRUD (Judge records verdict + punishment) + case report for Judge | ✅ |
| **Suspect status / Most Wanted** (§4.7) | most-wanted endpoint (score + reward computed) | ✅ |
| **Bounty** (§4.8) | Bounty tips: submit → officer review → detective verify → reward lookup | ✅ |
| **Bail & Payment** (§4.9, optional) | Bail CRUD + pay action | ✅ (optional) |
| **Notifications** (§4.4) | `GET /api/core/notifications/`, `POST .../read/` | ✅ Polling-based |
| **System constants for dropdowns** | `GET /api/core/constants/` (public) | ✅ |
| **Global search** | `GET /api/core/search/` | ✅ |

### No Endpoint Needed

| Feature | Reason |
|---|---|
| Loading/skeleton states (§7, 300 pts) | Frontend-only UI concern |
| Responsive design (§7, 300 pts) | Frontend-only CSS concern |
| Docker Compose (§7, 300 pts) | Infrastructure concern |
| Frontend tests (§7, 100 pts) | Test framework concern |
| State management (§7, 100 pts) | Frontend architecture concern |
| Component lifecycles (§7, 100 pts) | Frontend code quality concern |
| Error messages (§7, 100 pts) | Frontend UX + API error responses |
| Board image export (§5.4) | Client-side canvas rendering |

### Potentially Unclear ⚠️

| Item | Note |
|---|---|
| Most Wanted public access | Backend requires auth. Doc says "visible to all users." Base User can see it, but unauthenticated users cannot. |
| Board export as image | No backend endpoint needed — use client-side HTML canvas/SVG export. |
| 3-strike complaint voiding | Backend tracks `rejection_count` on Case model and auto-voids. Frontend needs to display the counter. |
| Detective notifications on new evidence | Backend creates notifications via `NotificationService`. Frontend must poll `GET /api/core/notifications/`. |

---

## 5. Confirmation

- ✅ No backend files were modified
- ✅ All changes limited to `frontend/docs/` and `md-files/`
- ✅ Backend code was used as the runtime source of truth
- ✅ 13 doc-vs-code mismatches documented and resolved
- ✅ 1 critical backend bug identified (URL double-prefix) — reported only, not fixed
- ✅ All 9 frontend pages from §7 have mapped API endpoints
- ✅ All 10 flows from §4 have mapped API endpoints

# Step 01 Agent Report — Frontend Requirements Matrix

> Agent run: 2026-02-25 | Branch: `agent/step-01-frontend-requirements-matrix`

---

## 1. Files Created / Changed

| File | Action | Description |
|---|---|---|
| `frontend/docs/requirements-matrix.md` | Created | Full requirements & scoring matrix organized by page, flow, cross-cutting concern, and constraint |
| `frontend/docs/frontend-scope-summary.md` | Created | Concise execution-focused summary of frontend deliverables |
| `md-files/step-01-agent-report.md` | Created | This report |

**No backend files were modified.** ✅

---

## 2. Summary of Extracted Requirements

### Pages (9 total, 3000 pts)
1. Home Page (200 pts) — intro + 3 live statistics
2. Login & Registration (200 pts) — full auth flow
3. Modular Dashboard (800 pts) — role-based module visibility
4. Detective Board (800 pts) — interactive canvas with drag-drop, red lines, image export
5. Most Wanted (300 pts) — ranked list with photos and bounty
6. Case & Complaint Status (200 pts) — case lifecycle management
7. General Reporting (300 pts) — full case reports for Judge/Captain/Chief
8. Evidence Registration & Review (200 pts) — 5 evidence subtypes
9. Admin Panel (200 pts) — user/role/permission management (React-based)

### Cross-Cutting (1550 pts)
- Loading/skeletons (300), Docker Compose (300), Responsive (300), Best practices (150), State management (100), Tests ≥5 (100), Lifecycles (100), Error messages (100), Code modifiability (100)

### Constraints
- Max 6 runtime NPM packages (currently 2 used)
- ≥15 commits required
- Dynamic role management (no code changes to add/remove roles)

### Optional
- Bail payment UI (§4.9 — explicitly optional in project doc)

---

## 3. Ambiguity Resolution Log

### A1 — Admin Panel (scored but not detailed in Ch. 5)
- **Finding:** Admin Panel appears in §7 scoring (200 pts) but has no dedicated section in §5 (Required Pages).
- **Backend support:** Full custom admin API exists — user management, role CRUD, permission assignment via `/api/accounts/users/`, `/api/accounts/roles/`, `/api/accounts/permissions/`.
- **Resolution:** Implement minimal admin panel: user list with activate/deactivate/assign-role, role CRUD, permission picker. No invented features.

### A2 — Most Wanted Ranking Formula
- **Finding:** Project doc describes `score = max_days_wanted × highest_crime_degree`. An image reference for the formula exists but is missing from the translated doc.
- **Backend support:** Formula implemented exactly as described in `suspects/models.py` (model property) and `core/services.py` (`RewardCalculatorService`). Eligibility threshold: 30 days.
- **Resolution:** Frontend displays backend-computed score. No frontend calculation needed. Formula is deterministic and matches text.

### A3 — Bounty Calculation Formula
- **Finding:** Project doc references a formula (likely in a missing image). Text says bounty is "calculated using the following formula" but the formula itself is absent from translated doc.
- **Backend support:** `reward = score × 20,000,000 Rials` where `score = max_days_wanted × max_crime_degree`. Implemented in `core/services.py` and served as `computed_reward` in the most-wanted API response.
- **Resolution:** Frontend displays `computed_reward` from backend. No business logic in frontend. The multiplier (20M Rials) is a backend constant.

### A4 — Bail Payment (Optional)
- **Finding:** §4.9 explicitly says "(Optional)". CP1 scoring includes 200 pts for payment gateway, but CP2 has no separate bail line item.
- **Backend support:** Full bail model + endpoints exist (`POST /api/suspects/{id}/bails/`, `/pay/` action). Payment is stub-level (accepts reference string, no real gateway SDK).
- **Resolution:** Optional. Implement bail status display + payment form if time permits. Backend is ready. Does NOT block CP2 scoring.

### A5 — Detective Notifications
- **Finding:** §4.4 states "a notification must be sent to the Detective" when new evidence is added to a case. No specific mechanism (WebSocket, SSE, polling) is prescribed.
- **Backend support:** `Notification` model exists in `core/models.py`. REST endpoints: `GET /api/core/notifications/`, `POST /api/core/notifications/{id}/read/`. Notifications created for: suspect approval, warrant issuance, arrest, evidence registration. **Polling only — no WebSocket.**
- **Resolution:** Implement polling-based notification system. Show notification badge/list in dashboard. Poll at reasonable interval (e.g., 30s). No fake real-time.

### A6 — Dashboard Role Mapping
- **Finding:** §5.3 says dashboard must be "modular" with modules shown by access level, but does not enumerate exactly which modules per role.
- **Backend support:** 15 roles defined with hierarchy levels (0–100) and granular permissions. Role→permission mapping in `setup_rbac.py`.
- **Resolution:** Created role→module mapping table in requirements-matrix.md derived from role descriptions (§3.1), flow responsibilities (§4.x), and page descriptions (§5.x). Dashboards = navigation + summary only; each module links to the corresponding page/action.

### A7 — "Visible to all users" (Most Wanted)
- **Finding:** §4.7 says most wanted details are "placed on a page visible to all users."
- **Backend support:** `SuspectViewSet` requires `IsAuthenticated`. The `most_wanted` action does NOT override to `AllowAny`. Base User role has `VIEW_SUSPECT` permission.
- **Resolution:** "All users" means all **authenticated** users, including Base User. Unauthenticated access is NOT supported by the backend. Minor gap: if truly public access is desired, backend endpoint would need `AllowAny`. Documented as anomaly — not fixing backend.

### A8 — Max 6 NPM Packages
- **Finding:** §1.4 says "a maximum of 6 NPM packages used in the project."
- **Resolution:** Counts runtime `dependencies` only. The following are EXCLUDED from the count:
  - `react`, `react-dom` (framework, analogous to Django itself)
  - `vite`, `typescript`, `@vitejs/plugin-react-swc` (build tooling)
  - `eslint` and eslint plugins (dev tooling)
  - All `devDependencies`
- Current count: **0** countable packages (react/react-dom are framework). **6 slots available.**
- Enforcement: Track in `package.json` before adding any dependency.

---

## 4. Coverage Verification

### Covered ✅
| Item | Status |
|---|---|
| Home Page (§5.1) | Fully covered — HP-1 through HP-3 |
| Login & Registration (§5.2, §4.1) | Fully covered — LR-1 through LR-4 |
| Modular Dashboard (§5.3) | Fully covered — MD-1 through MD-4 + role mapping table |
| Detective Board (§5.4, §4.4) | Fully covered — DB-1 through DB-8 |
| Most Wanted (§5.5, §4.7) | Fully covered — MW-1 through MW-6 |
| Case & Complaint Status (§5.6, §4.2) | Fully covered — CS-1 through CS-8 |
| General Reporting (§5.7, §4.6) | Fully covered — GR-1 through GR-4 |
| Evidence Registration & Review (§5.8, §4.3) | Fully covered — ER-1 through ER-8 |
| Admin Panel (§7) | Fully covered — AP-1 through AP-5 |
| All 10 flows (§4.1–§4.9) | Mapped to pages — FL-1 through FL-10 |
| Loading/Skeletons (§7) | XC-1 |
| Docker Compose (§7) | XC-2 |
| Frontend Tests ≥5 (§7) | XC-3 |
| State Management (§7) | XC-4 |
| Responsive Pages (§7) | XC-5 |
| Best Practices (§7) | XC-6 |
| Component Lifecycles (§7) | XC-7 |
| Error Messages (§7) | XC-8 |
| Code Modifiability (§7) | XC-9 |
| Max 6 NPM packages (§1.4) | CN-1 |
| 15+ commits (§1.2) | CN-3 |
| Dynamic roles (§2.2) | CN-5 |

### Potentially Unclear ⚠️
| Item | Notes |
|---|---|
| Bounty formula image | Referenced in §4.7 but image missing from translated doc. Backend implements `score × 20M Rials`. |
| Ranking formula image | Referenced in §4.7 Note 1 but image missing. Text clearly describes `max_days × max_degree`. |
| "Visible to all users" scope | §4.7 says "all users" but backend requires authentication. Treated as "all authenticated users." |
| Admin Panel detail | Scored in §7 but no §5 section. Implemented from backend API capabilities. |
| Dashboard module specifics | §5.3 gives examples but no exhaustive list. Derived from role responsibilities. |
| Bail scoring in CP2 | §4.9 is optional; CP2 scoring has no explicit bail line. Included as optional stretch. |

### Not Applicable to Frontend
| Item | Notes |
|---|---|
| Entity model design (§6, 750 pts) | Backend only (CP1) |
| Backend endpoint implementation (§6) | Backend only (CP1) |
| REST principles (§6) | Backend only (CP1) |
| Swagger documentation (§6) | Backend only (CP1) |
| Backend tests (§6) | Backend only (CP1) |
| Backend app structure (§6) | Backend only (CP1) |
| Django built-in usage (§6) | Backend only (CP1) |
| Payment gateway callback page (§6) | Backend — Django Templates |

---

## 5. Confirmation

- ✅ No backend files were modified
- ✅ All changes limited to `frontend/docs/` and `md-files/`
- ✅ Requirements extracted exclusively from `md-files/project-doc.md`
- ✅ Backend investigated for ambiguity resolution only (read-only)
- ✅ No features were invented beyond what the document describes

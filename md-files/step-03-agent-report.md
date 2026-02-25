# Step 03 Agent Report — Domain Model & Route Map

> **Branch:** `agent/step-03-domain-model-and-routes`  
> **Based on:** `master` (latest)  
> **Depends on:** Step 01 (requirements matrix), Step 02 (API contract inventory)

---

## 1. Files Created / Changed

| File | Action | Purpose |
|------|--------|---------|
| `frontend/docs/route-map.md` | Created | 26-row route table with auth guards, dashboard module matrix, nav structure |
| `frontend/docs/domain-model-summary.md` | Created | 24 entities, ER diagram, field tables, enum summary |
| `frontend/src/types/common.ts` | Created | Shared base types: `ISODateTime`, `PaginatedResponse`, `TimeStamped`, `ApiError` |
| `frontend/src/types/auth.ts` | Created | `User`, `Role`, `Permission`, `JwtPayload`, login/register DTOs |
| `frontend/src/types/cases.ts` | Created | `Case`, `CaseComplainant`, `CaseWitness`, `CaseStatusLog`, status/crime enums |
| `frontend/src/types/evidence.ts` | Created | Discriminated union `Evidence` (5 subtypes), `EvidenceFile`, custody log |
| `frontend/src/types/suspects.ts` | Created | `Suspect`, `Warrant`, `Interrogation`, `Trial`, `BountyTip`, `Bail`, status logs |
| `frontend/src/types/board.ts` | Created | `DetectiveBoard`, `BoardNote`, `BoardItem`, `BoardConnection` |
| `frontend/src/types/core.ts` | Created | `Notification`, `DashboardStats`, `SearchResponse`, `SystemConstants` |
| `frontend/src/types/index.ts` | Created | Barrel re-export of all types |
| `frontend/src/router/routes.ts` | Created | Data-driven route config with `RouteConfig` interface, hierarchy constants, full route tree |

**Total:** 11 new files (2 docs + 8 TypeScript + 1 route config)

---

## 2. Domain Model Summary

### Entities Mapped (24 total)

| Domain | Entities |
|--------|----------|
| Auth / Accounts | User, Role, Permission, JwtPayload |
| Cases | Case, CaseComplainant, CaseWitness, CaseStatusLog |
| Evidence | Evidence (5 subtypes: Testimony, Biological, Vehicle, Identity, Other), EvidenceFile, EvidenceCustodyLog |
| Suspects | Suspect, Warrant, Interrogation, Trial, BountyTip, Bail, SuspectStatusLog |
| Board | DetectiveBoard, BoardNote, BoardItem, BoardConnection |
| Core | Notification, DashboardStats, SearchResponse, SystemConstants |

### Key Type Design Decisions

1. **No `enum` keyword** — TypeScript `erasableSyntaxOnly: true` in tsconfig prohibits runtime enum declarations. All enumerations are string/number literal union types (e.g., `type CaseStatus = "complaint_registered" | "cadet_review" | ...`).

2. **Discriminated union for Evidence** — `Evidence = TestimonyEvidence | BiologicalEvidence | VehicleEvidence | IdentityEvidence | OtherEvidence`, narrowed by `evidence_type` field. Matches backend's multi-table inheritance pattern.

3. **`UserRef` lightweight type** — Nested user references use `UserRef` (id, username, first_name, last_name) rather than the full `User` shape, matching DRF's nested serializer pattern.

4. **ISO 8601 strings** — All date/time fields typed as `ISODateTime` (alias for `string`), not `Date`, since JSON serialization produces strings.

5. **Request DTOs included** — Each entity has corresponding `*CreateRequest` / `*UpdateRequest` interfaces so form components can type-check payloads without importing response types.

---

## 3. Route Map Summary

### Routes Defined: 26

| Category | Count | Routes |
|----------|-------|--------|
| Public | 3 | `/`, `/login`, `/register` |
| Authenticated (any role) | 4 | `/dashboard`, `/profile`, `/notifications`, `/most-wanted` |
| Case management | 10 | `/cases`, `new/complaint`, `new/crime-scene`, `:caseId`, `evidence`, `evidence/new`, `suspects`, `suspects/:suspectId`, `interrogations`, `trial` |
| Detective Board | 1 | `/detective-board/:caseId` |
| Reporting | 1 | `/reports` |
| Bounty system | 3 | `/bounty-tips`, `new`, `verify` |
| Admin panel | 3 | `/admin`, `users`, `roles` |
| Catch-all | 1 | `*` (404) |

### Guard Model

- `RouteConfig` interface defines: `authRequired`, `minHierarchy`, `requiredPermissions`
- Hierarchy levels mapped to constants (`HIERARCHY.DETECTIVE = 7`, `HIERARCHY.SYSTEM_ADMIN = 100`, etc.)
- Guard implementation deferred to Step 04 (when react-router-dom is installed)
- JWT claims (`role`, `hierarchy_level`, `permissions_list`) are the source of truth for client-side guards

### Dashboard Modules: 17

Each module is role-gated and maps to a specific route. Defined in `route-map.md` § "Dashboard Modules by Role".

---

## 4. TypeScript Compilation

```
$ tsc --noEmit --project tsconfig.app.json
Exit code: 0
Errors: 0
```

All 8 type files + 1 route config compile cleanly under strict mode with `erasableSyntaxOnly: true`.

---

## 5. Coverage Verification

### Project-doc §5 Pages → Routes ✅

| Page (§5) | Route | Types |
|-----------|-------|-------|
| §5.1 Home | `/` | `DashboardStats` |
| §5.2 Login/Register | `/login`, `/register` | `LoginRequest`, `RegisterRequest`, `TokenPair` |
| §5.3 Modular Dashboard | `/dashboard` | All domain types (module-dependent) |
| §5.4 Detective Board | `/detective-board/:caseId` | `DetectiveBoard`, `BoardItem`, `BoardConnection`, `BoardNote` |
| §5.5 Most Wanted | `/most-wanted` | `MostWantedEntry`, `Suspect` |
| §5.6 Case & Complaint Status | `/cases/**` | `Case`, `CaseComplainant`, `CaseWitness`, `CaseStatusLog` |
| §5.7 General Reporting | `/reports` | `Case` (full detail with nested evidence, suspects, personnel) |
| §5.8 Evidence Registration | `/cases/:caseId/evidence/**` | `Evidence` (discriminated union), `EvidenceFile` |
| §7 Admin Panel | `/admin/**` | `User`, `Role`, `Permission` |

### Project-doc §4 Flows → Route + Type Coverage ✅

| Flow (§4) | Routes | Primary Types |
|-----------|--------|---------------|
| §4.1 Registration & Login | `/register`, `/login` | `RegisterRequest`, `LoginRequest`, `JwtPayload` |
| §4.2 Case Creation | `/cases/new/complaint`, `/cases/new/crime-scene` | `CaseCreateComplaintRequest`, `CaseCreateCrimeSceneRequest` |
| §4.3 Evidence Registration | `/cases/:caseId/evidence/new` | 5 evidence create requests, `FileUploadMeta` |
| §4.4 Solving the Case | `/detective-board/:caseId` | `DetectiveBoard`, `BoardItem`, `BoardConnection` |
| §4.5 Suspect ID & Interrogation | `/cases/:caseId/suspects/**`, `interrogations` | `Suspect`, `Interrogation`, `InterrogationCreateRequest` |
| §4.6 Trial | `/cases/:caseId/trial` | `Trial`, `TrialCreateRequest` |
| §4.7 Suspect Status / Most Wanted | `/most-wanted` | `MostWantedEntry`, `SuspectStatus` |
| §4.8 Bounty | `/bounty-tips/**` | `BountyTip`, `BountyTipCreateRequest`, `BountyVerifyLookupRequest` |
| §4.9 Bail (optional) | via suspect detail | `Bail`, `BailCreateRequest` |

### CP2 Scoring Criteria → Coverage ✅

| Criterion | Points | Addressed By |
|-----------|--------|-------------|
| UI/UX of 9 pages | 3000 | All 9 pages have routes + types |
| Loading states & skeleton | 300 | Types support it (`PaginatedResponse`, async-ready DTOs) — implementation in Step 04+ |
| Docker Compose | 300 | Already exists |
| Frontend tests (5+) | 100 | Types are test-ready — implementation in later steps |
| Proper state management | 100 | Route config + types ready — state lib in Step 04+ |
| Responsive pages | 300 | Implementation concern — no type impact |
| Best practices | 150 | Strict TS, barrel exports, discriminated unions |
| Component lifecycles | 100 | Implementation concern |
| Error messages | 100 | `ApiError` type defined |
| Code modifiability | 100 | Modular type files, `RouteConfig` data structure |

---

## 6. Known Anomalies Carried Forward

These were identified in Step 02 and remain relevant:

1. **Suspects URL double-prefix** — Frontend must call `/api/suspects/suspects/...`. Route config and types are designed to work with either path pattern.
2. **Evidence filter param mismatch** — Swagger docs show different param names than actual code. Frontend should use actual code params (`is_verified`, `created_after`, `created_before`).
3. **7 undocumented endpoints** — Included in type coverage where applicable.

---

## 7. What's Next (Step 04+)

1. **Install react-router-dom** — Wire `routes.ts` config into `createBrowserRouter()`
2. **Install an HTTP client** — axios or native fetch wrapper
3. **Auth store** — JWT storage, token refresh, `ProtectedRoute` component
4. **API service layer** — Typed API functions using the DTOs from `src/types/`
5. **Page scaffolding** — Create page component stubs for all 9 scored pages

---

## 8. Confirmation

- [x] `frontend/docs/route-map.md` created with 26 routes, dashboard modules, guard strategy, nav structure
- [x] `frontend/docs/domain-model-summary.md` created with 24 entities, ER diagram, field tables
- [x] `frontend/src/types/` — 8 type files + barrel index, all compile cleanly (tsc exit 0)
- [x] `frontend/src/router/routes.ts` — data-driven route config with hierarchy constants
- [x] All 9 CP2 pages covered in route map
- [x] All 9 project-doc flows have matching types and route entries
- [x] Zero TypeScript errors under strict mode
- [x] No backend files modified

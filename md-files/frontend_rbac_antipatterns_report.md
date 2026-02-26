# Frontend RBAC Anti-Pattern Audit

> **Date:** 2025-01-XX  
> **Scope:** `frontend/src/` — all `.ts` / `.tsx` files  
> **Goal:** Identify every place the frontend gates access on **role names** or
> **hardcoded hierarchy levels** instead of **permissions**, and propose fixes.

---

## Executive Summary

| Category | Good ✅ | Anti-pattern ❌ | Neutral |
|----------|---------|-----------------|---------|
| Route guards (`minHierarchy`) | 0 | **14** | 1 |
| Conditional rendering (hierarchy level) | 0 | **6** | 0 |
| Conditional rendering (permissions) | **10+** | 0 | 0 |
| Constants / enums | 1 (`P` perms) | **1** (`HIERARCHY`) | 0 |
| Type definitions | 10 | 0 | 2 (carry `role` from API) |
| API / display usage | 6 | 0 | 6 |

**No direct role-name string comparisons** (e.g. `role === "Detective"`)
exist in the frontend. All anti-patterns use **hardcoded numeric hierarchy
levels** that implicitly encode role identity.

---

## 1 — Root Cause: `HIERARCHY` Constant

### Location
**`src/router/routes.ts`  lines 43–54**

```ts
export const HIERARCHY = {
  BASE_USER: 0,
  JUDGE: 2,
  CORONER: 3,
  CADET: 4,
  POLICE_OFFICER: 6,
  DETECTIVE: 7,
  SERGEANT: 8,
  CAPTAIN: 9,
  POLICE_CHIEF: 10,
  SYSTEM_ADMIN: 100,
} as const;
```

### Problem
Maps role names → fixed numeric levels. Every route and page that imports
`HIERARCHY.XXX` is effectively checking a role name.

### Suggested Fix
**Delete entirely.** Replace all downstream usages with
`requiredPermissions` arrays (the route config already supports this
field). The `checkAccess()` helper in `auth/can.ts` already handles
permission arrays — just stop passing `minHierarchy`.

---

## 2 — Route Guards Using `minHierarchy`

### Location
**`src/router/routes.ts`  lines 95–255**

| Line | Route | Current Guard | Suggested `requiredPermissions` |
|------|-------|---------------|--------------------------------|
| 104 | Most Wanted | `minHierarchy: HIERARCHY.BASE_USER` | `["suspects.view_suspect"]` |
| 119 | File Complaint | `minHierarchy: 1` | `["cases.add_casecomplainant"]` |
| 126 | Report Crime Scene | `minHierarchy: HIERARCHY.POLICE_OFFICER` | `["cases.can_create_crime_scene"]` |
| 145 | Add Evidence | `minHierarchy: HIERARCHY.DETECTIVE` | `["evidence.add_evidence"]` |
| 158 | Case Suspects | `minHierarchy: HIERARCHY.DETECTIVE` | `["suspects.view_suspect"]` |
| 165 | Suspect Detail | `minHierarchy: HIERARCHY.DETECTIVE` | `["suspects.view_suspect"]` |
| 172 | Interrogations | `minHierarchy: HIERARCHY.DETECTIVE` + perms | Keep only `requiredPermissions: ["suspects.can_conduct_interrogation"]` |
| 180 | Trial | `minHierarchy: HIERARCHY.JUDGE` + perms | Keep only `requiredPermissions: ["suspects.can_judge_trial"]` |
| 194 | Detective Board | `minHierarchy: HIERARCHY.DETECTIVE` | `["board.view_detectiveboard"]` |
| 203 | Reporting | `minHierarchy: HIERARCHY.JUDGE` | `["cases.can_view_case_report"]` |
| 224 | Verify Reward | `minHierarchy: HIERARCHY.POLICE_OFFICER` | `["suspects.can_lookup_bounty_reward"]` |
| 235 | Admin Panel | `minHierarchy: HIERARCHY.SYSTEM_ADMIN` | `["accounts.can_manage_users"]` |
| 242 | User Management | `minHierarchy: HIERARCHY.SYSTEM_ADMIN` | `["accounts.can_manage_users"]` |
| 249 | Role Management | `minHierarchy: HIERARCHY.SYSTEM_ADMIN` | `["accounts.can_manage_users"]` |

### How to Fix
1. Remove `minHierarchy` from every route definition.
2. Add / update `requiredPermissions` with the permission codenames above.
3. Update `checkAccess()` in `auth/can.ts` to ignore the now-unused
   `minHierarchy` parameter (or remove it entirely).
4. Delete the `HIERARCHY` constant and its import.

---

## 3 — Admin Pages: Hardcoded `hierarchyLevel < 100`

### Locations

| File | Line | Current Code |
|------|------|-------------|
| `src/pages/Admin/AdminPage.tsx` | 15–18 | `if (hierarchyLevel < 100) return <AccessDenied/>` |
| `src/pages/Admin/UserManagementPage.tsx` | 22–24 | `if (hierarchyLevel < 100) return <AccessDenied/>` |
| `src/pages/Admin/RoleManagementPage.tsx` | 29–31 | `if (hierarchyLevel < 100) return <AccessDenied/>` |

### Suggested Fix
Replace in all three files:

```tsx
// Before
const { hierarchyLevel } = useAuth();
if (hierarchyLevel < 100) return <AccessDenied />;

// After
const { permissionSet } = useAuth();
if (!permissionSet.has("accounts.can_manage_users")) return <AccessDenied />;
```

---

## 4 — BountyTipsPage: Hardcoded `hierarchyLevel >= 3 / >= 4`

### Location
**`src/pages/BountyTips/BountyTipsPage.tsx`  lines 43, 45, 167**

```tsx
const canReview = tip.status === "pending" && hierarchyLevel >= 3;
const canVerify = tip.status === "officer_reviewed" && hierarchyLevel >= 4;
// ...
{hierarchyLevel >= 3 && (<Link to="/bounty-tips/verify">Verify Reward</Link>)}
```

### Suggested Fix
```tsx
const canReview =
  tip.status === "pending" &&
  permissionSet.has("suspects.can_review_bounty_tip");

const canVerify =
  tip.status === "officer_reviewed" &&
  permissionSet.has("suspects.can_verify_bounty_tip");

// ...
{permissionSet.has("suspects.can_lookup_bounty_reward") && (
  <Link to="/bounty-tips/verify">Verify Reward</Link>
)}
```

---

## 5 — Auth Utilities: `hasMinHierarchy` Helper

### Location
**`src/auth/can.ts`  lines 62–67**

```ts
export function hasMinHierarchy(
  userHierarchy: number,
  minLevel: number
): boolean {
  return userHierarchy >= minLevel;
}
```

### Problem
This utility exists solely to support hierarchy-level checks. Once all
callers migrate to permission-based checks it becomes dead code.

### Suggested Fix
After all route guards and pages are migrated:
1. Remove `hasMinHierarchy()`.
2. Simplify `checkAccess()` (lines 82–97) to only evaluate permissions.
3. Remove `hierarchyLevel` from `AuthContextValue` if no longer needed
   anywhere.

---

## Already Correct ✅ (No Action Required)

These areas already use the permission-based pattern properly:

| Area | File(s) | Notes |
|------|---------|-------|
| Case workflow actions | `src/lib/caseWorkflow.ts` | All `STATUS_ACTIONS` use `requiredPermissions` |
| Dashboard modules | `src/pages/Dashboard/DashboardPage.tsx` | `canAny(permissionSet, ...)` |
| Evidence verification | `src/pages/Evidence/EvidenceDetailPage.tsx` | `permissionSet.has("evidence.can_verify_evidence")` |
| Board visibility | `src/pages/Cases/CaseDetailPage.tsx` | `permissionSet.has("board.view_detectiveboard")` |
| Sidebar navigation | `src/components/layout/Sidebar.tsx` | `canAny(permissionSet, link.permissions)` |
| Permission constants | `src/auth/permissions.ts` | Full `P` object mirroring backend codenames |
| `can()` / `canAll()` / `canAny()` | `src/auth/can.ts` | Clean utility functions |
| Role display (name badges) | Dashboard, Admin pages, Report view | Display only — acceptable |

---

## Migration Checklist

- [ ] Replace all 14 `minHierarchy` route guards with `requiredPermissions`
- [ ] Delete `HIERARCHY` constant from `router/routes.ts`
- [ ] Fix 3 Admin pages to use `permissionSet.has("accounts.can_manage_users")`
- [ ] Fix BountyTipsPage (3 locations) to use permission checks
- [ ] Remove `hasMinHierarchy()` from `auth/can.ts`
- [ ] Simplify `checkAccess()` in `auth/can.ts`
- [ ] Remove `hierarchyLevel` from `AuthContextValue` (if unused after migration)
- [ ] Run full test suite to verify no regressions

---

## Notes

- The backend JWT payload already includes `permissions_list: string[]`
  (see `types/auth.ts` line 140), so all required permissions are already
  available client-side. No backend changes needed for this migration.
- The `P` constants object in `auth/permissions.ts` already mirrors the
  backend codenames — use it for all new `requiredPermissions` values.
- Hierarchy levels may still be useful for **display** (e.g. sorting users
  by rank) but should never be used for **access control decisions**.

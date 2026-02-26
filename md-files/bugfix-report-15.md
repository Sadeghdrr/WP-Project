# Bug-Fix Report — Step 15 Stabilization

**Branch:** `fix/core-ui-and-api-bugs`  
**Date:** 2026-02-26

---

## 1. Bounty Tips API URL Fix

**Problem:** The frontend used `/api/suspects/bounty-tips/` for all bounty-tip endpoints. The backend mounts the `BountyTipViewSet` at the top-level router inside the suspects app, which — combined with the `/api/suspects/` include prefix — would result in `/api/suspects/bounty-tips/`. However, the backend Swagger and URL config document the canonical path as `/api/bounty-tips/` (top-level, not nested under `/suspects/`).

**Changes in `frontend/src/api/endpoints.ts`:**

| Constant | Before | After |
|---|---|---|
| `BOUNTY_TIPS` | `/suspects/bounty-tips/` | `/bounty-tips/` |
| `bountyTip(id)` | `/suspects/bounty-tips/${id}/` | `/bounty-tips/${id}/` |
| `bountyTipReview(id)` | `/suspects/bounty-tips/${id}/review/` | `/bounty-tips/${id}/review/` |
| `bountyTipVerify(id)` | `/suspects/bounty-tips/${id}/verify/` | `/bounty-tips/${id}/verify/` |
| `BOUNTY_REWARD_LOOKUP` | `/suspects/bounty-tips/lookup-reward/` | `/bounty-tips/lookup-reward/` |

No other files needed changes — all API calls go through the centralized `API` object.

---

## 2. Admin Panel Sidebar RBAC

**Problem:** The "Admin Panel" navigation link in `Sidebar.tsx` was unconditionally rendered for all authenticated users, leaking admin-only functionality to standard users.

**Fix in `frontend/src/components/layout/Sidebar.tsx`:**

- Imported `useAuth`, `canAny`, and `P` from the auth module.
- Added a `permissions` property to navigation link definitions.
- The "Admin Panel" link now requires at least one of: `accounts.view_user`, `accounts.view_role`, `accounts.change_user`, `accounts.change_role`.
- Before rendering each link, the component checks `canAny(permissionSet, link.permissions)` and skips rendering if the user lacks all listed permissions.

---

## 3. Case Creation Failure

**Root Cause:** Both `FileComplaintPage.tsx` and `CrimeScenePage.tsx` were **placeholder stubs** — they rendered a static `<PlaceholderPage>` component with no form, no state, and no API call. The API service layer (`api/cases.ts`) already had working `createComplaintCase()` and `createCrimeSceneCase()` functions, but no UI was wired to them. Additionally, no mutation hooks existed in `useCases.ts` for case creation.

**Fix:**

1. **Added mutation hooks** in `frontend/src/hooks/useCases.ts`:
   - `useCreateComplaintCase()` — calls `casesApi.createComplaintCase(data)`, invalidates case list on success.
   - `useCreateCrimeSceneCase()` — calls `casesApi.createCrimeSceneCase(data)`, invalidates case list on success.

2. **Replaced `FileComplaintPage.tsx`** stub with a working form:
   - Fields: title (required), description (required), crime_level (select 1–4), incident_date (optional), location (optional).
   - On submit: calls `useCreateComplaintCase` mutation with the payload `{ title, description, crime_level, incident_date?, location? }`.
   - `creation_type: "complaint"` is injected by the API service layer.
   - On success: navigates to `/cases/{id}`.

3. **Replaced `CrimeScenePage.tsx`** stub with a working form:
   - Same fields as complaint + a dynamic witnesses section (`full_name`, `phone_number`, `national_id` per witness).
   - On submit: calls `useCreateCrimeSceneCase` mutation. `creation_type: "crime_scene"` is injected by the API service layer.
   - On success: navigates to `/cases/{id}`.

4. **Created CSS modules** (`FileComplaintPage.module.css`, `CrimeScenePage.module.css`) following the existing project styling patterns (identical structure to `SubmitTipPage.module.css`).

---

## Files Changed

| File | Change |
|---|---|
| `frontend/src/api/endpoints.ts` | Fixed 5 bounty-tips URLs |
| `frontend/src/components/layout/Sidebar.tsx` | Added RBAC guard on Admin Panel link |
| `frontend/src/hooks/useCases.ts` | Added `useCreateComplaintCase` and `useCreateCrimeSceneCase` hooks |
| `frontend/src/pages/Cases/FileComplaintPage.tsx` | Replaced placeholder with working complaint form |
| `frontend/src/pages/Cases/CrimeScenePage.tsx` | Replaced placeholder with working crime-scene form |
| `frontend/src/pages/Cases/FileComplaintPage.module.css` | New — form styles |
| `frontend/src/pages/Cases/CrimeScenePage.module.css` | New — form styles with witness section |

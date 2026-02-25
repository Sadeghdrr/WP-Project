# Most Wanted & Bounty Tips — Developer Notes

## Overview

This module implements two closely-related features from the project spec:

1. **Most Wanted Page** (§5.5, 300 pts) — displays suspects wanted for over 30 days, ranked by `score = max_days_wanted × max_crime_degree`. Each entry shows a bounty reward of `score × 20,000,000 Rials`.

2. **Bounty Tips Workflow** (§4.8, 100 pts) — citizens submit tips about suspects/cases. An officer reviews → a detective verifies → a unique reward code is generated. Police personnel can then look up the reward at the station using national ID + code.

---

## Backend Endpoints (read-only reference)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/suspects/most-wanted/` | Public most-wanted list (ranked) |
| `GET` | `/api/suspects/bounty-tips/` | List tips (role-scoped) |
| `POST` | `/api/suspects/bounty-tips/` | Submit new tip |
| `GET` | `/api/suspects/bounty-tips/:id/` | Tip detail |
| `POST` | `/api/suspects/bounty-tips/:id/review/` | Officer review (accept/reject) |
| `POST` | `/api/suspects/bounty-tips/:id/verify/` | Detective verify (verify/reject) |
| `POST` | `/api/suspects/bounty-tips/lookup-reward/` | Reward lookup by national_id + code |

### Bounty Tip State Machine

```
PENDING → (officer accept) → OFFICER_REVIEWED → (detective verify) → VERIFIED [unique_code generated]
PENDING → (officer reject) → REJECTED
OFFICER_REVIEWED → (detective reject) → REJECTED
```

---

## Frontend Architecture

### Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/types/suspects.ts` | Modified | Fixed type anomalies vs backend serializers |
| `src/api/endpoints.ts` | Modified | Added missing endpoint helpers |
| `src/api/suspects.ts` | Created | API service layer for suspects/bounty |
| `src/hooks/useSuspects.ts` | Created | React Query hooks (queries + mutations) |
| `src/pages/MostWanted/MostWantedPage.tsx` | Replaced | Ranked card grid with scores/rewards |
| `src/pages/MostWanted/MostWantedPage.module.css` | Created | Page styles |
| `src/pages/BountyTips/BountyTipsPage.tsx` | Replaced | Tip list with inline review/verify |
| `src/pages/BountyTips/BountyTipsPage.module.css` | Created | Page styles |
| `src/pages/BountyTips/SubmitTipPage.tsx` | Replaced | Tip submission form |
| `src/pages/BountyTips/SubmitTipPage.module.css` | Created | Page styles |
| `src/pages/BountyTips/VerifyRewardPage.tsx` | Replaced | Reward lookup form |
| `src/pages/BountyTips/VerifyRewardPage.module.css` | Created | Page styles |
| `src/api/index.ts` | Modified | Barrel export for suspects API |
| `src/hooks/index.ts` | Modified | Barrel export for suspect hooks |
| `src/types/index.ts` | Modified | Barrel export for BountyTipListItem |

### Type Fixes Applied

1. **`BountyTipReviewRequest`** — Changed from `{status: "officer_reviewed"|"rejected"}` to `{decision: "accept"|"reject", review_notes?: string}` to match `BountyTipReviewSerializer`.

2. **`BountyTipVerifyRequest`** — Changed from `{status: "verified"|"rejected"}` to `{decision: "verify"|"reject", verification_notes?: string}` to match `BountyTipVerifySerializer`.

3. **`MostWantedEntry`** — Added missing fields: `description`, `address`, `case_title`, `status_display`, `calculated_reward` to match `MostWantedSerializer`.

4. **`BountyVerifyLookupResponse`** — Changed to flat structure `{tip_id, informant_name, informant_national_id, reward_amount, is_claimed, suspect_name, case_id}` matching the service return dict.

5. **`BountyTipListItem`** — New type added to match `BountyTipListSerializer` (compact list fields vs full detail).

6. **`BountyTip`** — Updated serializer field names: `informant` is now `number` (FK), added `informant_name`, `reviewed_by_name`, `verified_by_name`, `status_display`.

### Hooks

| Hook | Type | Purpose |
|------|------|---------|
| `useMostWanted()` | Query | Fetch ranked most-wanted list |
| `useBountyTips(filters)` | Query | List tips with optional status filter |
| `useBountyTipDetail(id)` | Query | Single tip detail |
| `useBountyTipActions()` | Mutations | `createTip`, `reviewTip`, `verifyTip`, `lookupReward` |

### Permission-Based UI

- **Submit Tip**: Available to any authenticated user
- **Review Tip**: Inline actions visible to hierarchy level ≥ 3 (Officer+)
- **Verify Tip**: Inline actions visible to hierarchy level ≥ 4 (Detective+)
- **Verify Reward**: Link visible to hierarchy level ≥ 3, lookup via backend permission check

---

## Routes (pre-existing, no changes needed)

```
/most-wanted         → MostWantedPage   (authRequired, minHierarchy: BASE_USER)
/bounty-tips         → BountyTipsPage   (authRequired)
/bounty-tips/new     → SubmitTipPage    (authRequired)
/bounty-tips/verify  → VerifyRewardPage (authRequired, minHierarchy: POLICE_OFFICER)
```

All routes were already wired in `Router.tsx` with lazy loading and `<ProtectedRoute>`.

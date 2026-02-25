# Step 15 — Most Wanted Page & Bounty Tips Workflow

**Branch:** `agent/step-15-most-wanted-bounty-tips`
**Scope:** Frontend only (backend read-only)

---

## Summary

Implemented the Most Wanted page (§5.5, 300 pts) and Bounty Tips workflow (§4.8, 100 pts) in the frontend. Replaced all four placeholder pages with fully functional data-driven UI. Fixed type definitions to match backend serializer contracts. Created API service layer, React Query hooks, and CSS modules.

---

## Requirements Coverage

### §5.5 Most Wanted Page (300 pts)
- [x] Display suspects wanted >30 days
- [x] Ranked grid sorted by `most_wanted_score` (backend-sorted)
- [x] Show: photo, name, national ID, status, days wanted, score, bounty reward
- [x] Description and case link
- [x] Reward formatted in human-readable Rials
- [x] Loading skeletons, empty state, error state

### §4.8 Bounty Tips Workflow (100 pts)
- [x] Citizen tip submission form (suspect and/or case + information)
- [x] Tip list page with status filtering
- [x] Inline officer review (accept/reject with notes)
- [x] Inline detective verification (verify/reject with notes)
- [x] Reward lookup page (national_id + unique_code)
- [x] Result display with reward amount, claim status, suspect info, case link
- [x] Permission-based UI (review/verify actions by hierarchy level)

---

## Files Changed

### New Files
| File | Purpose |
|------|---------|
| `frontend/src/api/suspects.ts` | API service (7 functions) |
| `frontend/src/hooks/useSuspects.ts` | React Query hooks (4 hooks) |
| `frontend/src/pages/MostWanted/MostWantedPage.module.css` | Most Wanted styles |
| `frontend/src/pages/BountyTips/BountyTipsPage.module.css` | Bounty Tips list styles |
| `frontend/src/pages/BountyTips/SubmitTipPage.module.css` | Submit Tip form styles |
| `frontend/src/pages/BountyTips/VerifyRewardPage.module.css` | Verify Reward styles |
| `frontend/docs/most-wanted-bounty-notes.md` | Developer documentation |

### Modified Files
| File | Changes |
|------|---------|
| `frontend/src/types/suspects.ts` | Fixed 5 type anomalies vs backend, added `BountyTipListItem` |
| `frontend/src/types/index.ts` | Added `BountyTipListItem` to barrel export |
| `frontend/src/api/endpoints.ts` | Added `bountyTip()`, `bountyTipReview()`, `bountyTipVerify()`, `BOUNTY_REWARD_LOOKUP` |
| `frontend/src/api/index.ts` | Added suspects barrel export |
| `frontend/src/hooks/index.ts` | Added suspects hooks barrel export |
| `frontend/src/pages/MostWanted/MostWantedPage.tsx` | Replaced placeholder with ranked card grid |
| `frontend/src/pages/BountyTips/BountyTipsPage.tsx` | Replaced placeholder with tip list + inline actions |
| `frontend/src/pages/BountyTips/SubmitTipPage.tsx` | Replaced placeholder with submission form |
| `frontend/src/pages/BountyTips/VerifyRewardPage.tsx` | Replaced placeholder with lookup form |

### Existing / Unchanged
- `frontend/src/router/Router.tsx` — routes already wired (no changes needed)
- `frontend/src/router/routes.ts` — route declarations already present

---

## Type Anomalies Fixed

| Type | Issue | Fix |
|------|-------|-----|
| `BountyTipReviewRequest` | Had `{status: ...}` but backend expects `{decision, review_notes}` | Updated to match `BountyTipReviewSerializer` |
| `BountyTipVerifyRequest` | Had `{status: ...}` but backend expects `{decision, verification_notes}` | Updated to match `BountyTipVerifySerializer` |
| `MostWantedEntry` | Missing `description`, `address`, `case_title`, `status_display`, `calculated_reward` | Added all fields from `MostWantedSerializer` |
| `BountyVerifyLookupResponse` | Had nested `{informant: UserRef, tip: BountyTip}` but backend returns flat dict | Changed to flat `{tip_id, informant_name, ...}` |
| `BountyTip` | Had `informant: UserRef` but serializer returns FK + name fields | Updated to `informant: number` + name/display fields |

---

## Architecture Decisions

1. **Hooks pattern** — follows existing `useCases` / `useEvidence` conventions (query + mutation hooks)
2. **Inline actions** — review/verify controls are inline in the tip list table row, using hierarchy level for visibility
3. **No backend changes** — all work is frontend-only; type anomalies were fixed client-side
4. **CSS modules** — consistent with existing page styles (Evidence, Cases pages)
5. **Permission gating** — `hierarchyLevel` from `useAuth()` used to show/hide review/verify buttons

---

## Verification

- [x] `npx tsc --noEmit` — zero errors
- [x] `npx eslint` on all changed files — zero errors/warnings
- [x] Routes pre-wired in Router.tsx — confirmed
- [x] All 4 placeholder pages replaced with functional implementations

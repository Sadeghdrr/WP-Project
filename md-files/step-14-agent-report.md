# Step 14 – Evidence Registration & Review

## Scope
Implement the Evidence Registration & Review frontend workspace (§4.3, §5.8 – 200 pts).

## Completed Deliverables

### New Files Created
| File | Purpose |
|------|---------|
| `src/api/evidence.ts` | Evidence API service (CRUD, verify, files, custody) |
| `src/hooks/useEvidence.ts` | React Query hooks (5 queries + 5 mutations) |
| `src/lib/evidenceHelpers.ts` | Display helpers (labels, colors, icons) |
| `src/pages/Evidence/EvidenceListPage.module.css` | List page styles |
| `src/pages/Evidence/EvidenceDetailPage.tsx` | Detail page with verify/files/custody |
| `src/pages/Evidence/EvidenceDetailPage.module.css` | Detail page styles |
| `src/pages/Evidence/AddEvidencePage.module.css` | Registration form styles |
| `frontend/docs/evidence-workspace-notes.md` | Implementation notes |

### Modified Files
| File | Changes |
|------|---------|
| `src/api/endpoints.ts` | Added 5 evidence action endpoints |
| `src/types/evidence.ts` | Rewrote to match actual backend serializer shapes |
| `src/types/index.ts` | Added new evidence type exports |
| `src/pages/Evidence/EvidenceListPage.tsx` | Replaced placeholder → full implementation |
| `src/pages/Evidence/AddEvidencePage.tsx` | Replaced placeholder → dynamic registration form |
| `src/router/Router.tsx` | Added `EvidenceDetailPage` lazy import + route |
| `src/router/routes.ts` | Added `evidence/:evidenceId` route declaration |
| `src/api/index.ts` | Added evidence API barrel exports |
| `src/hooks/index.ts` | Added evidence hooks barrel exports |
| `src/lib/index.ts` | Added evidence helpers barrel exports |

## Feature Coverage

| Feature | Status |
|---------|--------|
| Evidence list with filters (type, search) | ✅ |
| Evidence detail (polymorphic by type) | ✅ |
| Registration form with 5 evidence types | ✅ |
| Dynamic type-specific form fields | ✅ |
| Vehicle XOR constraint (plate vs serial) | ✅ |
| Identity key-value document details | ✅ |
| Coroner verification panel (approve/reject) | ✅ |
| File upload (multipart) | ✅ |
| Chain-of-custody timeline | ✅ |
| Loading/skeleton states | ✅ |
| Error/empty states | ✅ |
| Delete with confirmation | ✅ |
| Permission-gated verification | ✅ |

## Build Verification
- `npx tsc --noEmit` — zero errors
- `npx vite build` — all chunks compiled successfully

## Backend Anomalies
None found.

## Branch
`agent/step-14-evidence-registration-review`

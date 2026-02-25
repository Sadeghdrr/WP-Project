# Step 08 Agent Report — Core API Client, Error Handling & UI Feedback Primitives

**Branch**: `agent/step-08-core-client-infra`  
**Date**: 2026-02-25

---

## Files Created

| File | Purpose |
|---|---|
| `frontend/src/components/ui/LoadingSpinner.tsx` | CSS-only loading spinner (page + inline variants) |
| `frontend/src/components/ui/LoadingSpinner.module.css` | Styles for LoadingSpinner |
| `frontend/src/components/ui/Skeleton.tsx` | Shimmer skeleton placeholders (text/rect/circle + count) |
| `frontend/src/components/ui/Skeleton.module.css` | Styles for Skeleton |
| `frontend/src/components/ui/EmptyState.tsx` | Empty-state display with optional action |
| `frontend/src/components/ui/EmptyState.module.css` | Styles for EmptyState |
| `frontend/src/components/ui/ErrorState.tsx` | Error display consuming normalised `ApiError` |
| `frontend/src/components/ui/ErrorState.module.css` | Styles for ErrorState |
| `frontend/src/components/ui/FieldError.tsx` | Inline field-level validation error |
| `frontend/src/components/ui/FieldError.module.css` | Styles for FieldError |
| `frontend/src/lib/errors.ts` | Error extraction utilities (getFieldError, flattenErrors, etc.) |
| `frontend/src/lib/index.ts` | Lib barrel export |
| `frontend/src/hooks/useConstants.ts` | React Query hook for system constants + lookup helpers |
| `frontend/src/hooks/index.ts` | Hooks barrel export |
| `frontend/docs/core-client-infra-notes.md` | Architecture docs for this step |

## Files Modified

| File | Changes |
|---|---|
| `frontend/src/api/client.ts` | Added `apiPut`, `apiPostForm`, `apiPatchForm`; enhanced `normaliseError` to handle `non_field_errors` and `detail` arrays |
| `frontend/src/api/endpoints.ts` | Fixed `DASHBOARD_STATS` path from `/core/stats/` to `/core/dashboard/` (matching backend URL config) |
| `frontend/src/api/index.ts` | Added new exports (`apiPut`, `apiPostForm`, `apiPatchForm`) |
| `frontend/src/components/ui/index.ts` | Added exports for all new UI primitives |
| `frontend/src/types/core.ts` | Updated `SystemConstants` to match actual backend response (10 keys); added `ChoiceItem` and `RoleHierarchyItem` types |
| `frontend/src/types/index.ts` | Added `ChoiceItem`, `RoleHierarchyItem` to barrel exports |

---

## Core Infrastructure Implemented

### 1. API Client Enhancements
- **`apiPut<T>()`** — PUT method for full resource updates
- **`apiPostForm<T>()` / `apiPatchForm<T>()`** — FormData methods for file uploads (evidence images, suspect photos); deliberately omit Content-Type so browser sets the multipart boundary
- **Enhanced error normalisation** — now handles `non_field_errors` (promotes first entry to main message), `detail` as array, and standard DRF validation shape

### 2. Error Normalisation & Utilities
- `src/lib/errors.ts` provides typed helpers to extract/format errors from the normalised `ApiError` shape
- `getFieldError(error, field)` — single first error for inline display
- `getFieldErrors(error, field)` — all errors for a field
- `hasFieldErrors(error)` — quick boolean check
- `getErrorMessage(error, fallback?)` — top-level message
- `flattenErrors(error)` — all errors as flat array for summary display

### 3. Reusable UI Primitives
- **`LoadingSpinner`** — CSS-only animated spinner, "page" (centered, large) or "inline" (small, for buttons) variant. Uses `role="status"` for accessibility
- **`Skeleton`** — shimmer-animated placeholders for content loading. Supports text/rect/circle variants, configurable width/height/count. Last text line renders shorter for visual realism
- **`EmptyState`** — empty-data display with icon, title, optional description, and optional action button
- **`ErrorState`** — renders normalised `ApiError` with detail list and optional retry button. Compact mode available for inline contexts
- **`FieldError`** — inline field validation error display for forms, wired to `ApiError.fieldErrors`

### 4. Constants Access Layer
- `useConstants()` React Query hook fetches `GET /api/core/constants/` once per session (`staleTime: Infinity`)
- `fetchConstants()` exported for prefetching or use outside React
- `lookupLabel(choices, value)` helper for converting enum values to display labels
- `SystemConstants` type updated to match actual backend (10 keys including `role_hierarchy`)

---

## Backend Error/Response Anomalies Found (Report Only)

1. **`DASHBOARD_STATS` endpoint URL mismatch** — Frontend had `/core/stats/` but backend registers `/core/dashboard/`. **Fixed** in `endpoints.ts`.
2. **Pre-existing TypeScript errors in `AuthContext.tsx`** — `establishSession` is declared but unused (TS6133), and `TokenRefreshResponse` cast to `Record<string, unknown>` causes TS2352. These exist on master and are unrelated to this step.
3. **`SystemConstants` type was inaccurate** — Only had 5 fields with wrong shapes. Backend actually returns 10 keys. **Fixed** to match `SystemConstantsService.get_constants()` output.
4. **Potential `non_field_errors` masking** — If DRF returns `{ "non_field_errors": ["..."], "field": ["..."] }`, the original normaliser would set message to generic "Validation error". Now uses `non_field_errors[0]` as the message.

## Constants Endpoint Status

**Found and functional**: `GET /api/core/constants/` is registered at `backend/core/urls.py`, uses `AllowAny` permission (no auth needed), and delegates to `SystemConstantsService.get_constants()`. Returns 10 keys of choice enums + role hierarchy. Frontend type and hook are aligned.

## Confirmation: No Backend Files Modified

No files in `backend/` were created, modified, or deleted.

---

## Post-Check: Cross-Cutting Quality Criteria Coverage

| CP2 Criterion | Points | Coverage |
|---|---|---|
| **Loading states & Skeleton Layout** | 300 pts | ✅ `LoadingSpinner` (page/inline), `Skeleton` (text/rect/circle/count) |
| **Error messages for each situation** | 100 pts | ✅ `ErrorState`, `FieldError`, `flattenErrors` utility, normalised `ApiError` |
| **Proper state management** | 100 pts | ✅ React Query for constants cache; `useConstants()` hook; existing auth context |
| **Ease of code modifiability** | 100 pts | ✅ Centralised API client, barrel exports, typed interfaces, constants hook |
| **Responsive pages** | 300 pts | ⬜ Per-page responsibility; primitives use CSS custom properties & flexible layouts |
| **Best practices** | 150 pts | ✅ Separation of concerns, typed errors, accessibility attributes, CSS Modules |
| **Component lifecycles** | 100 pts | ✅ Hooks-based patterns, React Query manages fetch lifecycle |

All infrastructure is importable via barrel exports and ready for consumption by feature pages.

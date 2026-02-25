# Core Client Infrastructure Notes

## Architecture Summary

### API Client (`src/api/client.ts`)
The API client is a **lightweight fetch wrapper** built on the native `fetch` API (no Axios dependency). Key capabilities:
- **Base URL handling**: Reads `VITE_API_BASE_URL` from environment, defaults to `/api`
- **JSON request/response**: Auto-sets `Content-Type: application/json` for body requests
- **Auth header injection**: Attaches `Authorization: Bearer <token>` when access token is available
- **Multipart support**: `apiPostForm()` and `apiPatchForm()` helper methods for file uploads (omit Content-Type so browser sets boundary)
- **401 handler**: Notifies auth layer on 401 responses (session expiry triggering logout)
- **Normalised error shape**: All errors return a consistent `ApiError` type

Available methods:
- `apiGet<T>(path)` — GET request
- `apiPost<T>(path, body)` — POST with JSON body
- `apiPut<T>(path, body)` — PUT with JSON body
- `apiPatch<T>(path, body)` — PATCH with JSON body
- `apiDelete<T>(path)` — DELETE request
- `apiPostForm<T>(path, formData)` — POST with FormData (file uploads)
- `apiPatchForm<T>(path, formData)` — PATCH with FormData

All return `Promise<ApiResponse<T>>` which is a discriminated union:
```ts
type ApiResponse<T> =
  | { ok: true; data: T; status: number }
  | { ok: false; error: ApiError; status: number };
```

### Centralised Endpoints (`src/api/endpoints.ts`)
All backend URL paths in a single `API` object — no hardcoded paths in components. Includes dynamic path builders (e.g. `API.case(id)`).

**Bug fix applied in this step**: `DASHBOARD_STATS` was pointing to `/core/stats/` but the backend URL is `/core/dashboard/`.

---

## Error Model Summary

### Backend Error Patterns (DRF)
The backend produces several error response shapes:

1. **Detail string** — `{ "detail": "Authentication credentials were not provided." }`
2. **Validation errors** — `{ "field_name": ["Error message 1", "Error message 2"], ... }`
3. **Non-field errors** — `{ "non_field_errors": ["..."] }` (e.g. login failures)
4. **Detail array** — `{ "detail": ["err1", "err2"] }` (rare)

### Normalised Frontend Shape
```ts
interface ApiError {
  message: string;                        // Top-level summary
  fieldErrors?: Record<string, string[]>; // Per-field validation errors
}
```

### Error Extraction Utilities (`src/lib/errors.ts`)
- `getFieldError(error, field)` — first error for a field (for inline display)
- `getFieldErrors(error, field)` — all errors for a field
- `hasFieldErrors(error)` — boolean check
- `getErrorMessage(error, fallback?)` — top-level message with fallback
- `flattenErrors(error)` — all errors as flat string array

---

## Constants Strategy

### Endpoint
`GET /api/core/constants/` — **AllowAny** (no auth required), returns all system enums.

### Response Shape (10 keys)
| Key | Type | Description |
|---|---|---|
| `crime_levels` | `ChoiceItem[]` | Crime level choices (1-4) |
| `case_statuses` | `ChoiceItem[]` | Case workflow statuses |
| `case_creation_types` | `ChoiceItem[]` | Complaint vs Crime Scene |
| `evidence_types` | `ChoiceItem[]` | Evidence category choices |
| `evidence_file_types` | `ChoiceItem[]` | File type choices |
| `suspect_statuses` | `ChoiceItem[]` | Suspect status choices |
| `verdict_choices` | `ChoiceItem[]` | Trial verdict options |
| `bounty_tip_statuses` | `ChoiceItem[]` | Bounty tip status choices |
| `complainant_statuses` | `ChoiceItem[]` | Complainant review statuses |
| `role_hierarchy` | `RoleHierarchyItem[]` | Roles ordered by hierarchy |

Each `ChoiceItem` is `{ value: string, label: string }`.
Each `RoleHierarchyItem` is `{ id: number, name: string, hierarchy_level: number }`.

### Caching
- `useConstants()` hook wraps a React Query call with `staleTime: Infinity` and `gcTime: Infinity`
- Constants are fetched once per session and cached globally
- `lookupLabel(choices, value)` helper for quick label resolution
- `fetchConstants()` exported for use outside React (e.g. query client prefetching)

---

## Reusable UI Primitives Added

| Component | File | Purpose |
|---|---|---|
| `LoadingSpinner` | `components/ui/LoadingSpinner.tsx` | CSS-only spinner, "page" or "inline" variant |
| `Skeleton` | `components/ui/Skeleton.tsx` | Shimmer placeholders (text/rect/circle), `count` prop for multiple lines |
| `EmptyState` | `components/ui/EmptyState.tsx` | Empty data display with optional action button |
| `ErrorState` | `components/ui/ErrorState.tsx` | Error display consuming `ApiError`, with optional retry |
| `FieldError` | `components/ui/FieldError.tsx` | Inline field-level validation error |
| `ErrorBoundary` | `components/ui/ErrorBoundary.tsx` | React class component for unhandled render errors (pre-existing) |

All primitives use CSS Modules and the project's existing CSS custom properties (design tokens).

---

## Deferred Improvements

1. **Token refresh retry queue**: Currently 401 triggers logout. A proper retry queue that refreshes the token and replays failed requests would improve UX. The hook point exists (`setOnUnauthorized`) but the intercept-and-retry pattern is not yet implemented.
2. **Toast/notification system**: Error/success feedback currently relies on component-level rendering. A global toast provider would unify feedback.
3. **Request cancellation**: `AbortController` integration for in-flight request cleanup on unmount.
4. **Optimistic updates**: React Query mutation helpers with rollback.
5. **Constants type narrowing**: Enum values from constants could be used to generate TypeScript union types at build time.
6. **i18n**: Error messages are hardcoded in English.

# Frontend Implementation Principles

> Frozen: Step 05 — Tech Decisions & Dependency Budget  
> Branch: `agent/step-05-tech-decisions-and-deps`  
> Audience: Future implementation steps (agents and humans)

---

## 1. Folder Structure

```
frontend/src/
├── api/                    # API client, endpoint definitions
│   ├── client.ts           # fetch wrapper (auth header, refresh, error normalization)
│   ├── endpoints.ts        # URL constants per resource
│   └── types.ts            # API request/response types (if not covered by src/types/)
├── auth/                   # Auth primitives (already scaffolded in Step 04)
│   ├── permissions.ts      # P.CASES.VIEW_CASE etc.
│   ├── can.ts              # can(), canAll(), canAny(), hasMinHierarchy()
│   └── index.ts            # barrel export
├── components/             # Shared reusable components
│   ├── ui/                 # Generic UI: Button, Input, Modal, Skeleton, Toast, etc.
│   ├── guards/             # <ProtectedRoute>, <Can>
│   └── layout/             # AppLayout, Sidebar, Header, Footer
├── contexts/               # React Contexts
│   └── AuthContext.tsx      # AuthProvider + useAuth hook
├── hooks/                  # Custom reusable hooks
│   ├── useAuth.ts          # Re-export from context (convenience)
│   └── ...                 # useDebounce, useMediaQuery, etc.
├── pages/                  # One folder per top-level route
│   ├── Home/
│   ├── Login/
│   ├── Register/
│   ├── Dashboard/
│   ├── Cases/
│   ├── Evidence/
│   ├── DetectiveBoard/
│   ├── MostWanted/
│   ├── Reporting/
│   ├── Admin/
│   ├── Profile/
│   ├── Notifications/
│   ├── NotFound/
│   └── Forbidden/
├── router/                 # Router setup
│   ├── routes.ts           # Route config data (already exists from Step 03)
│   └── Router.tsx          # createBrowserRouter + lazy loading
├── types/                  # TypeScript types (already scaffolded in Step 03)
│   └── *.ts                # Domain types per module
├── utils/                  # Pure utility functions
│   ├── format.ts           # Date/number formatting
│   └── ...
├── App.tsx                 # Root component (wraps providers)
├── main.tsx                # Entry point (renders <App />)
├── index.css               # Global styles + CSS custom properties (design tokens)
└── vite-env.d.ts           # Vite env type declarations
```

### Naming Rules

| Item | Convention | Example |
|------|-----------|---------|
| Components | PascalCase | `CaseListPage.tsx`, `SkeletonCard.tsx` |
| Hooks | camelCase, `use` prefix | `useAuth.ts`, `useCaseList.ts` |
| Utilities | camelCase | `formatDate.ts`, `buildQueryString.ts` |
| Types | PascalCase, no `I` prefix | `Case`, `Evidence`, `User` |
| CSS Modules | camelCase classes | `styles.container`, `styles.headerNav` |
| Files | PascalCase for components, camelCase for everything else | — |
| Test files | `*.test.tsx` or `*.test.ts` co-located with source | `CaseList.test.tsx` |
| Constants | SCREAMING_SNAKE_CASE | `MAX_RETRY_COUNT` |

---

## 2. API Client Conventions

### Base client (`src/api/client.ts`)

```ts
// Conceptual shape — NOT final implementation code
async function apiFetch<T>(path: string, options?: RequestInit): Promise<ApiResponse<T>> {
  // 1. Prepend VITE_API_BASE_URL
  // 2. Inject Authorization: Bearer <token> (if token exists in memory)
  // 3. Set Content-Type: application/json (if body present)
  // 4. Call fetch()
  // 5. On 401 → attempt refresh → retry once → if fails → logout
  // 6. Parse response JSON → return { data, error, status }
}
```

### Rules

- **Never import `fetch` directly in components.** Always use `apiFetch` (or react-query hooks that call it).
- **API URLs** are centralized in `src/api/endpoints.ts` — no hardcoded paths in components.
- **Access token** is stored in a module-scoped variable (not React state, not localStorage). Only the auth module reads/writes it.
- **Refresh token** is stored in `localStorage` (backend doesn't support httpOnly cookies).
- **Error normalization**: All API errors are normalized to `{ message: string; status: number; field_errors?: Record<string, string[]> }` by the client, regardless of backend response shape.

---

## 3. Component Patterns

### Page components

```tsx
// src/pages/Cases/CaseListPage.tsx
export default function CaseListPage() {
  // 1. useQuery for data
  // 2. Loading → <CaseListSkeleton />
  // 3. Error → <ErrorMessage error={error} />
  // 4. Success → render <CaseList cases={data} />
}
```

### Rules

- **One default export per page** (enables `React.lazy()`).
- **Keep pages thin.** Pages orchestrate queries + layout. Business logic lives in hooks or utility functions.
- **Co-locate page-specific components** inside the page folder (e.g., `src/pages/Cases/CaseCard.tsx`). Move to `src/components/` only when shared across 2+ pages.
- **No `any` type.** Use `unknown` + type guards if the shape is uncertain.
- **No `// @ts-ignore` or `// eslint-disable`.** Fix the underlying issue.

### Loading states

Every async data load must show a skeleton or spinner:
- Use a `<Skeleton>` component that mimics the expected layout shape
- Place skeletons inside the component that owns the query, not at the page level
- For mutations, disable the trigger button and show an inline spinner

### Error handling

- API errors → show inline error near the relevant component
- Network errors → show a toast notification
- Form validation → show field-level error messages
- Never show raw error objects or stack traces to users

---

## 4. State Management Rules

1. **Server state** → `@tanstack/react-query`. Never store fetched API data in `useState` or Context.
2. **Auth state** → `AuthContext`. Single source of truth for user, permissions, and auth status.
3. **UI state** → `useState` / `useReducer` local to the component or page.
4. **Derived state** → Compute in render (`useMemo` only if profiling shows a perf issue).
5. **No prop drilling > 2 levels.** If data must pass through 3+ components, either lift the query or use Context.

---

## 5. TypeScript Rules

- **`erasableSyntaxOnly: true`** is enforced by tsconfig — no `enum`, no `namespace`, no `constructor` parameter properties.
- Use `as const` objects instead of enums (already done in `src/auth/permissions.ts`).
- Use **type** over **interface** unless extending is needed.
- All API response types must be defined in `src/types/` (already scaffolded).
- Generic utility types are fine (`Pick<T>`, `Omit<T>`, `Partial<T>`).
- All components must have typed props (no implicit `any` from missing types).

---

## 6. CSS Module Conventions

```css
/* CaseCard.module.css */
.container { /* ... */ }
.title { /* ... */ }
.statusBadge { /* ... */ }

/* Responsive */
@media (max-width: 640px) {
  .container { /* mobile adjustments */ }
}
```

### Rules

- One `.module.css` per component (co-located).
- Class names are camelCase.
- **No global styles** outside `src/index.css` (design tokens only).
- Responsive breakpoints: `640px` (mobile), `1024px` (tablet).
- Use CSS custom properties from `index.css` for colors, spacing, and font sizes — never hard-code hex values or pixel sizes in module files.

---

## 7. Testing Conventions

- Tests use `vitest` + `@testing-library/react`.
- Test files are co-located: `CaseList.test.tsx` next to `CaseList.tsx`.
- **Minimum 5 tests** (scoring requirement), target 8–12.
- Priority order for testing:
  1. Auth flow (login, token refresh, logout)
  2. Permission guards (`<ProtectedRoute>`, `<Can>`)
  3. Core page rendering (case list, evidence list)
  4. Form submission + validation
  5. Error state rendering
- Mock API calls using react-query's test utilities or `msw`.
- Never test implementation details (internal state, method calls). Test user-visible behavior.

---

## 8. Git & Workflow Rules

- **Never modify files in `backend/`.** The backend is read-only for all frontend steps.
- Commit messages: `type(scope): description` (e.g., `feat(cases): add case list page`).
- One feature branch per step: `agent/step-NN-description`.
- Run `tsc --noEmit` before committing — zero errors required.
- Run `eslint .` before committing — zero errors/warnings required (where possible).

---

## 9. Docker & Environment

- Frontend runs as a Vite dev server inside Docker (existing setup).
- `VITE_API_BASE_URL` env var controls the backend URL. Default: empty (same-origin proxy or `/api`).
- No CORS configuration needed when using Docker Compose (same-network).
- Production build: `vite build` generates static files in `dist/`. Can be served by nginx or any static server.

---

## 10. Performance Guidelines

- **Lazy load** every route except Home and Dashboard.
- **Avoid premature optimization.** No `useMemo`/`useCallback` unless profiling proves a bottleneck.
- **Image optimization**: Use WebP where possible; lazy-load images below the fold.
- **Bundle budget**: Keep the main chunk under 200 KB (gzip). Lazy chunks can be larger.
- **No unnecessary re-renders**: Keep Context providers narrow (AuthContext wraps the full app; any future context should wrap only the relevant subtree).

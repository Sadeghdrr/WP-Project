# Frontend Technical Decisions

> Frozen: Step 05 — Tech Decisions & Dependency Budget  
> Branch: `agent/step-05-tech-decisions-and-deps`  
> Constraint source: `project-doc.md` §1.4, §7 (CP2 scoring)

---

## 1. Routing

| Decision | Value |
|----------|-------|
| Library | `react-router-dom` v7 |
| Pattern | `createBrowserRouter` with a data-router; route config from `src/router/routes.ts` |
| Code-splitting | `React.lazy()` + `<Suspense>` for every route except `/` and `/dashboard` |
| Guards | `<ProtectedRoute>` wrapper reads `authRequired`, `minHierarchy`, `requiredPermissions` from route metadata |

**Rationale:** React Router is the standard for SPAs, counts as 1 package slot, and supports lazy routes natively. The route config from Step 03 already carries guard metadata.

---

## 2. Server-State & Data Fetching

| Decision | Value |
|----------|-------|
| Library | `@tanstack/react-query` v5 |
| Pattern | `useQuery` for reads, `useMutation` for writes |
| Caching | Query keys follow `[entity, id?, filters?]` convention |
| Loading states | Query `isLoading` / `isFetching` drives skeleton layouts (300 pts) |
| Error states | Query `error` object drives contextual error messages (100 pts) |
| Stale time | 30 s default; auth queries use 0 (always fresh) |
| Retry | 1 retry on failure, 0 for mutations |

**Rationale:** Directly satisfies three scoring categories (loading states, state management, error messages). Eliminates boilerplate for caching, refetch-on-focus, and request deduplication. 1 package slot.

---

## 3. HTTP Client

| Decision | Value |
|----------|-------|
| Library | **None** — native `fetch` API |
| Wrapper | `src/api/client.ts` — thin wrapper around `fetch` |
| Auth header | `Authorization: Bearer <access_token>` injected by wrapper |
| Refresh flow | On 401 → attempt silent refresh via `/api/accounts/token/refresh/` → retry original request → if refresh fails → logout |
| Base URL | Read from `import.meta.env.VITE_API_BASE_URL` (defaults to `/api`) |
| Response shape | Wrapper returns typed `{ data, error, status }` |

**Rationale:** `fetch` is browser-native, zero-cost, and sufficient for REST calls. Saving a package slot that would go to Axios. The thin wrapper provides interceptor-like behavior (auth injection, refresh, error normalization) without a dependency.

---

## 4. Local / Global State

| Decision | Value |
|----------|-------|
| Global state | React Context — **no additional state library** |
| Auth state | `AuthContext` (shape defined in Step 04 rbac-strategy.md §5) |
| UI state | Component-local `useState` / `useReducer` |
| Form state | Component-local `useState` (see §5) |
| Server state | Managed entirely by `@tanstack/react-query` (see §2) |

**Rationale:** The app has exactly one piece of truly global client state — the authenticated user. Everything else is either server-derived (react-query) or local to a component tree. Adding Zustand/Redux for one context is unjustifiable given the 6-package limit. Satisfies "Proper state management" (100 pts).

---

## 5. Forms

| Decision | Value |
|----------|-------|
| Library | **None** — native controlled components |
| Pattern | `useState` per form field, or `useReducer` for complex forms (case creation, evidence registration) |
| Validation | Custom `validate()` functions per form; inline error messages |
| Submission | `useMutation` from react-query wraps the API call |

**Rationale:** The project has ~8 forms (login, register, case creation ×2, evidence ×5 types, interrogation, verdict, bounty tip, bail). None are complex enough to justify a form library package. Controlled components + react-query mutations cover all flows.

---

## 6. Styling

| Decision | Value |
|----------|-------|
| Approach | **CSS Modules** (`.module.css` files) |
| Framework | **None** — no Tailwind, MUI, Ant Design |
| Responsive | CSS media queries + flexbox + CSS grid |
| Breakpoints | `≤ 640px` (mobile), `641–1024px` (tablet), `≥ 1025px` (desktop) |
| Design tokens | CSS custom properties in `src/index.css` (colors, spacing, typography) |
| Icons | Inline SVG components (no icon library package) |

**Rationale:** CSS Modules are built into Vite (zero config, zero packages). They provide scoped class names, preventing style leaks. Responsive design via media queries satisfies "Responsive Pages" (300 pts). No UI framework avoids bloat and preserves package slots for functional needs (Detective Board, image export).

---

## 7. Error & Loading UX (Cross-Cutting)

| Concern | Strategy |
|---------|----------|
| **Loading (initial)** | Full-page skeleton on route load |
| **Loading (data)** | Per-component skeleton or spinner driven by `useQuery.isLoading` |
| **Loading (mutation)** | Button disabled + spinner while `useMutation.isPending` |
| **Error (API)** | Contextual inline error message near the failed component |
| **Error (network)** | Toast notification at top-right |
| **Error (auth 401)** | Silent refresh → if fails → redirect to `/login` |
| **Error (auth 403)** | 403 page for route-level; disabled control + tooltip for action-level |
| **Error (404)** | Catch-all route renders Not Found page |
| **Error (form validation)** | Inline field-level error messages |

**Rationale:** This strategy maps 1:1 to the scoring items: "Displaying loading states and Skeleton Layout" (300 pts) and "Displaying appropriate error messages corresponding to each situation" (100 pts).

---

## 8. Testing

| Decision | Value |
|----------|-------|
| Runner | `vitest` (dev dependency, Vite-native) |
| DOM environment | `jsdom` (dev dependency) |
| Utilities | `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event` (all dev dependencies) |
| Minimum | 5 tests (scoring requirement) |
| Target | 8–12 tests covering: auth flow, permission guards, case list rendering, form validation, API error handling |
| Pattern | Arrange → Act → Assert; mock API calls via `msw` or react-query's test utilities |

**Rationale:** Vitest is the natural choice for a Vite project (shared config, fast). Testing Library is the React community standard. All are dev dependencies and do NOT count toward the 6-package limit. Satisfies "Presence of at least 5 tests" (100 pts).

---

## 9. Build & Environment Config

| Decision | Value |
|----------|-------|
| Bundler | Vite 7 + SWC (already configured) |
| Environments | `.env.development`, `.env.production` (Vite convention) |
| Key env vars | `VITE_API_BASE_URL` (backend URL, default `/api`) |
| Docker | Existing `Dockerfile` (node:20-alpine) + `docker-compose.yaml` frontend service — no changes needed |
| Dev server | `vite --host 0.0.0.0 --port 5173` (HMR via Docker volume mount) |
| Production build | `vite build` → `dist/` static files |
| Path aliases | Optional: `@/` → `src/` via `tsconfig.app.json` paths + Vite `resolve.alias` |

**Rationale:** Existing Docker setup is complete. Vite handles env vars via `import.meta.env.VITE_*` prefix. No additional build tooling needed. Satisfies "Dockerizing the entire project and using Docker Compose" (300 pts).

---

## 10. Detective Board (Special Consideration)

| Decision | Value |
|----------|-------|
| Library | `@xyflow/react` (React Flow v12) |
| Drag-drop | Built-in node dragging |
| Connections | Built-in edge creation/deletion (styled as red lines via custom edge config) |
| Notes | Custom node type for notes |
| Documents/Evidence | Custom node types rendering evidence/document summaries |
| Image export | `html-to-image` library → `toPng()` of the board container |
| Persistence | Board state serialized to JSON → `POST/PATCH /api/board/` |

**Rationale:** The Detective Board is 800 pts and requires drag-drop placement, connections (red lines), and image export. @xyflow/react is purpose-built for node-edge graph UIs. `html-to-image` (~8 KB, zero deps) handles the image export requirement. These consume the remaining 2 package slots.

---

## Decision Summary Table

| Area | Choice | Package Slot? |
|------|--------|:------------:|
| Routing | react-router-dom | ✅ (3/6) |
| Server state | @tanstack/react-query | ✅ (4/6) |
| HTTP client | Native fetch | — |
| Global state | React Context | — |
| Forms | Native controlled components | — |
| Styling | CSS Modules | — |
| Detective Board | @xyflow/react | ✅ (5/6) |
| Board export | html-to-image | ✅ (6/6) |
| Testing | Vitest + Testing Library | dev only |
| Build | Vite + SWC | existing |

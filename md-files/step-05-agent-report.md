# Step 05 Agent Report — Tech Decisions & Dependency Budget

> **Branch:** `agent/step-05-tech-decisions-and-deps`  
> **Based on:** `master` (latest)  
> **Depends on:** Steps 01–04 (requirements matrix, API contract, domain model, RBAC strategy)

---

## 1. Files Created / Changed

| File | Action | Purpose |
|------|--------|---------|
| `frontend/docs/tech-decisions.md` | Created | Frozen architecture decisions across 10 areas (routing, server-state, HTTP, global state, forms, styling, error/loading UX, testing, build/env, Detective Board) |
| `frontend/docs/dependency-budget.md` | Created | 6-package runtime budget with justification; dev/test deps listed separately; "avoid" list of 16 packages |
| `frontend/docs/implementation-principles.md` | Created | Coding conventions: folder structure, naming, API client, component patterns, state rules, CSS modules, testing, git workflow |
| `md-files/step-05-agent-report.md` | Created | This report |

**Total:** 4 new files (3 docs + 1 report). Zero backend files modified. Zero packages installed.

---

## 2. Summary of Frozen Technical Decisions

| Area | Decision |
|------|----------|
| **Routing** | `react-router-dom` v7 with `createBrowserRouter`, lazy routes via `React.lazy()` + `<Suspense>` |
| **Server-state** | `@tanstack/react-query` v5 — `useQuery` / `useMutation` for all API calls |
| **HTTP client** | Native `fetch` wrapped in `src/api/client.ts` (zero-dep, auth injection, refresh-on-401) |
| **Global state** | React Context — `AuthContext` only. No Redux/Zustand. |
| **Forms** | Native controlled components + `useState`/`useReducer`. No form library. |
| **Styling** | CSS Modules (`.module.css`, built into Vite, zero config). Responsive via media queries. No UI framework. |
| **Error/Loading** | Skeleton components for loading, inline errors for API failures, toast for network errors, 403/404 pages for route-level errors |
| **Testing** | Vitest + @testing-library/react (all dev deps). Min 5 tests, target 8–12. |
| **Build/Env** | Vite 7 + SWC (existing). `VITE_API_BASE_URL` env var. Existing Docker setup unchanged. |
| **Detective Board** | `@xyflow/react` (node-edge graph) + `html-to-image` (PNG export) |

---

## 3. Dependency Budget Summary

### Approved Runtime (6/6 slots)

| Slot | Package | Points supported |
|:----:|---------|-----------------|
| 1 | `react` | Mandated stack |
| 2 | `react-dom` | Mandated stack |
| 3 | `react-router-dom` | All page navigation |
| 4 | `@tanstack/react-query` | Loading (300), state mgmt (100), errors (100) |
| 5 | `@xyflow/react` | Detective Board (800) |
| 6 | `html-to-image` | Board image export (part of 800) |

### Approved Dev/Test (exempt from limit)

`vitest`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`

### Avoided (16 packages explicitly rejected)

axios, redux, zustand, jotai, recoil, react-hook-form, formik, tailwindcss, @mui/material, antd, styled-components, framer-motion, chart.js, d3, socket.io-client, lodash, moment/dayjs/date-fns, i18next, react-dnd, konva

---

## 4. Risks & Constraints from project-doc.md

### Hard Constraints

| Constraint | Source | Impact on decisions |
|------------|--------|---------------------|
| Max 6 NPM packages (must be documented in report) | §1.4 | Budget is now fully allocated — any new runtime dep requires dropping one |
| React or NextJS only | §2.3 | Confirmed: using React (Vite SPA) |
| Frontend tests ≥ 5 | §7 | Testing stack approved as dev deps |
| Docker Compose required | §7 | Existing docker-compose.yaml already handles frontend service |
| Proper state management required | §7 | Addressed by react-query (server) + Context (auth) + local state (UI) |
| Responsive pages required | §7 | CSS Modules + media queries; no framework needed |
| Loading/skeleton states required | §7 | react-query `isLoading` + Skeleton components |
| Error messages per situation | §7 | Inline errors, toasts, 403/404 pages |

### Risks

| Risk | Mitigation |
|------|------------|
| **0 package slots remaining** — any unforeseen need (e.g., date picker, drag-drop outside board) must be solved with browser APIs | Keep the avoid list visible in all steps. If truly needed, re-evaluate @xyflow/react alternatives. |
| **CSS Modules lack a component library** — every UI element (buttons, modals, inputs) must be built from scratch | Start with a small `src/components/ui/` library. ~10 base components cover 90% of needs. |
| **No charting library** — home page stats (§5.1) must use raw HTML/CSS | Stats are simple counters/percentages. HTML `<div>` bars with CSS widths are sufficient. |
| **Native fetch has no interceptor API** — refresh-on-401 logic requires careful implementation | The `apiFetch` wrapper handles this with a queued retry pattern. Must be tested thoroughly. |
| **@xyflow/react may increase bundle size** — ~150 KB gzip | Lazy-loaded on the Detective Board route only. Won't affect initial page load. |

---

## 5. Traceability: project-doc §7 Scoring Items

| Scoring Item | Points | Addressed By |
|--------------|:------:|--------------|
| Home Page | 200 | Route config (Step 03), lazy loading, CSS Modules responsive |
| Login and Registration Page | 200 | Route config, native form components, AuthContext |
| Modular Dashboard | 800 | Route config, permission guards (`<Can>`), react-query per module |
| Detective Board | 800 | `@xyflow/react` + `html-to-image` + custom node types |
| Most Wanted | 300 | Route config, react-query for data, CSS Modules for ranking display |
| Case and Complaint Status | 200 | Route config, react-query, permission-gated status transitions |
| General Reporting | 300 | Route config, react-query, hierarchy guard |
| Evidence Registration and Review | 200 | Route config, polymorphic form handling, react-query mutations |
| Admin Panel | 200 | Route config, permission guard (SysAdmin), react-query CRUD |
| Loading states / Skeleton Layout | 300 | `@tanstack/react-query` `isLoading` + `<Skeleton>` components |
| Dockerizing entire project | 300 | Existing `docker-compose.yaml` + `Dockerfile` — no changes needed |
| Frontend tests ≥ 5 | 100 | Vitest + @testing-library/react (approved dev deps) |
| Proper state management | 100 | react-query (server) + AuthContext (global) + useState (local) |
| Responsive pages | 300 | CSS Modules + media queries (640/1024 breakpoints) |
| Best practices | 150 | Folder structure, naming conventions, typed props, no `any` |
| Component lifecycles | 100 | useEffect cleanup, react-query handles unmount cancellation |
| Error messages per situation | 100 | Inline errors, toast notifications, 403/404 pages |
| Code modifiability | 100 | Modular folder structure, thin pages, co-located tests |
| **Total addressable** | **4750** | All items have a concrete implementation strategy |

---

## 6. Confirmation

- [x] `frontend/docs/tech-decisions.md` — 10 decision areas frozen with rationale
- [x] `frontend/docs/dependency-budget.md` — 6/6 runtime slots allocated, 16 packages explicitly avoided
- [x] `frontend/docs/implementation-principles.md` — folder structure, naming, API client, component patterns, state rules, CSS, testing, git workflow
- [x] All project-doc §7 scoring items traced to specific technical decisions
- [x] Zero backend files modified
- [x] Zero packages installed (planning step only)
- [x] Consistent with Steps 01–04 (RBAC strategy, route config, domain types, requirements matrix)

# Frontend Dependency Budget

> Frozen: Step 05 — Tech Decisions & Dependency Budget  
> Branch: `agent/step-05-tech-decisions-and-deps`  
> Hard constraint: **Maximum 6 NPM runtime packages** (project-doc §1.4)

---

## Budget Overview

| Slot | Package | Status |
|:----:|---------|--------|
| 1 | `react` | Already installed |
| 2 | `react-dom` | Already installed |
| 3 | `react-router-dom` | **Approved** — to install in implementation steps |
| 4 | `@tanstack/react-query` | **Approved** — to install in implementation steps |
| 5 | `@xyflow/react` | **Approved** — to install when building Detective Board |
| 6 | `html-to-image` | **Approved** — to install when building Detective Board export |

**Slots remaining: 0 / 6**

---

## 1. Runtime Dependencies — Already Installed

| Package | Version | Purpose |
|---------|---------|---------|
| `react` | ^19.2.0 | UI library (mandated by project-doc §2.3) |
| `react-dom` | ^19.2.0 | React DOM renderer |

---

## 2. Runtime Dependencies — Approved (to install)

### 2.1 `react-router-dom`

| Field | Value |
|-------|-------|
| Target version | ^7.x |
| Size | ~58 KB (gzip) |
| Purpose | Client-side routing, code-splitting, route guards |
| Justification | Required for SPA navigation across 9+ pages. Supports `createBrowserRouter`, lazy routes, and route metadata consumed by `<ProtectedRoute>` guards. The de facto React routing standard. |
| Install timing | Step 06+ (auth/layout implementation) |

### 2.2 `@tanstack/react-query`

| Field | Value |
|-------|-------|
| Target version | ^5.x |
| Size | ~40 KB (gzip) |
| Purpose | Server-state management, data caching, loading/error state |
| Justification | Provides `useQuery`/`useMutation` hooks with built-in loading, error, and caching states. Directly satisfies "Loading states and Skeleton Layout" (300 pts), "Proper state management" (100 pts), and "Error messages" (100 pts). Eliminates boilerplate for request deduplication, retry, and refetch-on-focus. |
| Install timing | Step 06+ (when first API integration begins) |

### 2.3 `@xyflow/react`

| Field | Value |
|-------|-------|
| Target version | ^12.x |
| Size | ~150 KB (gzip) |
| Purpose | Detective Board — node/edge graph with drag-drop and connections |
| Justification | The Detective Board (800 pts) requires: (1) placing documents/notes anywhere via drag-drop, (2) connecting items with red lines, (3) adding/removing connections, (4) positional persistence. @xyflow/react is purpose-built for this exact use case — draggable nodes, configurable edges, custom node types, and viewport controls. Building this from scratch with HTML5 drag API + SVG would take 3–5× the implementation time with worse UX. |
| Install timing | Detective Board implementation step |

### 2.4 `html-to-image`

| Field | Value |
|-------|-------|
| Target version | ^1.x |
| Size | ~8 KB (gzip) |
| Purpose | Export Detective Board as PNG image |
| Justification | Project-doc §5.4 requires "export [board] as an image so the Detective can attach it to their report." `html-to-image` converts any DOM node to PNG/JPEG/SVG with `toPng()`. Zero dependencies, tiny footprint. The alternative (Canvas API manual rendering) is unreliable for complex DOM structures. |
| Install timing | Detective Board implementation step |

---

## 3. Dev / Test Dependencies — Approved (exempt from 6-package limit)

These are development-only tools. They do NOT ship in the production bundle and do NOT count toward the 6-package limit.

### Already installed

| Package | Purpose |
|---------|---------|
| `typescript` ~5.9.3 | Type checking |
| `vite` ^7.3.1 | Bundler / dev server |
| `@vitejs/plugin-react-swc` ^4.2.2 | SWC compiler for React |
| `eslint` ^10.0.2 | Linting |
| `@eslint/js` ^9.39.1 | ESLint JS config |
| `eslint-plugin-react-hooks` ^7.0.1 | React hooks linting |
| `eslint-plugin-react-refresh` ^0.4.24 | React Refresh linting |
| `typescript-eslint` ^8.48.0 | TypeScript ESLint parser |
| `globals` ^16.5.0 | ESLint globals |
| `@types/react` ^19.2.7 | React type definitions |
| `@types/react-dom` ^19.2.3 | ReactDOM type definitions |
| `@types/node` ^24.10.1 | Node.js type definitions |

### To install (testing)

| Package | Purpose | Install timing |
|---------|---------|----------------|
| `vitest` | Test runner (Vite-native, fast) | Testing step |
| `jsdom` | DOM environment for tests | Testing step |
| `@testing-library/react` | React component testing utilities | Testing step |
| `@testing-library/jest-dom` | DOM assertion matchers (`toBeInTheDocument`, etc.) | Testing step |
| `@testing-library/user-event` | Simulates user interactions (click, type, etc.) | Testing step |

### Optional dev dependencies (install only if needed)

| Package | Purpose | When |
|---------|---------|------|
| `msw` (Mock Service Worker) | API mocking in tests | If react-query test utils are insufficient |
| `@tanstack/react-query-devtools` | React Query dev panel | During development, tree-shaken in production |

---

## 4. Avoid / Not Needed List

These packages are explicitly NOT approved. Adding any of them requires re-evaluating the 6-package budget.

| Package | Reason to avoid |
|---------|-----------------|
| `axios` | Native `fetch` + thin wrapper is sufficient; saves a package slot |
| `redux` / `@reduxjs/toolkit` | Overkill — only one global state slice (auth). React Context suffices |
| `zustand` / `jotai` / `recoil` | Same reason as Redux; not justified for one context |
| `react-hook-form` / `formik` | ~8 forms in the app, none complex enough to justify a dependency |
| `tailwindcss` | Requires PostCSS config + generates large CSS; CSS Modules are zero-config in Vite |
| `@mui/material` / `antd` / `chakra-ui` | Heavy UI frameworks; would dominate the package budget and bundle size |
| `styled-components` / `@emotion/react` | CSS-in-JS adds runtime overhead; CSS Modules provide scoping without cost |
| `framer-motion` / `react-spring` | Animations are nice-to-have but not scored; not worth a slot |
| `chart.js` / `recharts` / `d3` | Home page stats can be rendered with simple HTML/CSS bar/number displays |
| `socket.io-client` | Backend is REST-only; polling handles notifications |
| `moment` / `dayjs` / `date-fns` | `Intl.DateTimeFormat` and `Date` are sufficient for display formatting |
| `lodash` | Modern JS (structuredClone, Array.prototype.at, Object.groupBy) covers all needs |
| `i18next` | App is single-language (English/Persian); no i18n scoring requirement |
| `react-dnd` | @xyflow/react includes built-in drag-drop; separate DnD library is redundant |
| `konva` / `fabric.js` | Canvas-based alternatives to @xyflow/react; worse fit for node-edge graphs |

---

## 5. Budget Allocation Rationale

```
6 package slots
├── 2 × mandated framework    → react, react-dom
├── 1 × routing               → react-router-dom
├── 1 × server-state          → @tanstack/react-query
└── 2 × detective board       → @xyflow/react, html-to-image
    (800 pts — highest-value single page)
```

### Why this allocation maximizes score:

1. **Routing** is non-negotiable for a multi-page SPA.
2. **React Query** directly satisfies 3 scoring items (loading 300, state 100, errors 100 = **500 pts**).
3. **Detective Board libraries** enable the single highest-value page (**800 pts**) without weeks of custom canvas/SVG work.
4. **Everything else** (HTTP, forms, styling, global state, date formatting, charts) is achievable with browser-native APIs + minimal custom code.

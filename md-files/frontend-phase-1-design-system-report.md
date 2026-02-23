# Frontend Phase-1 Design System & Core Components Report

> **Phase:** 1 – Design System & Core Components  
> **Stack:** React 19.2 · TypeScript 5.9 · Vite 7.3 (SWC)  
> **Depends on:** Phase 0 Foundation (fully implemented)

---

## 1. Executive Summary

Phase 1 delivers a **complete design system** and **reusable component library** that forms the building blocks for all feature pages. Every component is type-safe, responsive, accessible, and supports loading/error states. No feature pages were implemented — only the reusable infrastructure they will consume.

### Components Delivered

| Category | Count | Components |
|---|---|---|
| **UI Primitives** | 6 | Button, Input, Textarea, Select, Badge, Skeleton, Loader |
| **UI Composites** | 7 | Card, Modal, Drawer, Table, Pagination, Tabs, Alert |
| **Toast System** | 1 | ToastProvider + useToast hook |
| **Dashboard** | 1 | ModuleCard |
| **Guards** | 2 | PermissionGate (refined), RoleGuard (new) |
| **Layouts** | 5 | ProtectedRoute (refined), AuthLayout, PublicLayout, DashboardLayout, Sidebar, Topbar |

**Total: 22 component implementations + 1 CSS design system + 1 context provider**

---

## 2. Created Components

### 2.1 UI Primitives

#### Button (`components/ui/Button.tsx`)
- **Variants:** `primary`, `secondary`, `danger`, `ghost`, `outline`
- **Sizes:** `sm`, `md`, `lg`
- **States:** loading (spinner overlay), disabled, fullWidth
- **Props:** Extends `ButtonHTMLAttributes` — fully compatible with native button props
- **Accessibility:** Focus-visible outline, disabled state prevents interaction

#### Input (`components/ui/Input.tsx`)
- Auto-generated `id` via `useId()` for label association
- **Props:** `label`, `error`, `hint`, `size`, `required` indicator
- **Accessibility:** `aria-invalid`, `aria-describedby` linking to error message, `role="alert"` on errors

#### Textarea (`components/ui/Input.tsx`)
- Co-located with Input for consistency
- Shares form-field styling, supports `label`, `error`, `hint`
- Vertical resize enabled, min-height set

#### Select (`components/ui/Select.tsx`)
- **Props:** `options: SelectOption[]`, `placeholder`, `label`, `error`, `size`
- Custom dropdown chevron via CSS background-image (no JS dependency)
- Same form-field styling as Input for visual consistency

#### Badge (`components/ui/Badge.tsx`)
- **Variants:** `success`, `warning`, `danger`, `info`, `neutral`, `primary`
- **Sizes:** `sm`, `md`
- Suitable for statuses (case status, suspect status, crime level, etc.)

#### Skeleton (`components/ui/Skeleton.tsx`)
- **Variants:** `text`, `rectangular`, `circular`
- **Props:** `width`, `height`, `count` (renders multiple)
- CSS shimmer animation for loading placeholders
- Used internally by Table and ModuleCard for loading states

#### Loader (`components/ui/Loader.tsx`)
- **Sizes:** `sm`, `md`, `lg` (spinner diameter scales)
- **Modes:** inline or `fullScreen` (fixed overlay)
- **Props:** optional `label` displayed below spinner
- Used by ProtectedRoute and AppRouter for auth/page loading

### 2.2 UI Composites

#### Card (`components/ui/Card.tsx`)
- **Sections:** optional header (title + subtitle + actions), body, footer
- **Props:** `padding` (flush body for custom content), `hoverable` (lift effect)
- Foundation for evidence cards, case cards, report cards

#### Modal (`components/ui/Modal.tsx`)
- Portal-based rendering (`createPortal` → `document.body`)
- **Keyboard:** Escape to close
- **Scroll lock:** `document.body.style.overflow = 'hidden'` while open
- **Sizes:** `sm` (400px), `md` (560px), `lg` (800px)
- **Props:** `closeOnOverlay`, `footer` for action buttons
- CSS animations: fade-in overlay + slide-up content

#### Drawer (`components/ui/Drawer.tsx`)
- Slide-in panel from `left` or `right`
- Same portal + keyboard + scroll-lock pattern as Modal
- **Sizes:** `sm` (320px), `md` (480px), `lg` (640px)
- Full-width on mobile (≤640px)
- Suitable for filters, detail panels, detective board notes

#### Table (`components/ui/Table.tsx`)
- **Generic:** `Table<T>` — column config with typed render functions
- **Column config:** `key`, `header`, `render?`, `sortable?`, `width?`, `align?`
- **Features:** sort indicators (↕ ↑ ↓), clickable rows, empty state message
- **Loading:** Renders 5 skeleton rows matching column count
- **Props:** `rowKey` function for stable React keys

#### Pagination (`components/ui/Pagination.tsx`)
- Intelligent ellipsis compression (shows first, last, and ±1 around current)
- **Props:** `currentPage`, `totalPages`, `onPageChange`, `totalItems`
- Hidden when `totalPages ≤ 1`
- ARIA: `aria-label="Pagination"`, `aria-current="page"` on active button

#### Tabs (`components/ui/Tabs.tsx`)
- **Modes:** Controlled (`activeKey` prop) or uncontrolled (`defaultActiveKey`)
- **Props:** `tabs: TabItem[]` with `key`, `label`, `content`, `disabled?`, `icon?`
- ARIA: `role="tablist"`, `role="tab"`, `role="tabpanel"`, `aria-selected`
- Horizontal scroll on overflow

#### Alert (`components/ui/Alert.tsx`)
- Inline contextual message banner
- **Types:** `success`, `error`, `warning`, `info`
- **Props:** optional `title`, optional `onClose` dismiss button
- Left border accent color for visual distinction
- Used by ProtectedRoute for 403 display

### 2.3 Toast System

#### ToastContext (`context/ToastContext.tsx`)
- Self-contained context + provider + hook + UI in one module
- **Provider:** `<ToastProvider>` wraps the app (added to App.tsx)
- **Hook:** `useToast()` returns `{ toast, success, error, warning, info, dismiss, dismissAll }`
- **Auto-dismiss:** 4s default duration, configurable per toast
- **Rendering:** Fixed top-right container, slide-in animation
- **Re-export:** `hooks/useToast.ts` for import consistency

### 2.4 Dashboard

#### ModuleCard (`components/dashboard/ModuleCard.tsx`)
- Dashboard metric card with icon, value, subtitle, and trend indicator
- **Trend:** directional arrow (↑ ↓ →) with percentage, color-coded
- **Loading:** Skeleton placeholder (circular icon + text lines)
- **Interaction:** optional `onClick` with keyboard support (Enter/Space)
- **Children:** optional slot for custom content below the metric
- Designed to power the Modular Dashboard (800pts requirement)

### 2.5 Guards

#### PermissionGate (`components/guards/PermissionGate.tsx`)
- **Refined:** exported `PermissionGateProps` interface for external type use
- Conditionally renders children based on permission codenames
- **Props:** `permissions[]`, `requireAll?`, `fallback?`

#### RoleGuard (`components/guards/RoleGuard.tsx`) — **NEW**
- Extends PermissionGate concept with hierarchy support
- **Props:** `permissions[]`, `requireAll?`, `minHierarchy?`, `fallback?`
- Checks both permission codenames AND role hierarchy level
- No hardcoded role names — uses dynamic permission + hierarchy level checks

### 2.6 Layout Refinements

#### ProtectedRoute (`components/layout/ProtectedRoute.tsx`)
- **Loading:** Now shows `<Loader fullScreen label="Authenticating…" />` instead of `null`
- **403 display:** Now uses `<Alert type="error">` instead of raw HTML
- **Type fix:** Uses `ReactNode` instead of `React.ReactNode` with proper import

#### AppRouter (`routes/AppRouter.tsx`)
- Page loading fallback now uses `<Loader fullScreen label="Loading page…" />`

---

## 3. Structural Decisions

### 3.1 Folder Organization

```
src/components/
├── ui/                     # Generic, reusable UI primitives & composites
│   ├── ui.css              # All component styles (BEM, CSS vars)
│   ├── index.ts            # Barrel export with CSS side-effect import
│   ├── Button.tsx
│   ├── Input.tsx           # Input + Textarea
│   ├── Select.tsx
│   ├── Badge.tsx
│   ├── Skeleton.tsx
│   ├── Loader.tsx
│   ├── Card.tsx
│   ├── Modal.tsx
│   ├── Drawer.tsx
│   ├── Table.tsx
│   ├── Pagination.tsx
│   ├── Tabs.tsx
│   └── Alert.tsx
├── guards/                 # RBAC conditional rendering
│   ├── index.ts
│   ├── PermissionGate.tsx
│   └── RoleGuard.tsx
├── dashboard/              # Dashboard-specific reusable components
│   ├── index.ts
│   └── ModuleCard.tsx
└── layout/                 # App shell & navigation
    ├── index.ts
    ├── ProtectedRoute.tsx
    ├── AuthLayout.tsx
    ├── PublicLayout.tsx
    ├── DashboardLayout.tsx
    ├── Sidebar.tsx
    └── Topbar.tsx
```

### 3.2 CSS Strategy

**Approach:** Single `ui.css` file using BEM naming + CSS custom properties.

**Why a single file instead of per-component CSS modules:**
- All components share a common visual language (colors, spacing, radii)
- BEM prevents class name collisions without CSS modules tooling
- Single file avoids import-order issues and simplifies the bundle
- CSS custom properties from `global.css` provide theming control

**Import chain:**
1. `main.tsx` → `index.css` (reset) + `assets/styles/global.css` (design tokens)
2. `App.tsx` → `App.css` (layout styles)
3. `components/ui/index.ts` → `ui.css` (component styles, side-effect import)

### 3.3 Prop Design Philosophy

| Principle | Example |
|---|---|
| **Extend native props** | `ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>` |
| **Consistent naming** | `variant`, `size`, `loading`, `disabled` across all components |
| **Optional with sensible defaults** | `variant = 'primary'`, `size = 'md'` |
| **Support `className` override** | Every component accepts `className` for custom styling |
| **No business logic** | Components accept data props, never fetch or mutate |
| **Generic types** | `Table<T>`, `Column<T>` — no hardcoded entity types |

### 3.4 Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Component file | PascalCase | `ModuleCard.tsx` |
| CSS class | BEM kebab-case | `.module-card__header` |
| Export | Named (no defaults) | `export function Button(...)` |
| Props interface | `ComponentNameProps` | `ButtonProps`, `ModalProps` |
| Hook | `use` prefix | `useToast`, `useAuth` |

---

## 4. Design Principles

### 4.1 Loading States

Every component that can be in a loading state has explicit support:
- **Table:** 5 skeleton rows matching column layout
- **ModuleCard:** Circular + text skeleton placeholders
- **Button:** Spinner overlay with hidden label
- **Loader:** Standalone spinner for page-level loading
- **ProtectedRoute:** Full-screen loader during auth hydration

### 4.2 Error & Disabled States

- **Input/Select/Textarea:** Red border + error message on validation failure
- **Button:** Opacity reduction + `cursor: not-allowed` when disabled
- **Alert:** Inline error banners with accent colors
- **Toast:** Auto-dismissing notifications for transient errors/successes
- **ProtectedRoute:** Alert component for 403 forbidden state

### 4.3 Responsiveness

- **Drawer:** Full-width on screens ≤640px
- **Modal:** Margin reduction on small screens
- **Pagination:** Stacks vertically on mobile
- **Toast container:** Stretches full-width on mobile
- **Sidebar:** Collapses/slides out on ≤768px (from Phase 0)
- **Table:** Horizontal scroll wrapper on overflow

### 4.4 Accessibility

- **Labels:** `htmlFor`/`id` association on all form fields
- **Errors:** `aria-invalid`, `aria-describedby`, `role="alert"`
- **Modals/Drawers:** `role="dialog"`, `aria-modal="true"`, `aria-label`
- **Tabs:** Full ARIA tablist/tab/tabpanel pattern
- **Keyboard:** Escape closes modals/drawers, all interactive elements focusable
- **Loading:** `role="status"`, `aria-label` on loaders, `aria-hidden` on skeletons
- **Focus:** `:focus-visible` outlines on buttons

### 4.5 Dark Mode

All components support `prefers-color-scheme: dark` via CSS media queries:
- Surface colors shift to dark grays
- Text colors shift to light tones
- Borders, backgrounds, and shadows adapt
- Skeleton shimmer uses darker gradient

---

## 5. How This Supports Grading Criteria

### Chapter 7 — Frontend Grading

| Criterion | Points | Phase 1 Support |
|---|---|---|
| **Modular Dashboard** | 800 | `ModuleCard` component with loading states, trends, click actions, children slot. Ready for feature pages to compose dashboard modules. |
| **Detective Board** | 800 | `Card` (for board items), `Modal` (for note editing), `Drawer` (for side panels), `Badge` (for item tags), `Loader` (for board loading). Structural components ready. |
| **UI/UX Quality** | — | Consistent design tokens, animations, hover states, accessibility, dark mode |
| **Loading States** | — | Every component has explicit loading support. Skeleton, Loader, Button spinner |
| **Responsive Pages** | — | Media queries at 640px and 768px breakpoints. Fluid layouts |
| **Clean Architecture** | — | BEM CSS, barrel exports, generic types, no hardcoded business logic |
| **Code Modifiability** | — | Components are atomic and composable. Adding new variants or sizes is a CSS-only change |

### Modular Dashboard Readiness

The dashboard can be built by composing these Phase 1 components:
```tsx
<div className="dashboard-grid">
  <ModuleCard title="Active Cases" value={42} trend={{ value: 12, direction: 'up' }} />
  <ModuleCard title="Evidence Items" value={156} />
  <Card title="Recent Cases">
    <Table columns={caseColumns} data={recentCases} rowKey={(c) => c.id} />
  </Card>
  <Card title="Alerts">
    <Alert type="warning">3 cases pending review</Alert>
  </Card>
</div>
```

### Detective Board Compatibility

Board features can consume:
- `Card` → board items (evidence, suspects, notes)
- `Modal` → editing board notes, item details
- `Drawer` → side panel for item connections
- `Badge` → status tags on board items
- `Button` → board actions (add item, connect, export)
- `Alert` → board notifications
- `Loader` → board loading state

---

## 6. Phase 0 Refactors

| Component | Change | Reason |
|---|---|---|
| **ProtectedRoute** | Loading: `null` → `<Loader fullScreen>`, 403: `<div>` → `<Alert>` | Proper UX for loading/error states |
| **AppRouter** | PageLoader: `<div>Loading…</div>` → `<Loader fullScreen>` | Consistent with design system |
| **PermissionGate** | Exported `PermissionGateProps` interface | Enables type consumption by other modules |
| **App.tsx** | Added `ToastProvider` wrapping, `App.css` import | Toast system integration, CSS was missing |
| **main.tsx** | Added `global.css` import | Design tokens were defined but never imported |
| **guards/index.ts** | Added `RoleGuard` export | New guard component |

---

## 7. Provider Stack

After Phase 1, the provider composition in App.tsx is:

```
StrictMode
  └── QueryClientProvider    (React Query cache)
       └── AuthProvider      (JWT auth state)
            └── ToastProvider (toast notifications)
                 └── AppRouter (routing + layouts)
```

---

## 8. CSS Import Chain

```
main.tsx
  ├── index.css              → CSS reset, base typography
  └── assets/styles/global.css → CSS custom properties (design tokens)

App.tsx
  └── App.css                → Layout structure styles (sidebar, topbar, etc.)

components/ui/index.ts
  └── ui.css                 → All UI component styles (BEM, animations, dark mode)
```

---

## 9. Future Extension Considerations

### Adding a New UI Component
1. Create `components/ui/NewComponent.tsx` with exported props interface
2. Add CSS rules to `ui.css` using BEM naming
3. Add barrel export in `components/ui/index.ts`
4. No other files need to change

### Adding a New Variant to an Existing Component
1. Add the variant to the TypeScript union type
2. Add the `.component--new-variant` CSS class
3. No structural changes needed

### Adding a New Dashboard Module
1. Use `ModuleCard` for metrics or `Card` for content
2. Compose with Table, Badge, Alert as needed
3. Wrap in `PermissionGate` or `RoleGuard` for RBAC

### Adding a New Design Token
1. Add the CSS custom property to `global.css`
2. Reference it in `ui.css` with a fallback value: `var(--new-token, fallback)`

---

## 10. Build Verification

```
$ npx tsc -b
(zero errors — clean exit)
```

TypeScript compilation passes under strict mode with all strict flags enabled (`strict`, `noUnusedLocals`, `noUnusedParameters`, `erasableSyntaxOnly`, `verbatimModuleSyntax`).

> Note: `vite build` requires platform-specific rollup binaries (`@rollup/rollup-win32-x64-msvc`) which are installed in the Docker build environment, not the local dev environment. This is expected for the Docker-based project setup.

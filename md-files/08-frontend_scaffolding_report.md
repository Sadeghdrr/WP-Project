# Frontend Architecture & Scaffolding Report

## 1. Overview

This document outlines the architectural decisions and directory structure established during the initial frontend scaffolding phase of the L.A. Noire-inspired Police Department Management System.

The frontend is built using **React**, **TypeScript**, and **Vite**. To ensure maintainability, scalability, and a seamless integration with the Django REST Framework (DRF) backend, we have adopted a **Feature-Sliced / Domain-Driven Architecture**. This approach mirrors the backend's app structure, reducing cognitive load and making it easier to locate related code.

---

## 2. Architectural Pattern

Instead of grouping files purely by technical type (e.g., all components in one folder, all state in another), the architecture separates **global/shared concerns** from **domain-specific business logic**.

### Key Principles:

1. **Separation of Concerns:** UI components are strictly separated from business logic and API calls.
2. **Domain Alignment:** Frontend features (`cases`, `evidence`, `suspects`, `board`, `auth`) map 1:1 with backend DRF apps.
3. **Strict Typing:** Comprehensive TypeScript interfaces mirror backend models to ensure end-to-end type safety.
4. **Centralized RBAC:** Role-Based Access Control is managed globally via Context and custom hooks, utilizing the exact permission codenames defined in the backend.

---

## 3. Directory Structure Breakdown

The `src/` directory is organized as follows:

### `assets/`

Contains static assets such as images, fonts, and global stylesheets (`global.css`).

### `types/`

Holds global TypeScript interfaces that mirror the backend data models.

- `user.types.ts`: `User`, `Role`
- `case.types.ts`: `Case`, `CaseComplainant`, `CaseWitness`, `CaseStatusLog`
- `evidence.types.ts`: `Evidence`, `TestimonyEvidence`, `BiologicalEvidence`, etc.
- `suspect.types.ts`: `Suspect`, `Interrogation`, `Trial`, `BountyTip`, `Bail`
- `board.types.ts`: `DetectiveBoard`, `BoardItem`, `BoardNote`, `BoardConnection`
- `api.types.ts`: Shared API shapes (Pagination, Errors, Tokens)

### `config/`

Global configuration files.

- `constants.ts`: API Base URLs, pagination limits, threshold values.
- `permissions.ts`: Frontend constants mirroring backend `core.permissions_constants` to ensure typo-free RBAC checks.

### `services/api/`

The data-fetching layer.

- `axios.instance.ts`: Configured Axios client with request interceptors (for JWT injection) and response interceptors (for 401 refresh token flows and global error handling).
- Domain-specific API wrappers (`auth.api.ts`, `cases.api.ts`, `evidence.api.ts`, etc.) that encapsulate all backend endpoints.

### `context/` & `hooks/`

Global state management and reusable React hooks.

- `AuthContext.tsx`: Manages JWT tokens, current user profile, and user permissions.
- `useAuth.ts`: Hook to access authentication state and login/logout methods.
- `usePermissions.ts`: Hook to evaluate if the current user has specific RBAC permissions (`hasPermission`, `hasAnyPermission`).

### `utils/`

Pure, stateless helper functions.

- `formatters.ts`: Date formatting, currency formatting (Rials), status label formatting.
- `validators.ts`: Form validation logic (email, national ID, vehicle XOR constraints).

### `components/`

Dumb, reusable, global UI components.

- **`ui/`**: Atomic design elements (`Button`, `Input`, `Modal`, `Table`, `Badge`, `Skeleton`, `Card`). These components have no business logic.
- **`layout/`**: Structural components (`Sidebar`, `Topbar`, `AuthLayout`, `DashboardLayout`, `ProtectedRoute`).

### `features/`

Smart components grouped by business domain. These components are aware of the application state and API layer.

- **`auth/`**: `LoginForm`, `RegisterForm`
- **`cases/`**: `CaseForm`, `CaseTable`, `CaseTimeline`, `CaseReviewActions`
- **`board/`**: `BoardCanvas`, `BoardItem`, `BoardConnection`
- **`evidence/`**: `EvidenceForm`, `EvidenceCard`, `CoronerVerificationForm`
- **`suspects/`**: `SuspectList`, `InterrogationForm`, `TrialForm`, `MostWantedCard`
- **`dashboard/`**: `DashboardModule`, `StatsCards`
- **`reports/`**: `CaseReport`
- **`admin/`**: `RoleManager`, `UserManager`

### `pages/`

Route-level components that compose features and layouts together.

- Examples: `HomePage`, `LoginPage`, `OverviewPage`, `CasesListPage`, `KanbanBoardPage`, `EvidenceVaultPage`, `MostWantedPage`.

### `routes/`

React Router configuration.

- `AppRouter.tsx`: Defines the routing tree, applying `AuthLayout` for public routes and `DashboardLayout` (wrapped in `ProtectedRoute`) for authenticated routes.

---

## 4. Core Infrastructure Highlights

### 4.1. Routing Strategy

The application uses a nested routing strategy:

1. **Public Routes:** `/`, `/most-wanted`
2. **Auth Routes:** `/login`, `/register` (Wrapped in `AuthLayout`)
3. **Protected Routes:** `/dashboard`, `/cases/*`, `/evidence/*`, `/suspects/*`, `/board/*` (Wrapped in `ProtectedRoute` and `DashboardLayout`)

### 4.2. RBAC Integration

The frontend enforces RBAC at two levels:

1. **Route Level:** `ProtectedRoute` can restrict access to entire pages based on required permissions (e.g., `/admin` requires System Admin permissions).
2. **Component Level:** The `usePermissions` hook is used inside components to conditionally render UI elements (e.g., hiding the "Verify Evidence" button if the user lacks `CAN_VERIFY_EVIDENCE`).

### 4.3. The Detective Board

The Detective Board (`features/board/`) is scaffolded to support a complex, interactive UI. It separates the canvas (`BoardCanvas`), draggable items (`BoardItem`), and SVG connections (`BoardConnection`) to prepare for drag-and-drop implementation (e.g., using `dnd-kit` or `react-dnd`) and HTML5 Canvas/SVG rendering.

---

## 5. Next Steps

With the architectural scaffolding complete, the project is ready for the implementation phase:

1. **UI Implementation:** Build out the atomic components in `components/ui/` using CSS/Tailwind/Styled-Components.
2. **API Integration:** Implement the Axios calls in `services/api/` and connect them to the backend.
3. **State & Auth:** Finalize the JWT lifecycle in `AuthContext`.
4. **Feature Development:** Build the smart components in `features/` and wire them into the `pages/`.

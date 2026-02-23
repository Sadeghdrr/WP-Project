# Frontend Phase 4 — Core Pages Implementation Report

## Overview

Phase 4 implements all core pages and feature components defined in **Chapter 5** of `project-doc.md`. Each page group follows RBAC (permission-gated actions), uses the Phase 1 design system, supports loading/error states via `@tanstack/react-query`, and passes `tsc -b` with zero errors.

**Build status:** ✅ Clean (`npx tsc -b` — 0 errors)

---

## Implemented File Inventory

### 1. Home Page
| File | Description |
|------|-------------|
| `src/pages/home/HomePage.tsx` | Public landing page with hero section, department stats via `StatsCards`, and feature cards grid |
| `src/features/dashboard/StatsCards.tsx` | Grid of 6 `ModuleCard` instances showing solved cases, active cases, employees, suspects, evidence, voided cases |

### 2. Most Wanted
| File | Description |
|------|-------------|
| `src/pages/suspects/MostWantedPage.tsx` | Public page listing top 10 most-wanted suspects fetched from `suspectsApi.mostWanted()` |
| `src/features/suspects/MostWantedCard.tsx` | Ranked card displaying suspect photo, name, score, reward, and days wanted |

### 3. Case & Complaint Status (Cases)
| File | Description |
|------|-------------|
| `src/pages/cases/CasesListPage.tsx` | Paginated list with status/crime-level/type filters, permission-gated "New Case" button |
| `src/pages/cases/CaseCreatePage.tsx` | Create new case (complaint or crime-scene) via `CaseForm` |
| `src/pages/cases/CaseDetailsPage.tsx` | Full case detail: info grid, calculations, timeline, review actions, complainant manager |
| `src/features/cases/CaseTable.tsx` | Sortable Table of `CaseListItem` with crime-level labels and status badges |
| `src/features/cases/CaseTimeline.tsx` | Vertical timeline of case status transitions |
| `src/features/cases/CaseForm.tsx` | Multi-field form for case creation (title, description, crime level, location, type, incident date) |
| `src/features/cases/CaseReviewActions.tsx` | Status-aware review buttons (approve/reject/escalate/void) with permission gating via `usePermissions` |
| `src/features/cases/ComplainantManager.tsx` | Add/remove complainants on a case with inline form |

### 4. Evidence Registration & Review
| File | Description |
|------|-------------|
| `src/pages/evidence/EvidenceVaultPage.tsx` | Paginated evidence list filtered by type, permission-gated "Register Evidence" button |
| `src/pages/evidence/EvidenceCreatePage.tsx` | Create any evidence type via polymorphic `EvidenceForm` |
| `src/pages/evidence/EvidenceDetailPage.tsx` | Full evidence detail with `EvidenceCard` and optional `CoronerVerificationForm` for biological evidence |
| `src/features/evidence/EvidenceTable.tsx` | Sortable Table of `EvidenceListItem` with type and verification badges |
| `src/features/evidence/EvidenceForm.tsx` | Polymorphic form that adapts fields by evidence type (testimony, biological, vehicle, identity, other) |
| `src/features/evidence/EvidenceCard.tsx` | Full evidence detail card with type-specific sections, files list, and custody log |
| `src/features/evidence/CoronerVerificationForm.tsx` | Coroner verification form for biological evidence (forensic result + submit) |

### 5. General Reporting
| File | Description |
|------|-------------|
| `src/pages/reports/ReportsPage.tsx` | List cases, click to view full report for any case |
| `src/features/reports/CaseReport.tsx` | Full case report: info, personnel, complainants, witnesses, evidence, suspects, status history, calculations |

### 6. Admin Panel
| File | Description |
|------|-------------|
| `src/pages/admin/AdminPanelPage.tsx` | Tabbed admin panel with Roles and Users tabs |
| `src/features/admin/RoleManager.tsx` | List/create/edit/delete roles, assign permissions via checkboxes |
| `src/features/admin/UserManager.tsx` | List users with pagination, assign roles via modal, activate/deactivate users |

### 7. Dashboard
| File | Description |
|------|-------------|
| `src/pages/dashboard/OverviewPage.tsx` | Authenticated dashboard with `StatsCards` and permission-gated `DashboardModule` cards |
| `src/features/dashboard/DashboardModule.tsx` | Permission-gated `ModuleCard` wrapper — only renders if user has the required permission |

### 8. Suspects
| File | Description |
|------|-------------|
| `src/pages/suspects/SuspectsListPage.tsx` | Paginated suspect list filtered by status, linking to detail pages |
| `src/pages/suspects/SuspectDetailPage.tsx` | Full suspect detail: info, interrogations, trials, bail payments, permission-gated action forms |
| `src/pages/suspects/BountyTipPage.tsx` | Public bounty tip submission form + reward lookup |
| `src/features/suspects/SuspectList.tsx` | Sortable Table of `SuspectListItem` with status badges |
| `src/features/suspects/InterrogationForm.tsx` | Record interrogation: technique, score, duration, notes |
| `src/features/suspects/TrialForm.tsx` | Record trial verdict: verdict, sentence, trial date |
| `src/features/suspects/BountyTipForm.tsx` | Submit anonymous tip about a suspect |
| `src/features/suspects/BailPaymentForm.tsx` | Record bail payment for a suspect |

### 9. CSS
| File | Description |
|------|-------------|
| `src/App.css` | Extended with ~300 lines of page-specific styles for all Phase 4 pages |

---

## Total: 35 files (20 features + 14 pages + 1 CSS update)

---

## Architecture Decisions

### RBAC Integration
- **PermissionGate** wraps action buttons (e.g., "New Case", "Register Evidence") using `permissions={[...]}` array prop
- **DashboardModule** internally checks `usePermissions().hasPermission()` before rendering
- **CaseReviewActions** checks multiple permissions to conditionally render approve/reject/escalate/void buttons
- Permission constants imported from `@/config/permissions`

### State Management
- All data fetching via `@tanstack/react-query` (`useQuery`, `useMutation`)
- `useQueryClient().invalidateQueries()` for cache invalidation after mutations
- Local UI state (filters, pagination, modals) via `useState`
- Toast notifications via `useToast()` context

### Loading & Error States
- `Skeleton` component used as loading placeholder
- `Alert type="error"` used for error messages
- `CaseTable` and `StatsCards` accept a `loading: boolean` prop
- Mutations show loading state via `isPending` on buttons

### Polymorphic Evidence
- `EvidenceForm` renders different fields per `evidence_type` (testimony → statement text, biological → forensic result, vehicle → model/color/plate/serial, identity → owner name)
- `EvidenceCard` displays type-specific sections conditionally

### Design System Usage
- All pages use `Card`, `Badge`, `Button`, `Table`, `Pagination`, `Modal`, `Select`, `Input`, `Textarea`, `Alert`, `Skeleton`, `Tabs`, `ModuleCard`
- Badge variants: `success`, `warning`, `danger`, `info`, `neutral`, `primary`
- Table: `rowKey={(row) => row.id}`, `width` as string (e.g., `'60px'`)

---

## Type Safety Notes
- `CaseListItem` does not include `created_at` — used `incident_date` column instead
- `ModuleCard` uses `subtitle` (not `description`) and has no `href` prop — navigation handled via `onClick`
- Badge does not support `"secondary"` or `"default"` variants — `"neutral"` is used instead
- `PermissionGate` expects `permissions: string[]` (plural array), not `permission: string`
- BountyTipPage reward typed as `Record<string, unknown> | null` to avoid `unknown`-as-ReactNode issues

---

## Verification

```
$ npx tsc -b
(no output — 0 errors)
```

All 35 files compile cleanly with TypeScript 5.9 strict mode, `erasableSyntaxOnly`, and `verbatimModuleSyntax`.

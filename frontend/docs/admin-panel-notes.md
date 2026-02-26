# Admin Panel — Frontend Implementation Notes

## Overview

The Admin Panel provides System Administrators with a custom (non-Django) frontend
interface for managing users, roles, and permissions. It mirrors the functionality
of Django's built-in admin but is implemented entirely within the React frontend.

**Access:** Restricted to authenticated users with `hierarchy_level >= 100` (System Admin).

---

## Admin Sections

### 1. Admin Overview (`/admin`)
- Quick statistics: total users, active/inactive users, total roles
- Navigation cards linking to User Management and Role Management

### 2. User Management (`/admin/users`)
- **List:** Tabular view of all users with columns: username, name, email, role, status
- **Search:** Debounced text search across name/email/username
- **Filters:** By role (select), by active status (active/inactive/all)
- **Detail panel:** Slide-in panel showing full user profile
- **Actions:**
  - Activate / Deactivate user (`PATCH /api/accounts/users/:id/activate/` and `/deactivate/`)
  - Assign role to user (`PATCH /api/accounts/users/:id/assign-role/`)

### 3. Role Management (`/admin/roles`)
- **List:** Card grid showing all roles with hierarchy level badges
- **Create:** Modal form with name, description, hierarchy level (`POST /api/accounts/roles/`)
- **Edit:** Modal form pre-filled with role data (`PUT /api/accounts/roles/:id/`)
- **Delete:** Confirmation dialog (`DELETE /api/accounts/roles/:id/`)
- **Permission assignment:** Dedicated modal showing all Django permissions grouped by app,
  with select/deselect all and search/filter (`POST /api/accounts/roles/:id/assign-permissions/`)

---

## Endpoints Used

| Action | Method | Endpoint |
|--------|--------|----------|
| List users | `GET` | `/api/accounts/users/?search=&role=&is_active=` |
| User detail | `GET` | `/api/accounts/users/:id/` |
| Assign role | `PATCH` | `/api/accounts/users/:id/assign-role/` |
| Activate user | `PATCH` | `/api/accounts/users/:id/activate/` |
| Deactivate user | `PATCH` | `/api/accounts/users/:id/deactivate/` |
| List roles | `GET` | `/api/accounts/roles/` |
| Role detail | `GET` | `/api/accounts/roles/:id/` |
| Create role | `POST` | `/api/accounts/roles/` |
| Update role | `PUT` | `/api/accounts/roles/:id/` |
| Delete role | `DELETE` | `/api/accounts/roles/:id/` |
| Assign permissions | `POST` | `/api/accounts/roles/:id/assign-permissions/` |
| List permissions | `GET` | `/api/accounts/permissions/` |

---

## Supported vs Deferred Actions

### Supported (Implemented)
- User list with search/filter
- User detail view
- User activate/deactivate
- User role assignment
- Role CRUD (create, read, update, delete)
- Permission listing (grouped by app)
- Permission assignment to roles (full replacement)

### Deferred (Not Implemented)
- User creation from admin panel (users register themselves per project flow)
- User deletion (not exposed by backend — users are deactivated instead)
- Bulk operations (batch activate/deactivate)
- Audit logging UI
- Permission-level assignment directly to users (only via roles)

---

## Access Control Handling

- **Frontend guard:** Each admin page checks `hierarchyLevel >= 100` (System Admin). Non-admins see an "Access Denied" message.
- **Sidebar visibility:** The "Admin Panel" link in the sidebar is only shown when the user holds at least one relevant permission (`accounts.view_user`, `accounts.view_role`, etc.) via `canAny()`.
- **Backend enforcement:** All admin endpoints require `IsAuthenticated` + System Admin check on the server side. Even if the frontend guard is bypassed, the API will return 403.
- **No Route Guard (by design):** The React Router tree uses `<ProtectedRoute>` for auth but does not enforce hierarchy at the route level — this is handled within each page component and enforced server-side.

---

## Architecture Notes

- **API layer:** `src/api/admin.ts` — pure fetch functions, no React dependency
- **React Query hooks:** `src/hooks/useAdmin.ts` — query/mutation hooks with cache invalidation
- **Types:** `src/types/admin.ts` — TypeScript interfaces for admin DTOs
- **Styling:** CSS Modules per page (`AdminPage.module.css`, etc.)
- **No external UI library:** Custom components consistent with the rest of the project

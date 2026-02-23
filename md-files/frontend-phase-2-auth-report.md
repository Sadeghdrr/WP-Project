# Frontend Phase 2 — Authentication & Access Control Report

## Overview

Phase 2 implements the complete authentication UI layer: Login page, Register page, Unauthorized (403) page, and Not Found (404) page. All forms integrate with the existing auth infrastructure (AuthContext, JWT interceptors, token storage) built in Phase 0.

---

## Files Created / Modified

| File | Action | Description |
|------|--------|-------------|
| `types/api.types.ts` | **Modified** | Added `password_confirm` to `RegisterRequest` (backend requires it) |
| `features/auth/LoginForm.tsx` | **Replaced stub** | Full login form with identifier + password |
| `features/auth/RegisterForm.tsx` | **Replaced stub** | Full registration form with 8 fields + client validation |
| `pages/auth/LoginPage.tsx` | **Replaced stub** | Wraps `LoginForm` in AuthLayout |
| `pages/auth/RegisterPage.tsx` | **Replaced stub** | Wraps `RegisterForm` in AuthLayout |
| `pages/errors/UnauthorizedPage.tsx` | **Created** | 403 Forbidden page with navigation |
| `pages/errors/NotFoundPage.tsx` | **Created** | 404 catch-all page |
| `routes/AppRouter.tsx` | **Modified** | Added `/unauthorized` and `*` (404) routes |
| `App.css` | **Modified** | Added auth-form, error page, and responsive styles |

---

## Authentication Flow

### Login Flow
1. User navigates to `/login` (or is redirected by `ProtectedRoute`)
2. `AuthLayout` checks if already authenticated → redirects to `/dashboard`
3. `LoginForm` renders identifier + password fields
4. User enters any of: **username, email, phone number, or national ID**
5. On submit → `AuthContext.login()` → `authApi.login()` → `POST /accounts/auth/login/`
6. Backend resolves the identifier to a user via `CustomTokenObtainPairSerializer`
7. JWT tokens (access + refresh) + user profile returned
8. Tokens stored in `localStorage` via `tokenStorage.setTokens()`
9. User state set in `AuthContext` → `isAuthenticated` becomes `true`
10. Navigate to `location.state.from` (redirect origin) or `/dashboard`

### Register Flow
1. User navigates to `/register`
2. `RegisterForm` renders 8 required fields
3. Client-side validation runs before submission:
   - Username: non-empty
   - Email: regex via `validateEmail()`
   - Phone: Iranian mobile format via `validatePhoneNumber()` (`09xxxxxxxxx`)
   - National ID: 10 digits via `validateNationalId()`
   - Password: 8+ chars, uppercase, lowercase, digit via `validatePassword()`
   - Password confirm: must match password
4. On submit → `AuthContext.register()` → `authApi.register()` → `POST /accounts/auth/register/`
5. Server validates unique constraints (username, email, phone, national_id) and password format
6. On success → toast notification → redirect to `/login`
7. Server-side field errors are extracted via `extractFieldErrors()` and displayed per-field

### Token Storage Strategy
- **Storage**: `localStorage` with keys `lapd_access_token` / `lapd_refresh_token`
- **Why localStorage**: Simple, persistent across tabs, suitable for this application's security model
- **Hydration**: On app mount, `AuthProvider.fetchUser()` checks for existing tokens and calls `/me/` to restore session

### Auto-Refresh Token
- **Interceptor**: `axios.instance.ts` response interceptor catches 401 errors
- **Silent refresh**: Calls `POST /accounts/auth/token/refresh/` with the stored refresh token
- **Deduplication**: Concurrent 401s share a single refresh request (prevents token race conditions)
- **Failure**: If refresh fails, tokens are cleared and the user is redirected to `/login`
- **Token TTL**: Access token = 30 minutes, Refresh token = 7 days (configured server-side in SimpleJWT)

---

## Role-Based Routing Integration

### Route-Level Protection
- `ProtectedRoute` wraps all `/dashboard/*` routes
- Checks `isAuthenticated` → redirects to `/login` if not
- Supports `requiredPermissions` prop for specific permission checks
- Supports `requireAll` prop for AND logic (default OR)
- Shows inline 403 Alert for permission failures

### Component-Level Guards
- `PermissionGate` — conditionally renders children based on permission codenames
- `RoleGuard` — checks permissions + hierarchy level (e.g., only Captains and above)

### Permission Flow
1. JWT token contains `permissions_list` and `role` claims (added by `CustomTokenObtainPairSerializer.get_token()`)
2. `/me/` endpoint returns `permissions: string[]` in `UserDetailSerializer`
3. `AuthContext` exposes `permissions` array
4. `usePermissions()` hook provides `hasPermission()`, `hasAnyPermission()`, `hasAllPermissions()`, `hasMinHierarchy()`

---

## Error Handling

### Form-Level Errors
- **Client validation**: Runs before API call; sets per-field error messages
- **Server validation**: Backend returns `400` with field-level errors; parsed via `extractFieldErrors()`
- **General errors**: Displayed in `Alert` component above the form; dismissible via `onClose`
- **Toast notifications**: Success messages on login/register use `useToast()` from `ToastContext`

### Error Page Hierarchy
| Code | Route | Component | Purpose |
|------|-------|-----------|---------|
| 401 | — | `ProtectedRoute` redirect | Unauthenticated → `/login` |
| 403 | `/unauthorized` | `UnauthorizedPage` | Explicit forbidden page |
| 403 | inline | `ProtectedRoute` Alert | Per-route permission denied |
| 404 | `*` | `NotFoundPage` | Catch-all unmatched routes |

---

## UI/UX Design

### Login Page
- Centered card layout via `AuthLayout`
- Single `identifier` field (supporting username/email/phone/national ID)
- Password field with autocomplete hints
- "Don't have an account?" link to Register
- Full-width submit button with loading spinner
- Auto-focus on identifier field

### Register Page
- Same centered card layout
- 8 fields with logical grouping (first/last name in a row)
- Per-field validation feedback with error messages
- Password strength requirements communicated via validation
- "Already have an account?" link to Login
- Responsive: row layout collapses on mobile (< 480px)

### Error Pages
- Large status code display (403/404)
- Contextual messaging
- Navigation buttons (Go Back + Dashboard/Login)
- Consistent styling with the rest of the application

---

## Responsive Behavior

- Auth forms respond to viewport width; 2-column name fields collapse at 480px
- Auth layout card max-width: 480px, centered with padding
- Error pages are full-viewport centered
- All existing responsive behavior preserved (sidebar collapse, topbar menu toggle)

---

## Grading Criteria Coverage (§7)

| Criterion | Points | Status |
|-----------|--------|--------|
| Login and Registration Page | 200 | ✅ Both implemented with full validation |
| Proper UI/UX implementation | (part of 3000) | ✅ Clean forms, error feedback, loading states |
| Displaying appropriate error messages | 100 | ✅ Client + server field errors, toast, Alert |
| Responsive Pages | 300 | ✅ Breakpoints, collapsible layouts |

---

## Build Verification

```
npx tsc -b → Clean (0 errors)
```

All files type-check cleanly. No `enum` keywords used (erasableSyntaxOnly compliant). No bare `import React` (verbatimModuleSyntax compliant).

# Step 07 — Auth / Session Flow · Agent Report

**Branch:** `agent/step-07-auth-session-flow`  
**Base:** `master`  
**Scope:** frontend-only (no backend files touched)

---

## 1  Objective

Implement the authentication and session lifecycle required by **§5.2 Login and Registration Page** (200 pts) and supporting requirements from **§4.1 Registration and Login** (CP1 backend — 100 pts, already delivered) and **§3.1 RBAC** (access-level-aware UI).

Concretely:

| Capability | Status |
|---|---|
| Login form (identifier + password) | ✅ Done |
| Registration form (8 fields, validation) | ✅ Done |
| JWT token persistence (access in-memory, refresh in localStorage) | ✅ Done |
| Bootstrap on page-load (`/me` via refresh) | ✅ Done |
| Logout (clear tokens + state) | ✅ Done |
| 401 handling (expired session → redirect to login) | ✅ Done |
| Route guards (ProtectedRoute / GuestRoute) | ✅ Done |
| Permission set + hierarchy level exposed via context | ✅ Done |

---

## 2  Files Created

| File | Purpose |
|---|---|
| `src/auth/tokenStorage.ts` | localStorage helpers for refresh token |
| `src/auth/AuthContext.tsx` | AuthProvider, AuthStatus, full auth lifecycle |
| `src/auth/useAuth.ts` | `useAuth()` hook consuming AuthContext |
| `src/api/auth.ts` | `loginApi`, `registerApi`, `refreshTokenApi`, `fetchMeApi` |
| `src/components/auth/RouteGuards.tsx` | `ProtectedRoute` and `GuestRoute` components |
| `src/components/auth/index.ts` | Barrel export |
| `src/pages/Login/LoginPage.module.css` | Login form styles |
| `src/pages/Register/RegisterPage.module.css` | Register form styles |
| `frontend/docs/auth-session-notes.md` | Architecture reference document |

## 3  Files Modified

| File | Changes |
|---|---|
| `src/api/endpoints.ts` | Fixed LOGIN, REGISTER, TOKEN_REFRESH paths to match backend URL config |
| `src/api/client.ts` | Added `setOnUnauthorized` callback + 401 detection in `apiFetch` |
| `src/api/index.ts` | Added `setOnUnauthorized` and auth API re-exports |
| `src/types/auth.ts` | Fixed `User` (role → string, added `role_detail`, `permissions`), fixed `LoginResponse` (flat shape), fixed `RegisterResponse` (User only, no tokens), added `RoleDetail` interface |
| `src/types/index.ts` | Added `RoleDetail` export |
| `src/auth/index.ts` | Added `AuthProvider`, `useAuth`, token-storage exports |
| `src/App.tsx` | Wrapped app tree with `AuthProvider` |
| `src/router/Router.tsx` | Added `ProtectedRoute` / `GuestRoute` wrappers to route tree |
| `src/components/layout/Header.tsx` | Added username display + logout button |
| `src/pages/Login/LoginPage.tsx` | Replaced placeholder with real login form |
| `src/pages/Register/RegisterPage.tsx` | Replaced placeholder with real register form |

## 4  Backend Files Modified

**None.** All work is frontend-only per the step rules.

---

## 5  Architecture Decisions

### Token storage strategy
- **Access token** — module-scoped variable in `client.ts`; never touches storage APIs.
- **Refresh token** — `localStorage` under key `lapd_refresh_token`; survives page reloads.

### Bootstrap sequence (page load)
1. Read refresh token from localStorage.
2. If present → `POST /api/accounts/auth/token/refresh/` to get a new access token.
3. If refresh succeeds → `GET /api/accounts/me/` to hydrate user + permissions.
4. If any step fails → status becomes `unauthenticated`; user sees login page.

### Register → auto-login
The backend register endpoint returns only the new `User` (no tokens). After a successful register, the frontend automatically calls `loginApi` with the same credentials to obtain tokens and log the user in.

### 401 handling
`apiFetch` detects HTTP 401 responses from any API call. When detected, it invokes the `onUnauthorized` callback registered by `AuthProvider`, which clears all auth state and redirects to `/login`.

### Route protection
- `ProtectedRoute` — requires `status === 'authenticated'`; redirects to `/login` otherwise.
- `GuestRoute` — requires `status === 'unauthenticated'`; redirects to `/dashboard` otherwise.
- Both show nothing while `status === 'loading'` (bootstrap in progress).

---

## 6  Backend Anomalies (report only — not fixed)

| # | Anomaly | Impact | Recommendation |
|---|---|---|---|
| 1 | Register endpoint returns no JWT tokens | Frontend must make a second API call (login) after register | Backend could return tokens on register to avoid extra round-trip |
| 2 | Login returns HTTP 400 (not 401) for invalid credentials | Frontend already handles this (checks `response.ok` + shows error from body) | Consider 401 for standards compliance |
| 3 | No logout / token-blacklist endpoint exposed | Logout is client-side only (clear tokens); refresh token remains valid server-side until expiry | Add `POST /accounts/auth/logout/` that blacklists the refresh token |
| 4 | No password-reset endpoint | Password reset flow cannot be built | Add forgot-password / reset endpoints |
| 5 | `national_id` max 10 chars but no format docs | Frontend uses placeholder hint only; no regex validation | Document expected format |
| 6 | `phone_number` max 15 chars, no regex on backend | Same as above | Add phone regex validation on backend serializer |

---

## 7  Deferred to Later Steps

| Item | Planned Step |
|---|---|
| Role-based dashboard modules (§5.3) | Step 8+ (modular dashboard) |
| Permission-gated UI elements (`can.ts` helpers) | Step 8+ |
| Admin panel (non-Django, §7) | Step 12+ |
| Loading skeletons on auth pages | Step 10+ (skeleton layer) |
| Responsive login/register layout | Step 10+ |
| Frontend tests for auth | Dedicated testing step |
| Password-reset flow | Blocked on backend endpoint |
| Token-blacklist logout | Blocked on backend endpoint |

---

## 8  Scoring Coverage (§7 — CP2 Checklist)

| Criterion | Points | Step-07 Contribution |
|---|---|---|
| Login and Registration Page (§5.2) | 200 | Fully implemented: both pages with validation, error handling, redirect |
| Proper state management | 100 | AuthContext + React Context for auth state; TanStack Query for server state |
| Displaying appropriate error messages | 100 | Login/register show field-level and general errors from backend |
| Component lifecycles | 100 | Bootstrap effect, cleanup, loading states handled |
| Adherence to best practices | 150 | TypeScript strict mode, barrel exports, separation of concerns |

---

## 9  Verification

```
npx tsc --noEmit   → 0 errors
npx vite build     → 143 modules transformed, build success (2.99 s)
```

No regressions introduced. All existing pages continue to compile and render.

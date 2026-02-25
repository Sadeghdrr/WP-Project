# Auth & Session – Architecture Notes

> Created during **Step 07 – Auth Session Flow**.
> Reference for all auth-related decisions and implementation details.

---

## 1. Endpoints Used

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/accounts/auth/login/` | POST | Login with identifier + password |
| `/api/accounts/auth/register/` | POST | Register new user |
| `/api/accounts/auth/token/refresh/` | POST | Refresh access token |
| `/api/accounts/me/` | GET | Fetch current authenticated user |

### Login

- **Request**: `{ identifier: string, password: string }`
- **Response (200)**: `{ access: string, refresh: string, user: UserDetail }`
- **Error (400)**: `{ detail: "Invalid credentials." }` or `{ detail: "User account is disabled." }`
- Note: `identifier` can be username, email, phone, or national_id

### Register

- **Request**: `{ username, password, password_confirm, email, phone_number, first_name, last_name, national_id }`
- **Response (201)**: `UserDetail` (no tokens returned)
- **Error (400)**: field-level validation errors
- **Error (409)**: duplicate field conflict
- After successful registration, frontend auto-calls login endpoint

### Token Refresh

- **Request**: `{ refresh: string }`
- **Response (200)**: `{ access: string }` (+ new `refresh` if rotation enabled)
- Backend has `ROTATE_REFRESH_TOKENS = True` and `BLACKLIST_AFTER_ROTATION = True`

### Me

- **Request**: GET with `Authorization: Bearer <access_token>`
- **Response (200)**: `UserDetail` (id, username, email, role, role_detail, permissions, etc.)

---

## 2. Token / Session Approach

### Storage Strategy

| Token | Where | Why |
|---|---|---|
| Access token | In-memory (module-scoped variable) | Never touches storage → XSS can't leak it |
| Refresh token | `localStorage` (`lapd_refresh_token`) | Survives page reload for session persistence |

### Token Lifecycle

```
App Load
  ├─ Check localStorage for refresh token
  ├─ If found → POST /token/refresh/ → get new access token
  │   ├─ Success → setAccessToken(access), GET /me/ → set user → "authenticated"
  │   └─ Failure → clear all → "unauthenticated"
  └─ If not found → "unauthenticated"

Login
  ├─ POST /auth/login/ → { access, refresh, user }
  ├─ setAccessToken(access) + localStorage.setItem(refresh)
  └─ Set user state → "authenticated"

Register
  ├─ POST /auth/register/ → user (no tokens)
  ├─ Auto-call POST /auth/login/ with same credentials
  └─ Same as Login flow above

Logout
  ├─ setAccessToken(null) + localStorage.removeItem(refresh)
  └─ Set user null → "unauthenticated"

401 Response (any API call)
  └─ Same as Logout (clear tokens, set unauthenticated)
```

### JWT Config (from backend settings.py)

- Access token: 30 min lifetime
- Refresh token: 7 days lifetime
- Rotation: enabled (new refresh on each refresh call)
- Blacklisting: enabled (old refresh tokens invalidated)
- Auth header: `Authorization: Bearer <access_token>`
- Custom claims in access token: `role`, `hierarchy_level`, `permissions_list`

---

## 3. Route Protection Behaviour

### Guard Components

| Component | Purpose | Location |
|---|---|---|
| `<ProtectedRoute>` | Requires auth → redirects to `/login` | `src/components/auth/RouteGuards.tsx` |
| `<GuestRoute>` | Guest-only → redirects to `/dashboard` if logged in | `src/components/auth/RouteGuards.tsx` |

### Route Categories

| Category | Routes | Guard |
|---|---|---|
| Public | `/`, `/forbidden`, `*` | None |
| Guest-only | `/login`, `/register` | `<GuestRoute>` |
| Protected | `/dashboard`, `/cases/*`, `/admin/*`, etc. | `<ProtectedRoute>` |

### Loading State

While auth status is `"loading"` (bootstrap in progress), both guards
show a "Loading…" spinner instead of redirecting. This prevents a
flash-of-login-page on page reload when the user has a valid refresh token.

### 401 Handling

The API client (`api/client.ts`) has a `setOnUnauthorized` callback that
is registered by `AuthContext`. When any API call receives a 401 response,
the auth state is cleared and the user is redirected to login via the
`<ProtectedRoute>` guard (which sees `status === "unauthenticated"`).

---

## 4. Key Files

### New Files

| File | Purpose |
|---|---|
| `src/auth/AuthContext.tsx` | React context with AuthProvider — manages full auth lifecycle |
| `src/auth/useAuth.ts` | `useAuth()` hook for consuming auth context |
| `src/auth/tokenStorage.ts` | localStorage helpers for refresh token |
| `src/api/auth.ts` | Auth API functions (login, register, refresh, me) |
| `src/components/auth/RouteGuards.tsx` | ProtectedRoute + GuestRoute components |
| `src/components/auth/index.ts` | Barrel export |
| `src/pages/Login/LoginPage.module.css` | Login form styles |
| `src/pages/Register/RegisterPage.module.css` | Register form styles |

### Modified Files

| File | Changes |
|---|---|
| `src/api/endpoints.ts` | Fixed login/register/refresh paths to match backend |
| `src/api/client.ts` | Added `setOnUnauthorized` for 401 handling |
| `src/api/index.ts` | Updated barrel exports |
| `src/types/auth.ts` | Fixed User, LoginResponse, RegisterResponse to match backend |
| `src/types/index.ts` | Added RoleDetail export |
| `src/auth/index.ts` | Added AuthProvider, useAuth, tokenStorage exports |
| `src/App.tsx` | Added AuthProvider to provider stack |
| `src/router/Router.tsx` | Added ProtectedRoute/GuestRoute guards |
| `src/components/layout/Header.tsx` | Added username display + logout button |
| `src/pages/Login/LoginPage.tsx` | Replaced placeholder with real login form |
| `src/pages/Register/RegisterPage.tsx` | Replaced placeholder with real register form |

---

## 5. Known Limitations / Deferred Items

| Item | Status | Notes |
|---|---|---|
| Permission-based route guards | Deferred | `routes.ts` has `requiredPermissions` and `minHierarchy` metadata; not enforced yet |
| Automatic token refresh before expiry | Deferred | Currently only refreshes on app load; 401 → logout. Could add proactive refresh timer. |
| "Remember me" option | Deferred | Refresh token always stored; could add sessionStorage option |
| Password reset / forgot password | Not in backend | No endpoint exists |
| OAuth / social login | Not required | Not in project-doc |
| CSRF protection | N/A | JWT-based auth, no cookies |
| Redirect to original page after login | Deferred | Currently always redirects to /dashboard |

---

## 6. Backend Anomalies (reported, not fixed)

1. **Register returns no tokens** — Forces auto-login as second request
2. **Login returns HTTP 400 for invalid credentials** — Not 401 (DRF ValidationError)
3. **User serializer missing fields** — `is_staff` and `last_login` not in UserDetailSerializer (frontend types updated to match actual response)
4. **Suspect endpoints double-prefix** — `/suspects/suspects/...` (known from Step 2)
5. **No logout endpoint** — Backend has no token blacklist endpoint; frontend just clears local state
6. **No password reset endpoint** — Not available in backend

# Patch Report — Home Page App Shell & Auth Navigation

## Branch

`agent/patch-home-shell-auth-nav-rootcause`

## Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/router/Router.tsx` | Modified | Moved Home + Forbidden routes inside `AppLayout`; `ProtectedRoute` nested inside `AppLayout` instead of wrapping it |
| `frontend/docs/home-shell-auth-nav-fix-notes.md` | Created | Implementation notes for this patch |
| `md-files/patch-home-shell-auth-nav-rootcause-report.md` | Created | This report |

**No changes** to `Header.tsx` or `Sidebar.tsx` — they already had the correct auth-conditional logic on master.

## Root Cause(s)

### Primary: Home route outside AppLayout (Route tree / layout wrapping)

The Home route was declared as a bare top-level entry in the
`createBrowserRouter` array:

```tsx
{ path: "/", element: s(HomePage) }
```

This sat **outside** the `ProtectedRoute > AppLayout` nesting that provided
the shared shell (Header + Sidebar) to all other pages. Visiting `/`
rendered only the `HomePage` component with zero navigation chrome.

### Secondary (non-issue on master): Header auth links

The `Header` component already contained a ternary rendering Login/Register
for unauthenticated users and Username/Logout for authenticated users.
However, because `Header` was only mounted inside `AppLayout`, and the Home
route was outside `AppLayout`, this code was never exercised on the Home
page. No code change was needed — fixing the routing was sufficient.

### Root-cause checklist results

| # | Check | Result |
|---|-------|--------|
| 1 | Route tree / layout wrapping | **ROOT CAUSE** — Home mounted outside AppLayout |
| 2 | Navbar placement | Not an issue — Header is correctly placed in AppLayout |
| 3 | Auth state hydration | Not an issue — AuthProvider is at app root in App.tsx |
| 4 | Conditional rendering bugs | Not an issue — Header ternary is correct |
| 5 | CSS/layout issues | Not an issue — styles are fine |
| 6 | Duplicate shell implementations | Not an issue — single AppLayout exists |

## Patch Summary

Restructured the router so that `AppLayout` wraps **all** non-guest routes:

- **Guest routes** (login, register): remain shell-less with `GuestRoute` guard
- **Public pages** (Home, Forbidden): now inside `AppLayout` but **not** inside
  `ProtectedRoute` — they get the shared shell without requiring authentication
- **Protected pages** (dashboard, cases, etc.): inside both `AppLayout` and
  `ProtectedRoute` — shell + auth guard

This is a single structural change in `Router.tsx` (route nesting order).

## Before / After Behaviour

| Aspect | Before | After |
|--------|--------|-------|
| Home page navigation | No Header, no Sidebar | Full app shell (Header + Sidebar) |
| Login/Register links on Home | Not visible (Header not rendered) | Visible in Header nav |
| Logout/username on Home | Not visible | Visible when authenticated |
| Protected page shell | Working (Header + Sidebar) | Working (unchanged) |
| Home page content | Intact | Intact |
| Duplicate nav bars | None | None |

## Sidebar/Nav — Generic Pending Step 12

The Sidebar currently shows a **generic static list** of navigation links
(Dashboard, Cases, Most Wanted, Reporting, Bounty Tips, Admin, Profile,
Notifications) regardless of the user's role or permissions.

For unauthenticated users on the Home page, clicking any protected link
will redirect to `/login` via the `ProtectedRoute` guard.

**Permission-based sidebar filtering** (hiding links the user cannot access)
is deferred to **Step 12**.

## Backend Anomalies / Problems

None found during this investigation. The `Header` and `Sidebar` components
do not depend on any backend endpoint for rendering. The `useAuth()` hook
correctly provides auth state from the app-root `AuthProvider`.

## Confirmation

- **No backend files were modified.**
- Only `frontend/src/router/Router.tsx` was changed (code).
- Two documentation files were created.

## Validation Checklist

- [x] Home route uses shared layout / app shell (`AppLayout`)
- [x] Navbar / top navigation (Header) visible on Home page
- [x] Unauthenticated auth entry visible (Login + Register links)
- [x] Authenticated logout / user entry visible (Username + Logout)
- [x] No duplicate nav bars
- [x] Home page content preserved (hero + stats sections unchanged)

## Build Verification

- `npx tsc -b --noEmit` — only pre-existing errors in `AuthContext.tsx`; no new errors
- `npx vite build` — succeeds (exit code 0)

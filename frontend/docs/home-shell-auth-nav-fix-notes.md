# Home Page — Shell & Auth Navigation Fix Notes

## Root Cause

The Home page route (`/`) was declared as a **bare top-level route** in
`Router.tsx`, outside the `AppLayout` wrapper. All other non-guest routes
were nested inside `ProtectedRoute > AppLayout`, which meant only
authenticated pages received the shared shell (Header + Sidebar).

Visiting `/` rendered `HomePage` directly with no navigation chrome.

## Route/Layout Changes

**Before:**
```
createBrowserRouter([
  { path: "/", element: <HomePage /> },            // ← bare, no shell
  { path: "/forbidden", element: <ForbiddenPage /> }, // ← bare, no shell
  { element: <GuestRoute />, children: [...] },
  { element: <ProtectedRoute />, children: [
      { element: <AppLayout />, children: [...] }  // ← shell only here
  ]},
])
```

**After:**
```
createBrowserRouter([
  { element: <GuestRoute />, children: [...] },       // login/register (no shell)
  { element: <AppLayout />, children: [                // ← single shared shell
      { path: "/", element: <HomePage /> },            //    public, no auth
      { path: "/forbidden", element: <ForbiddenPage /> }, // public, no auth
      { element: <ProtectedRoute />, children: [...] }, // protected pages
  ]},
])
```

Key change: `AppLayout` wraps **all** non-guest routes (both public and
protected). `ProtectedRoute` is nested inside `AppLayout` so it only gates
access — the shell is always visible.

## Auth Nav Behaviour After Patch

The `Header` component (already on master) conditionally renders:

| Auth state        | Nav actions shown          |
|-------------------|----------------------------|
| Unauthenticated   | Login, Register links      |
| Authenticated     | Username label, Logout btn |

No changes were needed to `Header.tsx` — the ternary was already present on
master but was never exercised on the Home page because the Header was never
rendered there (root cause above).

## Sidebar Behaviour

The Sidebar renders a generic set of navigation links (Dashboard, Cases,
Most Wanted, etc.) regardless of auth state. For an unauthenticated user,
clicking a protected link will redirect to `/login` via `ProtectedRoute`.

Permission-based sidebar filtering (hiding links the user cannot access) is
**deferred to Step 12+**.

## Deferred Items

- Permission-aware sidebar link visibility (Step 12)
- Role-based sidebar section differences
- Active nav highlighting for Home route in Sidebar

# Frontend RBAC Strategy

> Generated: Step 04 — RBAC Strategy  
> Branch: `agent/step-04-rbac-strategy`  
> Source: backend auth analysis, `project-doc.md` §2.2, §5.3, §7

---

## 1. Approach: Permission-Driven, Not Role-Name-Driven

The frontend RBAC is **permission-driven**. We never hardcode logic like `if (role === "Detective")`. Instead, every guard checks the user's `permissions_list` array — a flat list of `"app_label.codename"` strings delivered via:

1. **JWT access token** — `permissions_list` claim (available immediately after login, no extra API call)
2. **`GET /api/accounts/me/`** — `permissions` field (fresh from DB, used to rehydrate on page reload)

This approach is future-proof: when the System Admin creates a new role or reassigns permissions, the frontend adapts automatically without code changes.

### Why Not Role Names?

The project-doc §2.2 explicitly requires: *"the system administrator must be able to add a new role, delete existing roles, or modify them"* without changing code. If the frontend checks `role === "Sergeant"`, a renamed or new role breaks the UI. Permission strings are stable identifiers.

### Hierarchy Level as Secondary Guard

Some actions are not tied to a specific permission but to rank (e.g., "only Police Officer or above can create a crime-scene case"). For these, we check `hierarchy_level ≥ N` from the JWT/me payload. This is a secondary mechanism used **only** where the backend service layer also enforces hierarchy.

---

## 2. Permission Data Sources

```
Login → JWT access token → decode → { role, hierarchy_level, permissions_list }
                                         ↓  
                              Store in auth context (React state)
                                         ↓
Page reload → GET /api/accounts/me/ → rehydrate auth context
```

### Bootstrap Flow

1. **On login**: decode the JWT access token to extract `permissions_list`, `role`, `hierarchy_level`. Store in React auth context.
2. **On page reload (token in storage)**: call `GET /api/accounts/me/` to get fresh user data + permissions. This handles cases where permissions changed since the token was issued.
3. **On token refresh**: the new access token contains updated claims. Re-extract and update context.
4. **On logout**: clear auth context and stored tokens.

### Staleness Window

JWT claims become stale if an admin changes the user's role/permissions mid-session. The max staleness window is the access token lifetime (30 minutes). Mitigations:
- Rehydrate from `/me` on each page reload
- Backend service layer is the final authority; if a stale frontend allows an action, the backend will reject it with 403

---

## 3. Guard Types

### 3.1 Route Guard (`<ProtectedRoute>`)

Wraps route components. Prevents rendering if access criteria are not met.

```
<ProtectedRoute
  requireAuth                           // must be logged in
  permissions={["cases.view_case"]}     // AND logic: all must be present
  minHierarchy={7}                      // optional: hierarchy_level >= 7
  fallback="redirect"                   // "redirect" | "forbidden"
>
  <CaseListPage />
</ProtectedRoute>
```

**Behavior:**
| Condition | Action |
|-----------|--------|
| Not authenticated | Redirect to `/login` (save intended URL for post-login redirect) |
| Authenticated but missing permission | Show 403 Forbidden page |
| Authenticated and authorized | Render children |

**Where used:** In the route config (`routes.ts`) already defines `authRequired`, `minHierarchy`, and `requiredPermissions` for each route.

### 3.2 Component Guard (`<Can>`)

Conditionally renders UI fragments (dashboard modules, nav items, sections).

```
<Can permissions={["board.view_detectiveboard"]}>
  <DashboardModule title="Detective Board" ... />
</Can>
```

**Behavior:**
| Missing permission | Render |
|-------------------|--------|
| Default | Nothing (hidden) |
| `fallback={<Disabled/>}` | Fallback component |

**Where used:** Dashboard module cards, sidebar nav items, page sections.

### 3.3 Action Guard (`can()` utility)

Imperative check for enabling/disabling buttons, showing action menus, etc.

```ts
const { can } = useAuth();

<button disabled={!can("suspects.can_issue_arrest_warrant")}>
  Issue Warrant
</button>
```

**Behavior:**
| Missing permission | Effect |
|-------------------|--------|
| Button | `disabled` attribute + tooltip "Insufficient permissions" |
| Menu item | Hidden or grayed out |
| Form submit | Prevented |

**Where used:** Action buttons, form submissions, context menus.

### 3.4 Hierarchy Guard

A special case for actions gated by rank rather than specific permission:

```ts
const { hasMinHierarchy } = useAuth();

// Only Police Officer (6) and above can create crime-scene cases
if (hasMinHierarchy(6)) { ... }
```

---

## 4. Fallback UX Strategy

| Scenario | UX Response |
|----------|-------------|
| **Unauthenticated → protected route** | Redirect to `/login` with `?next=` param |
| **Authenticated → unauthorized route** | Render 403 Forbidden page (not redirect) |
| **Authenticated → unauthorized action** | Disable button/control; show tooltip |
| **Authenticated → unauthorized dashboard module** | Hide the module entirely |
| **Authenticated → unauthorized nav item** | Hide nav item |
| **Backend returns 403 on action** | Show toast/alert error; do NOT redirect away |
| **Token expired mid-session** | Attempt silent refresh; if refresh fails → redirect to `/login` |

### Why "Hide" for Modules/Nav, "Disable" for Actions?

- **Hiding** unused modules/nav items keeps the UI clean and prevents cognitive overload. Users shouldn't see features they can never use.
- **Disabling** action buttons (rather than hiding) provides contextual awareness — the user sees the action exists but understands they lack permission. This is important for buttons within a page the user can already access (e.g., a Sergeant viewing a case can see the "Forward to Judiciary" button disabled because they need Captain rank).

---

## 5. Auth Context Shape

```ts
interface AuthContext {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;  // true during bootstrap/rehydration
  
  // Permission checks
  can: (permission: string) => boolean;
  canAll: (permissions: string[]) => boolean;
  canAny: (permissions: string[]) => boolean;
  hasMinHierarchy: (level: number) => boolean;
  
  // Actions
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;  // re-fetch from /me
}
```

The `can*` functions read from a `Set<string>` built from `permissions_list` for O(1) lookups.

---

## 6. Token Storage Strategy

| Item | Storage | Reason |
|------|---------|--------|
| Access token | In-memory (React state) | Prevents XSS access to token; lost on tab close is OK since refresh token persists |
| Refresh token | `httpOnly` cookie (preferred) OR `localStorage` | If backend sets `httpOnly` cookie: most secure. If not: `localStorage` as fallback with refresh-on-load pattern |

> **Backend note**: SimpleJWT returns tokens as JSON response body, not as cookies. The frontend will store the refresh token in `localStorage` and the access token in memory. This is a pragmatic choice given the backend's current behavior.

---

## 7. Permission String Constants

All permission strings used by the frontend are centralized in `frontend/src/auth/permissions.ts` to avoid magic strings scattered across components. The constants mirror `core/permissions_constants.py` but use the full `"app_label.codename"` format.

---

## 8. Integration Points with Route Config

The route config from Step 03 (`frontend/src/router/routes.ts`) already defines:
- `authRequired: boolean` → maps to Route Guard auth check
- `minHierarchy?: number` → maps to hierarchy guard
- `requiredPermissions?: string[]` → maps to permission guard (AND logic)

When `react-router-dom` is installed, the `<ProtectedRoute>` wrapper will read these config values and apply guards automatically.

---

## 9. Backend Anomalies Affecting RBAC

### 9.1 No `DEFAULT_PERMISSION_CLASSES` in Settings

`REST_FRAMEWORK` config has no `DEFAULT_PERMISSION_CLASSES`. DRF defaults to `AllowAny`. Every view explicitly sets `[IsAuthenticated]`, but any new view without it would be unprotected.

**Frontend impact:** None directly. The frontend always sends JWT headers for authenticated requests.

### 9.2 All Fine-Grained Auth is Service-Layer Only

No custom DRF permission classes exist. All authorization (role checks, hierarchy comparisons, ownership verification) is enforced inside service methods, not at the view/middleware level.

**Frontend impact:** The backend will return 403 errors as business-logic exceptions, not as DRF permission-denied responses. Error messages may differ from standard DRF format. The frontend error handler should handle both `{"detail": "..."}` and custom error shapes.

### 9.3 Service-Layer Uses Role Names in Some Places

`UserManagementService.assign_role()` checks `performed_by.role.name == "System Admin"`. This is a hardcoded role-name check on the backend side.

**Frontend impact:** The frontend should NOT mirror this. Use the permission-based approach (`accounts.change_user`). If the backend rejects, show the 403 error.

### 9.4 Home Page Stats Require Auth (Contradicts Doc)

`DashboardStatsView` uses `[IsAuthenticated]`, but §5.1 describes the home page as a public-facing intro page with stats. This means unauthenticated visitors cannot see stats.

**Frontend impact:** Show the home page publicly with static intro content. Stats section shown only if authenticated, with a "login to see live statistics" fallback for unauthenticated visitors.

### 9.5 Most Wanted Page Requires Auth (Ambiguous in Doc)

§4.7 says "visible to all users", but "all users" may mean "all authenticated users" (even Base User). Backend requires `IsAuthenticated`.

**Frontend impact:** Gate the most-wanted route with `auth-only`. No specific permission needed beyond authentication.

### 9.6 JWT `permissions_list` Can Be Large

If a role has many permissions (System Admin could have 80+), the JWT payload becomes large. This increases token size and header size per request.

**Frontend impact:** No functional issue, but worth monitoring. The `Set<string>` approach for lookups handles any list size efficiently.

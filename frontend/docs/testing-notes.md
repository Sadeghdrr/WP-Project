# Frontend Testing Notes

## Test Stack

| Tool | Version | Purpose |
|------|---------|---------|
| Vitest | ^4.0.18 | Test runner (Vite-native, fast) |
| @testing-library/react | ^16.3.2 | Component rendering & DOM queries |
| @testing-library/jest-dom | ^6.9.1 | Custom DOM matchers (toBeInTheDocument, etc.) |
| jsdom | ^28.1.0 | Browser environment simulation |

Configuration lives in `vite.config.ts` (`test` block) and `src/test/setup.ts`.

## How to Run Tests

```bash
# Run all tests once
npm test
# or
npx vitest run

# Watch mode (re-runs on file change)
npm run test:watch
# or
npx vitest
```

## Tests Added

### 1. `src/test/can.test.ts` — Permission Utilities (18 tests)
Pure function unit tests for the permission-checking module:
- `can()` — single permission check (present / absent / empty set)
- `canAll()` — AND logic (all met / partial / empty array)
- `canAny()` — OR logic (one present / none / empty array)
- `hasMinHierarchy()` — hierarchy level comparisons
- `checkAccess()` — combined permission + hierarchy guard
- `buildPermissionSet()` — Set factory from permission arrays

### 2. `src/test/tokenStorage.test.ts` — Token Storage (6 tests)
- Get returns null when empty
- Store + retrieve round-trip
- Clear removes stored token
- Graceful handling of localStorage exceptions (get + store)
- Stores under correct localStorage key

### 3. `src/test/LoginPage.test.tsx` — Login Page (7 tests)
- Renders identifier & password fields
- Submit button disabled when fields empty
- Submit button enabled when both fields filled
- Redirects to /dashboard when already authenticated
- Calls login with correct credentials on submit
- Displays backend error message on failure
- Shows link to registration page

### 4. `src/test/RouteGuards.test.tsx` — Protected/Guest Routes (6 tests)
- ProtectedRoute renders children when authenticated
- ProtectedRoute redirects to /login when unauthenticated
- ProtectedRoute shows loading during bootstrap
- GuestRoute renders children when unauthenticated
- GuestRoute redirects to /dashboard when authenticated
- GuestRoute shows loading during bootstrap

### 5. `src/test/ErrorBoundary.test.tsx` — Error Handling (5 tests)
- Renders children normally
- Catches render errors and shows fallback UI
- Displays the error message in fallback
- Uses custom fallback when provided
- Shows reload button in default fallback

### 6. `src/test/apiClient.test.ts` — API Client (13 tests)
- Token management (store/retrieve)
- Authorization header injection (with/without token)
- Successful JSON response handling
- 204 No Content handling
- DRF `detail` error normalization
- DRF validation field error normalization
- `non_field_errors` as main message
- 401 handler callback triggered
- Non-401 errors don't trigger unauthorized callback
- Network error handling
- Content-Type header for JSON vs FormData

### Pre-existing Tests
- `src/test/AddEvidencePage.test.tsx` — 9 tests (evidence form validation, type selector, backend error mapping)
- `src/test/EvidenceListPage.test.tsx` — 6 tests (list rendering, filters, loading/error states)

## Known Gaps / Deferred Tests

- **Full AuthContext provider test**: Would require mocking multiple API modules + async bootstrap flow. Current coverage is achieved indirectly through LoginPage/RouteGuards tests that mock useAuth.
- **React Query mutation hooks**: cache invalidation after mutations tested at the component integration level in existing evidence tests rather than at the hook level.
- **Dashboard / Board pages**: Complex component trees with many dependencies; deferred to avoid brittle tests.
- **E2E / Playwright tests**: Not added in this step. Could be added for critical user journeys (login → dashboard → create case) as a future enhancement.
- **Reporting / Admin pages**: Lower priority; core flows (auth, permissions, evidence, errors) are covered first.

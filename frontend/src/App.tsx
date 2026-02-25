import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "./components/ui";
import { AuthProvider } from "./auth";
import AppRouter from "./router/Router";

/**
 * Shared QueryClient — created once at module scope so the cache
 * persists for the lifetime of the application.
 *
 * Default behaviour:
 *   - staleTime 60 s → avoids redundant refetches on rapid navigation
 *   - retry 1        → one automatic retry on failure
 *   - refetchOnWindowFocus false → less noise during dev
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

/**
 * Root application component.
 *
 * Provider ordering (outer → inner):
 *   1. QueryClientProvider – data-fetching cache
 *   2. AuthProvider        – auth state, login/logout, token management
 *   3. ErrorBoundary       – catches unhandled render errors
 *   4. AppRouter           – RouterProvider with all route definitions
 */
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ErrorBoundary>
          <AppRouter />
        </ErrorBoundary>
      </AuthProvider>
    </QueryClientProvider>
  );
}

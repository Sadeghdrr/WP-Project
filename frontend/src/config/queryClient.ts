/**
 * React Query client — shared configuration.
 *
 * Defaults:
 * - staleTime  : 30 s (avoids refetching unchanged data too aggressively)
 * - gcTime     : 5 min (garbage-collect inactive queries)
 * - retry      : 1 (one automatic retry on failure)
 * - refetchOnWindowFocus : true (keep data fresh when user tabs back)
 */
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
});

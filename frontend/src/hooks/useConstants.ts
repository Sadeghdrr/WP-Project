/**
 * useConstants — React Query hook for system constants.
 *
 * Fetches GET /api/core/constants/ and caches the result for the
 * lifetime of the session (staleTime = Infinity).  Constants rarely
 * change, so this avoids redundant network calls.
 *
 * Usage:
 *   const { data: constants, isLoading } = useConstants();
 *   constants?.crime_levels.map(...)
 */

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "../api/client";
import { API } from "../api/endpoints";
import type { SystemConstants } from "../types/core";

/** React Query cache key for constants. */
export const CONSTANTS_QUERY_KEY = ["system-constants"] as const;

/**
 * Fetch system constants from the backend.
 * Exported for use outside of React (e.g. prefetching).
 */
export async function fetchConstants(): Promise<SystemConstants> {
  const result = await apiGet<SystemConstants>(API.SYSTEM_CONSTANTS);
  if (!result.ok) {
    throw new Error(result.error.message);
  }
  return result.data;
}

/**
 * React hook wrapping the constants query.
 *
 * - `staleTime: Infinity` → fetched once, never refetched automatically
 * - `gcTime: Infinity`    → stays in cache for the session
 * - `retry: 2`            → retry twice on failure
 */
export function useConstants() {
  return useQuery<SystemConstants>({
    queryKey: CONSTANTS_QUERY_KEY,
    queryFn: fetchConstants,
    staleTime: Infinity,
    gcTime: Infinity,
    retry: 2,
  });
}

// ---------------------------------------------------------------------------
// Lookup helpers — convenience functions over the cached data
// ---------------------------------------------------------------------------

/**
 * Find the label for a choice value inside a choice list.
 * Returns the value itself if not found (safe fallback).
 */
export function lookupLabel(
  choices: Array<{ value: string; label: string }> | undefined,
  value: string,
): string {
  return choices?.find((c) => c.value === value)?.label ?? value;
}

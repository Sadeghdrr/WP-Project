/**
 * useDashboardStats — React Query hook for the dashboard endpoint.
 *
 * Fetches GET /api/core/dashboard/ and caches the result.
 * The backend returns role-aware data — the response shape is the same
 * for all roles, but the data is scoped to what the user can see.
 */

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "../api/client";
import { API } from "../api/endpoints";
import type { DashboardStats } from "../types/core";

export const DASHBOARD_QUERY_KEY = ["dashboard-stats"] as const;

async function fetchDashboardStats(): Promise<DashboardStats> {
  const result = await apiGet<DashboardStats>(API.DASHBOARD_STATS);
  if (!result.ok) {
    throw new Error(result.error.message);
  }
  return result.data;
}

/**
 * React hook wrapping the dashboard stats query.
 *
 * - `staleTime: 2 min` → data considered fresh for 2 minutes
 * - `retry: 1`         → retry once on failure
 */
export function useDashboardStats() {
  return useQuery<DashboardStats>({
    queryKey: [...DASHBOARD_QUERY_KEY],
    queryFn: fetchDashboardStats,
    staleTime: 2 * 60 * 1000,
    retry: 1,
  });
}

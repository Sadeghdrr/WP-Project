/**
 * React Query hook for fetching a full case report.
 *
 * Calls GET /api/cases/{id}/report/ — restricted to Judge, Captain,
 * Police Chief, or System Administrator on the backend.
 */

import { useQuery } from "@tanstack/react-query";
import * as casesApi from "../api/cases";
import type { CaseReport } from "../types";

export const caseReportKey = (id: number) => ["cases", id, "report"] as const;

/** Custom error that carries the HTTP status code */
export class ReportFetchError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ReportFetchError";
    this.status = status;
  }
}

export function useCaseReport(caseId: number | undefined) {
  return useQuery<CaseReport, ReportFetchError>({
    queryKey: caseReportKey(caseId!),
    queryFn: async () => {
      const res = await casesApi.fetchCaseReport(caseId!);
      if (!res.ok) throw new ReportFetchError(res.error.message, res.status);
      return res.data;
    },
    enabled: caseId !== undefined,
    staleTime: 60_000,
    retry: (failureCount, error) => {
      if (error.status === 403 || error.status === 404) return false;
      return failureCount < 2;
    },
  });
}

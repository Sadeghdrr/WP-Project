/**
 * Global search API call.
 *
 * Wraps GET /api/core/search/ with typed request/response.
 */

import { apiGet } from "./client";
import type { ApiResponse } from "./client";
import { API } from "./endpoints";
import type { GlobalSearchResponse, SearchCategory } from "../types/core";

export interface SearchParams {
  q: string;
  category?: SearchCategory;
  limit?: number;
}

/** GET /api/core/search/?q=...&category=...&limit=... */
export function globalSearchApi(
  params: SearchParams,
): Promise<ApiResponse<GlobalSearchResponse>> {
  const qs = new URLSearchParams();
  qs.set("q", params.q);
  if (params.category) qs.set("category", params.category);
  if (params.limit != null) qs.set("limit", String(params.limit));
  return apiGet<GlobalSearchResponse>(`${API.GLOBAL_SEARCH}?${qs.toString()}`);
}

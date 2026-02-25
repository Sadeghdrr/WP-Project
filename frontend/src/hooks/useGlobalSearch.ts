/**
 * useGlobalSearch — React Query + debounce hook for global search.
 *
 * Only fires requests when the debounced query is >= 2 chars.
 * Returns loading/error/data states for the search dropdown.
 */

import { useQuery } from "@tanstack/react-query";
import { globalSearchApi } from "../api/search";
import type { SearchCategory } from "../types/core";
import type { GlobalSearchResponse } from "../types/core";
import type { ApiError } from "../api/client";
import { useDebounce } from "./useDebounce";

const SEARCH_DEBOUNCE_MS = 350;
const MIN_QUERY_LENGTH = 2;

export interface UseGlobalSearchOptions {
  category?: SearchCategory;
  limit?: number;
}

export function useGlobalSearch(
  rawQuery: string,
  options: UseGlobalSearchOptions = {},
) {
  const debouncedQuery = useDebounce(rawQuery.trim(), SEARCH_DEBOUNCE_MS);
  const enabled = debouncedQuery.length >= MIN_QUERY_LENGTH;

  const query = useQuery<GlobalSearchResponse, ApiError>({
    queryKey: ["global-search", debouncedQuery, options.category, options.limit],
    queryFn: async () => {
      const result = await globalSearchApi({
        q: debouncedQuery,
        category: options.category,
        limit: options.limit,
      });
      if (!result.ok) throw result.error;
      return result.data;
    },
    enabled,
    staleTime: 30_000,
    gcTime: 60_000,
    retry: false,
  });

  return {
    ...query,
    /** Whether we have a query that meets the minimum length after debounce */
    isQueryValid: enabled,
    /** The debounced query string actually being searched */
    debouncedQuery,
  };
}

/**
 * API module barrel export.
 */
export {
  apiFetch,
  apiGet,
  apiPost,
  apiPut,
  apiPatch,
  apiDelete,
  apiPostForm,
  apiPatchForm,
  setAccessToken,
  getAccessToken,
  setOnUnauthorized,
} from "./client";
export type { ApiResponse, ApiError } from "./client";
export { API } from "./endpoints";
export { loginApi, registerApi, refreshTokenApi, fetchMeApi } from "./auth";
export { globalSearchApi } from "./search";
export type { SearchParams } from "./search";
export * as casesApi from "./cases";
export type { CaseFilters } from "./cases";
export * as evidenceApi from "./evidence";
export type { EvidenceFilters } from "./evidence";

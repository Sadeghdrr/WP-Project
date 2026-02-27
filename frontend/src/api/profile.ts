/**
 * Profile API — current-user read/update operations.
 *
 * Uses the same /accounts/me/ endpoint that AuthContext bootstraps with,
 * but provides standalone functions for the Profile page to call.
 */

import { apiGet, apiPatch } from "./client";
import type { ApiResponse } from "./client";
import { API } from "./endpoints";
import type { User } from "../types/auth";

// ---------------------------------------------------------------------------
// Request DTOs
// ---------------------------------------------------------------------------

/** Fields the current user is allowed to update. */
export interface UpdateProfileRequest {
  email?: string;
  phone_number?: string;
  first_name?: string;
  last_name?: string;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/** GET /accounts/me/ — fetch the currently authenticated user. */
export function getCurrentUser(): Promise<ApiResponse<User>> {
  return apiGet<User>(API.ME);
}

/** PATCH /accounts/me/ — update editable fields for the current user. */
export function updateCurrentUser(
  data: UpdateProfileRequest,
): Promise<ApiResponse<User>> {
  return apiPatch<User>(API.ME, data);
}

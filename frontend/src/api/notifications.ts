/**
 * Notification API calls.
 *
 * Wraps the core notification endpoints for listing and marking as read.
 */

import { apiGet, apiPost } from "./client";
import type { ApiResponse } from "./client";
import { API } from "./endpoints";
import type { Notification } from "../types/core";

/** GET /api/core/notifications/ — list all notifications for the current user */
export function getNotifications(): Promise<ApiResponse<Notification[]>> {
  return apiGet<Notification[]>(API.NOTIFICATIONS);
}

/** POST /api/core/notifications/{id}/read/ — mark a single notification as read */
export function markNotificationAsRead(
  id: number,
): Promise<ApiResponse<Notification>> {
  return apiPost<Notification>(API.NOTIFICATION_READ(id));
}

import { useEffect, useState, useCallback } from "react";
import { notificationsApi } from "../../api";
import type { Notification } from "../../types";
import styles from "./NotificationsPage.module.css";

/**
 * Full-page notification list.
 *
 * - Fetches all notifications for the current user
 * - Visually distinguishes unread items (accent border + dot)
 * - Clicking an unread notification marks it as read (optimistic update)
 * - Handles loading / empty / error states
 */
export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await notificationsApi.getNotifications();
    if (res.ok) {
      setNotifications(res.data);
    } else {
      setError(res.error.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  async function handleMarkRead(id: number) {
    // Optimistic update
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
    );

    const res = await notificationsApi.markNotificationAsRead(id);
    if (res.ok) {
      // Notify other components (e.g. NotificationBell) about the read
      window.dispatchEvent(new CustomEvent("notification:read"));
    } else {
      // Revert on failure
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: false } : n)),
      );
    }
  }

  function formatDate(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  }

  // ── Render ──────────────────────────────────────────────────────────

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>Notifications</h1>
        <p className={styles.pageSubtitle}>
          {loading
            ? "Loading…"
            : `${notifications.length} notification${notifications.length !== 1 ? "s" : ""}` +
              (unreadCount > 0 ? ` · ${unreadCount} unread` : "")}
        </p>
      </div>

      {loading && <p className={styles.loading}>Loading notifications…</p>}

      {error && (
        <div className={styles.error}>
          <p>Failed to load notifications: {error}</p>
          <button className={styles.retryBtn} onClick={fetchNotifications}>
            Retry
          </button>
        </div>
      )}

      {!loading && !error && notifications.length === 0 && (
        <p className={styles.empty}>No notifications yet.</p>
      )}

      {!loading && !error && notifications.length > 0 && (
        <div className={styles.list}>
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`${styles.item} ${!n.is_read ? styles.itemUnread : ""}`}
              onClick={() => !n.is_read && handleMarkRead(n.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if ((e.key === "Enter" || e.key === " ") && !n.is_read) {
                  e.preventDefault();
                  handleMarkRead(n.id);
                }
              }}
            >
              <span
                className={`${styles.dot} ${n.is_read ? styles.dotRead : ""}`}
                aria-hidden="true"
              />
              <div className={styles.itemBody}>
                <p className={styles.itemTitle}>{n.title}</p>
                <p className={styles.itemMessage}>{n.message}</p>
                <span className={styles.itemDate}>
                  {formatDate(n.created_at)}
                </span>
              </div>
              {!n.is_read && (
                <button
                  className={styles.markReadBtn}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleMarkRead(n.id);
                  }}
                >
                  Mark as read
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

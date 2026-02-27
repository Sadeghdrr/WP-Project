import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { notificationsApi } from "../../api";
import styles from "./NotificationBell.module.css";

/**
 * Bell icon with unread-notification badge for the top bar.
 *
 * Fetches the notification list on mount to derive the unread count.
 * Automatically re-fetches every 60 s so the count stays reasonably current
 * without WebSocket support.
 *
 * Clicking the bell navigates to `/notifications`.
 */

const POLL_INTERVAL_MS = 60_000;

export default function NotificationBell() {
  const [unreadCount, setUnreadCount] = useState(0);
  const navigate = useNavigate();

  const fetchCount = useCallback(async () => {
    const res = await notificationsApi.getNotifications();
    if (res.ok) {
      setUnreadCount(res.data.filter((n) => !n.is_read).length);
    }
  }, []);

  useEffect(() => {
    fetchCount();
    const id = setInterval(fetchCount, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchCount]);

  // Listen for custom event dispatched when a notification is marked read
  // elsewhere (e.g. on the NotificationsPage) so the badge updates instantly.
  useEffect(() => {
    function handleRead() {
      fetchCount();
    }
    window.addEventListener("notification:read", handleRead);
    return () => window.removeEventListener("notification:read", handleRead);
  }, [fetchCount]);

  return (
    <div className={styles.bellWrapper}>
      <button
        className={styles.bellButton}
        onClick={() => navigate("/notifications")}
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
        title="Notifications"
      >
        {/* Inline SVG bell icon – avoids an extra asset/icon library dep */}
        <svg
          className={styles.bellIcon}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>

        {unreadCount > 0 && (
          <span className={styles.badge} aria-hidden="true">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>
    </div>
  );
}

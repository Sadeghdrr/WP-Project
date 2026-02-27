# Step 23 – Notifications System – Agent Report

## Summary

Implemented a complete notification system consisting of:

1. **API service layer** for fetching and marking notifications as read
2. **Notifications page** with full notification list and mark-as-read UX
3. **Bell icon in the top bar** with live unread-count badge
4. **Sidebar cleanup** – removed the Notifications link from sidebar nav

## Files Created

| File | Description |
|---|---|
| `frontend/src/api/notifications.ts` | API service: `getNotifications()`, `markNotificationAsRead(id)` |
| `frontend/src/components/layout/NotificationBell.tsx` | Bell icon component with badge |
| `frontend/src/components/layout/NotificationBell.module.css` | Styles for bell + badge |
| `frontend/src/pages/Notifications/NotificationsPage.module.css` | Styles for notification list page |
| `frontend/docs/notifications-notes.md` | Architecture documentation |
| `md-files/step-23-agent-report.md` | This report |

## Files Modified

| File | Change |
|---|---|
| `frontend/src/api/endpoints.ts` | Added `NOTIFICATION_READ` endpoint helper |
| `frontend/src/api/index.ts` | Exported `notificationsApi` from barrel |
| `frontend/src/pages/Notifications/NotificationsPage.tsx` | Replaced placeholder with full implementation |
| `frontend/src/components/layout/Header.tsx` | Added `NotificationBell` to the top bar |
| `frontend/src/components/layout/Sidebar.tsx` | Removed `{ to: "/notifications", label: "Notifications" }` |
| `frontend/src/components/layout/index.ts` | Exported `NotificationBell` from barrel |

## API Integration Details

| Action | Method | Endpoint |
|---|---|---|
| List notifications | `GET` | `/api/core/notifications/` |
| Mark as read | `POST` | `/api/core/notifications/{id}/read/` |

Both use the existing `apiFetch` wrapper which handles auth token injection and
error normalisation.

## How Unread Count Works

1. `NotificationBell` fetches `GET /core/notifications/` on mount.
2. Derives count: `notifications.filter(n => !n.is_read).length`.
3. Polls every **60 seconds** to stay current without WebSocket support.
4. Listens for `window` custom event `"notification:read"` dispatched by the
   `NotificationsPage` whenever a notification is successfully marked read —
   triggers an immediate re-fetch of the count.

## UI Behavior Summary

### Notifications Page
- Shows all notifications sorted by the API's default order
- Unread items have a blue left border and a solid dot indicator
- Read items have a clean, muted appearance
- Clicking an unread notification optimistically marks it as read
- Explicit "Mark as read" button also available per item
- Loading, empty, and error states are handled with retry option

### Top Bar Bell
- Positioned between the global search and navigation links
- Shows an SVG bell icon (no icon library dependency)
- Red badge displays unread count (caps at "99+")
- Badge hidden when unread count is 0
- Clicking navigates to `/notifications`
- Only rendered when user is authenticated

### Sidebar
- Notifications link fully removed from the "System" section
- Notifications only accessible via the header bell icon

## Edge Cases Handled

- **Empty notification list** – "No notifications yet." message
- **API errors** – error message with retry button
- **Optimistic revert** – if mark-as-read API fails, the notification reverts
  to unread state in the UI
- **Badge overflow** – displays "99+" for counts exceeding 99
- **Keyboard accessibility** – notification items are focusable and respond to
  Enter/Space
- **Unauthenticated** – bell only renders when user is logged in

## Backend Anomalies

None observed. The `GET /core/notifications/` and
`POST /core/notifications/{id}/read/` endpoints behave as documented:
- Returns a flat array (no pagination envelope)
- Mark-as-read returns the updated notification object
- Types (`Notification`, `NotificationMarkReadRequest`) were already defined in
  `frontend/src/types/core.ts`

## Confirmation

- ✅ No backend files were modified
- ✅ Bell icon exists in the header
- ✅ Unread count badge works and syncs
- ✅ Notifications page fetches and renders correctly
- ✅ Mark-as-read API is called on click
- ✅ Sidebar notifications link removed
- ✅ TypeScript compilation passes (`tsc --noEmit` — zero errors)

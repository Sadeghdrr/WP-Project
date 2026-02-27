# Notifications System – Architecture Notes

## Overview

The notification system provides users with a bell icon in the top bar showing
unread notification count, and a dedicated `/notifications` page listing all
notifications with the ability to mark them as read.

## API Integration

| Action | Method | Endpoint |
|---|---|---|
| List notifications | `GET` | `/api/core/notifications/` |
| Mark as read | `POST` | `/api/core/notifications/{id}/read/` |

Both calls use the shared `apiFetch` wrapper which automatically injects the
`Authorization: Bearer <token>` header and handles error normalisation.

### Response shape

```json
[
  {
    "id": 1,
    "title": "Evidence updated",
    "message": "New forensic report added to Case #42",
    "is_read": false,
    "created_at": "2026-02-27T03:21:15.319Z",
    "content_type": "case",
    "object_id": 42
  }
]
```

## State Synchronization

### Unread count

The `NotificationBell` component in the header fetches notifications on mount
and derives the unread count by filtering `is_read === false`. It re-fetches on
a 60-second polling interval to keep the count reasonably current without
WebSocket support.

### Cross-component sync

When a notification is marked as read on the `NotificationsPage`, a custom DOM
event `notification:read` is dispatched on `window`. The `NotificationBell`
listens for this event and re-fetches its count immediately, keeping the badge
in sync without shared React state or a global store.

### Optimistic updates

On the notifications page, clicking an unread notification optimistically flips
`is_read` to `true` in local state before the API responds. If the API call
fails, the change is reverted.

## Component Architecture

```
Header.tsx
  └── NotificationBell.tsx   ← bell icon + badge; navigates to /notifications
        └── fetches GET /core/notifications/ (poll every 60 s)

NotificationsPage.tsx         ← full page list
  └── fetches GET /core/notifications/ (on mount)
  └── calls POST /core/notifications/{id}/read/ on click
  └── dispatches "notification:read" event on success
```

## Sidebar Cleanup

The `Notifications` link was removed from the sidebar navigation in
`Sidebar.tsx`. Notifications are now **only** accessible via the header bell
icon, which navigates to `/notifications`.

## Known Limitations

1. **No real-time updates** – relies on 60 s polling; no WebSocket/SSE
   integration.
2. **No pagination** – the full notification list is fetched at once. For users
   with a very large notification history this could become slow.
3. **No "mark all as read"** – only individual mark-as-read is supported (the
   backend does not expose a bulk endpoint).
4. **No push notifications** – browser push is out of scope.
5. **content_type / object_id** – present in the API response but not used for
   deep linking yet. Could be used in the future to navigate to the related
   entity.

# Profile Feature — Architecture Notes

## Overview

The profile feature allows the authenticated user to view and edit their personal information via `GET /api/accounts/me/` and `PATCH /api/accounts/me/`.

## Architecture Decisions

### API Layer (`src/api/profile.ts`)

- Created a dedicated `profile.ts` module with `getCurrentUser()` and `updateCurrentUser()` functions.
- Reuses the `apiGet` / `apiPatch` wrappers from `client.ts`.
- Shares the `API.ME` endpoint constant already in `endpoints.ts`, same endpoint used by AuthContext for session bootstrap.
- Defines an `UpdateProfileRequest` interface restricting fields to the PATCH-allowed set.

### Why a Separate API Module

Although `fetchMeApi` already exists in `auth.ts`, the profile module provides a clear separation of concerns:
- `auth.ts` handles login/register/refresh/session bootstrap.
- `profile.ts` handles intentional user-facing read/update operations.
- The update function (`PATCH`) doesn't belong in the auth module.

### Fields Shown / Hidden

**Displayed (read-only):**
- `username` — identity, not editable
- `role_detail.name` — shown as "Role"; falls back to `role` string if `role_detail` is null
- `date_joined` — formatted as locale date string

**Displayed (editable):**
- `email` — validated with basic regex
- `phone_number` — optional
- `first_name` — required
- `last_name` — required

**Hidden:**
- `id` — internal identifier, not useful to user
- `national_id` — sensitive; displayed at registration but not editable here
- `is_active` — system field
- `role` (raw) — redundant with `role_detail.name`
- `role_detail.id`, `role_detail.description`, `role_detail.hierarchy_level` — internal
- `permissions` — array of codenames, not meaningful to end user

### Validation Approach

Client-side validation is "basic but solid":
- Email: required + regex format check (`/^[^\s@]+@[^\s@]+\.[^\s@]+$/`)
- First/Last name: required (non-empty after trim)
- Phone number: optional (no format enforcement — international variations)
- Backend field errors (422/400) are also mapped and displayed per-field.

### Update Flow

1. User edits form fields.
2. Click "Save Changes" → client validation runs.
3. If valid, PATCH request sent with trimmed values.
4. On success: user state updated, form synced with response, success message shown.
5. On error: error message shown, field-level errors mapped from backend response.
6. No full-page reload — everything is in-place.

### TopBar Profile Icon

- `ProfileIcon` component added next to `NotificationBell` in the Header.
- Uses an inline SVG (user-circle icon) — same zero-dependency approach as NotificationBell.
- Clicking navigates to `/profile`.

### Sidebar Cleanup

- Removed the `{ to: "/profile", label: "Profile" }` entry from Sidebar's `NAV_SECTIONS`.
- Profile is now exclusively accessible via the TopBar icon, preventing duplicate navigation entries.

## Known Limitations

- No password change functionality (non-goal).
- No avatar/photo upload (non-goal).
- `national_id` is not editable — by design, it's an immutable identifier.
- Phone number has no format validation — intentional to support international formats.
- Success message clears on next submit, not on a timer.

# Accounts Services — RBAC Implementation Report

**Branch:** `feat/accounts-services`  
**Date:** February 22, 2026  
**Scope:** Role Management, User Management, Current User ("Me") services, and full permission flattening.

---

## 1. Endpoint → Service Mapping Table

All URLs are relative to `/api/accounts/`.

| HTTP Method | URL                                | View Method                          | Service Method                                          |
|-------------|------------------------------------|--------------------------------------|---------------------------------------------------------|
| `GET`       | `/me/`                             | `MeView.get`                         | `CurrentUserService.get_profile(user)`                  |
| `PATCH`     | `/me/`                             | `MeView.patch`                       | `CurrentUserService.update_profile(user, data)`         |
| `GET`       | `/users/`                          | `UserViewSet.list`                   | `UserManagementService.list_users(**filters)`            |
| `GET`       | `/users/{id}/`                     | `UserViewSet.retrieve`               | `UserManagementService.get_user(user_id)`               |
| `PATCH`     | `/users/{id}/assign-role/`         | `UserViewSet.assign_role`            | `UserManagementService.assign_role(user_id, role_id, performed_by)` |
| `PATCH`     | `/users/{id}/activate/`            | `UserViewSet.activate`               | `UserManagementService.activate_user(user_id, performed_by)` |
| `PATCH`     | `/users/{id}/deactivate/`          | `UserViewSet.deactivate`             | `UserManagementService.deactivate_user(user_id, performed_by)` |
| `GET`       | `/roles/`                          | `RoleViewSet.list`                   | `RoleManagementService.list_roles()`                    |
| `POST`      | `/roles/`                          | `RoleViewSet.create`                 | `RoleManagementService.create_role(data)`               |
| `GET`       | `/roles/{id}/`                     | `RoleViewSet.retrieve`               | `RoleManagementService.get_role(role_id)`               |
| `PUT`       | `/roles/{id}/`                     | `RoleViewSet.update`                 | `RoleManagementService.update_role(role_id, data)`      |
| `PATCH`     | `/roles/{id}/`                     | `RoleViewSet.partial_update`         | `RoleManagementService.update_role(role_id, data)`      |
| `DELETE`    | `/roles/{id}/`                     | `RoleViewSet.destroy`                | `RoleManagementService.delete_role(role_id)`            |
| `POST`      | `/roles/{id}/assign-permissions/`  | `RoleViewSet.assign_permissions`     | `RoleManagementService.assign_permissions_to_role(role_id, perm_ids)` |
| `GET`       | `/permissions/`                    | `PermissionListView.get_queryset`    | `list_all_permissions()`                                |

---

## 2. Permission Flattening Strategy — "Me" Endpoint

### Goal

The Next.js frontend needs a **flat list of permission strings** to conditionally render dashboard modules (e.g., show "Detective Board" only if `board.view_board` is present). The frontend must never hard-code role names — it only depends on permissions.

### Data Flow

```
GET /api/accounts/me/
  → MeView.get(request)
     → CurrentUserService.get_profile(request.user)
        → User.objects.select_related('role')
                      .prefetch_related('role__permissions__content_type')
                      .get(pk=user.pk)
     → UserDetailSerializer(user)
        → user.permissions_list  (model @property)
           → user.get_all_permissions()
              → role.permissions M2M → set of "app_label.codename" strings
```

### How `permissions_list` Works

1. The `User` model defines `get_all_permissions()` which:
   - Returns an empty set for inactive users.
   - Returns all permissions for superusers (cached in `_superuser_perm_cache`).
   - For regular users, resolves `self.role.permissions` M2M → `{app_label}.{codename}` strings (cached in `_perm_cache`).

2. The `@property permissions_list` calls `get_all_permissions()` and converts the set to a list.

3. `UserDetailSerializer` maps `source="permissions_list"` to the `permissions` field, producing:

```json
{
  "id": 42,
  "username": "cole_phelps",
  "role": 5,
  "role_detail": {
    "id": 5,
    "name": "Detective",
    "description": "...",
    "hierarchy_level": 5
  },
  "permissions": [
    "cases.view_case",
    "cases.add_case",
    "evidence.view_evidence",
    "board.view_board"
  ]
}
```

### Frontend Usage

```tsx
const { permissions } = useAuth();
{permissions.includes('board.view_board') && <DetectiveBoardModule />}
```

This makes the system truly **dynamic RBAC**: roles and their permissions can be edited at runtime by the System Admin, and the frontend automatically reflects the changes on the next `/me/` fetch.

---

## 3. Service-Level Authorization

Authorization is enforced **inside** the service layer, not in views:

| Service Method                          | Authorization Rule                                                                                   |
|-----------------------------------------|------------------------------------------------------------------------------------------------------|
| `assign_role(performed_by)`             | Performer must be System Admin **OR** have `hierarchy_level` strictly greater than both the target user's current level and the new role's level. |
| `activate_user(performed_by)`           | Performer must be System Admin **OR** have `hierarchy_level` > target's level.                       |
| `deactivate_user(performed_by)`         | Same as activate + **self-deactivation is blocked** (raises `DomainError`).                          |
| Role CRUD endpoints                     | All require `IsAuthenticated`; System Admin access enforced at the view permission level.             |

Unauthorized actions raise `core.domain.exceptions.PermissionDenied` (HTTP 403) or `core.domain.exceptions.DomainError` (HTTP 400), which are automatically handled by the global `domain_exception_handler`.

---

## 4. Error Handling via Domain Exceptions

All service methods use the domain exception hierarchy from `core/domain/exceptions.py`:

| Exception Used       | HTTP | Scenario                                                    |
|----------------------|------|-------------------------------------------------------------|
| `NotFound`           | 404  | User or Role with given PK does not exist                   |
| `PermissionDenied`   | 403  | Performer lacks authority for role assignment / activation  |
| `DomainError`        | 400  | Self-deactivation attempt, role deletion with assigned users, invalid permission IDs |
| `Conflict`           | 409  | Duplicate unique field during registration (existing logic) |

These are mapped to HTTP responses by `core.domain.exception_handler.domain_exception_handler`, registered in `settings.py → REST_FRAMEWORK['EXCEPTION_HANDLER']`.

---

## 5. New Additions to `core/domain/`

**None.** All required exceptions (`DomainError`, `PermissionDenied`, `NotFound`, `Conflict`) already existed in `core/domain/exceptions.py`. No new shared logic was needed.

---

## 6. Files Modified

| File                              | Changes                                                              |
|-----------------------------------|----------------------------------------------------------------------|
| `backend/accounts/services.py`    | Replaced all `NotImplementedError` stubs with production-ready code  |
| `backend/accounts/views.py`       | Connected all view methods to their corresponding service calls      |
| `backend/accounts/serializers.py` | Implemented all validation and display methods                       |

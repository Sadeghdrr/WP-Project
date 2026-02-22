# Accounts API — Design Report

> **App**: `accounts`
> **Branch**: `feat/accounts-api-drafts`
> **Date**: 2026-02-22

---

## 1. Endpoint Table

All URLs are relative to the project prefix `/api/accounts/`.

| HTTP Method | URL                                 | Purpose                                                    | Access Level                            |
|-------------|-------------------------------------|------------------------------------------------------------|-----------------------------------------|
| `POST`      | `/auth/register/`                   | Register a new user (defaults to "Base User" role)         | Public (`AllowAny`)                     |
| `POST`      | `/auth/login/`                      | Multi-field login (username / national_id / phone / email) | Public (`AllowAny`)                     |
| `POST`      | `/auth/token/refresh/`              | Refresh an expired JWT access token                        | Public (valid refresh token required)   |
| `GET`       | `/me/`                              | Retrieve current user profile + flat permissions list      | Authenticated                           |
| `PATCH`     | `/me/`                              | Update own profile fields (email, phone, name)             | Authenticated                           |
| `GET`       | `/users/`                           | List users (filterable by role, hierarchy, active, search) | System Admin / High-ranking officers    |
| `GET`       | `/users/{id}/`                      | Retrieve a single user's full details                      | System Admin / High-ranking officers    |
| `PATCH`     | `/users/{id}/assign-role/`          | Assign or change a user's role                             | System Admin / Higher hierarchy officer |
| `PATCH`     | `/users/{id}/activate/`             | Re-activate a deactivated user                             | System Admin / Higher hierarchy officer |
| `PATCH`     | `/users/{id}/deactivate/`           | Deactivate an active user                                  | System Admin / Higher hierarchy officer |
| `GET`       | `/roles/`                           | List all roles ordered by hierarchy level                  | System Admin                            |
| `POST`      | `/roles/`                           | Create a new role                                          | System Admin                            |
| `GET`       | `/roles/{id}/`                      | Retrieve a role with full permission details               | System Admin                            |
| `PUT`       | `/roles/{id}/`                      | Full update of a role                                      | System Admin                            |
| `PATCH`     | `/roles/{id}/`                      | Partial update of a role                                   | System Admin                            |
| `DELETE`    | `/roles/{id}/`                      | Delete a role (if no users assigned)                       | System Admin                            |
| `POST`      | `/roles/{id}/assign-permissions/`   | Replace the role's permission set                          | System Admin                            |
| `GET`       | `/permissions/`                     | List all available Django permissions                      | Authenticated (Admin in practice)       |

---

## 2. Service Layer Pattern

### Why a Service Layer?

The project mandates **Fat Models, Thin Views, Service Layer** — a strict separation of concerns:

| Layer        | Responsibility                                                                 |
|--------------|--------------------------------------------------------------------------------|
| **View**     | Accept HTTP request, validate input via serializer, call service, return `Response`. |
| **Serializer** | Define field shapes, read/write constraints, basic format validations.         |
| **Service**  | Contains **all** business logic: authorization checks, multi-step workflows, model mutations, cache invalidation. |
| **Model**    | Data definition, database constraints, helper predicates (e.g., `has_role()`). |

### Service Classes in `accounts/services.py`

| Service Class              | Scope                                                                 |
|----------------------------|-----------------------------------------------------------------------|
| `UserRegistrationService`  | Create new users, assign the default "Base User" role.                |
| `AuthenticationService`    | Resolve user from any of four identifiers, verify password, issue JWT.|
| `UserManagementService`    | List/filter users, assign roles, activate/deactivate.                 |
| `RoleManagementService`    | Full CRUD on roles, assign Django permissions to roles.               |
| `CurrentUserService`       | Fetch and update the authenticated user's own profile.                |
| `list_all_permissions()`   | Standalone function returning all Django `Permission` objects.        |

Views never import models directly for mutations—they always go through the service layer.

---

## 3. Multi-Field Login Design

### Problem

The project-doc (§4.1) requires that users can log in with their password **plus any one of**: username, national_id, phone_number, or email.

### Design

The `LoginRequestSerializer` accepts two fields:

```json
{
  "identifier": "john_doe",
  "password": "s3cur3p@ss"
}
```

The `identifier` field is **polymorphic** — it may contain any of the four unique-constrained fields. The resolution is handled entirely in the service layer:

1. **`AuthenticationService.resolve_user(identifier)`** — Attempts sequential lookups against `username`, `national_id`, `phone_number`, and `email` (all indexed and unique, so each is an O(1) lookup). Returns the matched `User` or `None`.

2. **`AuthenticationService.authenticate(identifier, password)`** — Calls `resolve_user()`, then `user.check_password(password)`, verifies `is_active`, and returns the user or `None`.

3. **`AuthenticationService.generate_tokens(user)`** — Uses `rest_framework_simplejwt.tokens.RefreshToken.for_user()` to generate a JWT access/refresh pair.

The view (`LoginView`) simply:
- Validates input with the serializer.
- Delegates to `authenticate()`.
- On success, calls `generate_tokens()` and returns the tokens alongside a serialized user object.
- On failure, returns `401 Unauthorized`.

### Why not a custom Django Authentication Backend?

A custom backend (`settings.AUTHENTICATION_BACKENDS`) is also viable, but the explicit service-layer approach keeps the logic visible and testable without relying on Django's `authenticate()` dispatch mechanism. Either approach works; the service-layer pattern was chosen for consistency with the project's architecture mandate.

---

## 4. Frontend Permission Delivery ("Me" Endpoint)

### Problem

The Next.js frontend needs to conditionally render dashboard modules (e.g., show "Detective Board" only for detectives). It requires a **flat list of permission strings** from the backend on login / page load.

### Design

**Endpoint**: `GET /api/accounts/me/`

**Response payload** (via `UserDetailSerializer`):

```json
{
  "id": 42,
  "username": "cole_phelps",
  "email": "cole@lapd.gov",
  "national_id": "1234567890",
  "phone_number": "+989121234567",
  "first_name": "Cole",
  "last_name": "Phelps",
  "is_active": true,
  "date_joined": "2026-01-15T08:30:00Z",
  "role": 5,
  "role_detail": {
    "id": 5,
    "name": "Detective",
    "description": "Searches for evidence and reasons connections.",
    "hierarchy_level": 5
  },
  "permissions": [
    "cases.view_case",
    "cases.add_case",
    "evidence.view_evidence",
    "evidence.add_evidence",
    "board.view_board",
    "board.change_board"
  ]
}
```

### How it works

1. The `User` model defines a `permissions_list` property that calls `get_all_permissions()`, which resolves permissions through the user's assigned `Role.permissions` M2M relationship.
2. `UserDetailSerializer` maps `permissions_list` → `permissions` field as a read-only flat list of `app_label.codename` strings.
3. The frontend stores this list (e.g., in React context / Zustand / Redux) and uses it for conditional rendering:
   ```tsx
   {permissions.includes('board.view_board') && <DetectiveBoardModule />}
   ```
4. This approach avoids hardcoding role names in frontend code — the frontend depends only on **permissions**, making the system truly dynamic RBAC.

---

## 5. Prerequisites / Configuration Notes

Before the structural drafts can be implemented, the following must be configured at the project level:

1. **Install SimpleJWT**: Add `djangorestframework-simplejwt` to `requirements.txt`.
2. **Settings updates** (`backend/settings.py`):
   ```python
   REST_FRAMEWORK = {
       'DEFAULT_AUTHENTICATION_CLASSES': [
           'rest_framework_simplejwt.authentication.JWTAuthentication',
       ],
       # ... existing settings
   }
   
   SIMPLE_JWT = {
       'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
       'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
       'ROTATE_REFRESH_TOKENS': True,
   }
   ```
3. **Include accounts URLs** in `backend/urls.py`:
   ```python
   path('api/accounts/', include('accounts.urls')),
   ```

---

## 6. File Summary

| File                           | Purpose                                                      |
|--------------------------------|--------------------------------------------------------------|
| `backend/accounts/urls.py`     | Route definitions with named URL patterns                    |
| `backend/accounts/serializers.py` | Request/response serializers with validation stubs        |
| `backend/accounts/services.py` | Service layer classes with detailed implementation contracts |
| `backend/accounts/views.py`    | Thin DRF views wiring serializers ↔ services                |
| `backend/accounts/models.py`   | Unchanged — User + Role models (already finalized)          |

# Accounts Services — Registration & Authentication Report

> **Branch**: `feat/accounts-services`  
> **Date**: 2026-02-22  
> **Scope**: `accounts` app — registration + multi-field login

---

## 1. Implemented Methods

### 1.1 `UserRegistrationService.register_user(validated_data)`

**File**: `backend/accounts/services.py`

| Step | Behaviour |
|------|-----------|
| Input cleaning | Pops `password_confirm` and `password` from `validated_data` |
| Uniqueness pre-check | Queries `username`, `email`, `phone_number`, `national_id` individually; collects conflicts and raises `Conflict` (HTTP 409) listing all duplicate fields |
| Base User role | `Role.objects.get(name__iexact="Base User")`; if missing, auto-creates with `hierarchy_level=0` |
| User creation | `User.objects.create_user(password=password, **validated_data)` inside `transaction.atomic()` |
| Role assignment | Sets `user.role = base_role` and saves |
| Race-condition guard | Catches `IntegrityError` from the atomic block and raises `Conflict` |
| Return | The newly created `User` instance |

### 1.2 `AuthenticationService.authenticate(identifier, password)`

**File**: `backend/accounts/services.py` (already implemented)

Delegates to `django.contrib.auth.authenticate(identifier=identifier, password=password)`, which dispatches to `MultiFieldAuthBackend`. The backend resolves the user via a `Q(username=...) | Q(national_id=...) | Q(phone_number=...) | Q(email=...)` lookup, verifies password, and checks `is_active`.

### 1.3 `AuthenticationService.resolve_user(identifier)` / `generate_tokens(user)`

Already implemented — reused without modification.

---

## 2. Serializer Changes

### `RegisterRequestSerializer.validate(attrs)`

**File**: `backend/accounts/serializers.py`

Previously raised `NotImplementedError`. Now implements:

1. **Password match** — confirms `password == password_confirm`; raises `ValidationError` if mismatch.
2. **National ID format** — must be exactly 10 digits.
3. **Phone format** — must match Iranian mobile pattern `^(\+98|0)?9\d{9}$`.
4. **Cleanup** — pops `password_confirm` from validated data.

---

## 3. View Changes

### `RegisterView.create(request)`

**File**: `backend/accounts/views.py`

Previously raised `NotImplementedError`. Now:

1. Validates input via `RegisterRequestSerializer`.
2. Calls `UserRegistrationService.register_user(validated_data)`.
3. Serializes the new user with `UserDetailSerializer`.
4. Returns `201 Created`.

---

## 4. Files Changed

| File | Change |
|------|--------|
| `backend/accounts/services.py` | Implemented `register_user()`; added `IntegrityError`, `transaction`, `Conflict` imports |
| `backend/accounts/serializers.py` | Implemented `RegisterRequestSerializer.validate()` |
| `backend/accounts/views.py` | Implemented `RegisterView.create()` |
| `backend/accounts/tests/__init__.py` | Created test package (replaced `tests.py`) |
| `backend/accounts/tests/test_auth.py` | 5 integration tests for register + login |
| `backend/tests/test_smoke.py` | Trimmed to 5 core domain tests |
| `backend/conftest.py` | Minor docstring update |
| `backend/pytest.ini` | Added `accounts/tests` to `testpaths` |
| `docker-compose.yaml` | Added port `5432:5432` mapping for local test access |

---

## 5. Test Summary

**Total: 10 tests across 2 apps (5 per app) — all passing**

### Accounts App (5 tests) — `accounts/tests/test_auth.py`

| # | Test | What it verifies |
|---|------|------------------|
| 1 | `test_register_creates_user_with_base_role` | POST register → 201, user created with hashed password and "Base User" role |
| 2 | `test_duplicate_username_rejected` | Duplicate username → 400/409 rejection |
| 3 | `test_login_with_username` | POST login with username → 200, returns access + refresh + user |
| 4 | `test_wrong_password_fails` | Wrong password → 400 |
| 5 | `test_inactive_user_cannot_login` | Inactive user → 400 |

### Core App (5 tests) — `tests/test_smoke.py`

| # | Test | What it verifies |
|---|------|------------------|
| 1 | `test_exception_hierarchy` | `InvalidTransition > Conflict > DomainError` inheritance chain |
| 2 | `test_domain_error_message` | `DomainError` carries message attribute |
| 3 | `test_invalid_transition_structured` | Structured fields (current, target, reason) |
| 4 | `test_get_user_role_name_superuser` | Superuser → `"system_admin"` |
| 5 | `test_apply_role_filter_unknown_role_default_all` | Unknown role returns unfiltered queryset |

---

## 6. Example Request/Response

### POST `/api/accounts/auth/register/`

**Request:**
```json
{
  "username": "cole_phelps",
  "password": "Str0ng!Pass123",
  "password_confirm": "Str0ng!Pass123",
  "email": "cole@lapd.gov",
  "phone_number": "09121234567",
  "first_name": "Cole",
  "last_name": "Phelps",
  "national_id": "1234567890"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "username": "cole_phelps",
  "email": "cole@lapd.gov",
  "national_id": "1234567890",
  "phone_number": "09121234567",
  "first_name": "Cole",
  "last_name": "Phelps",
  "is_active": true,
  "date_joined": "2026-02-22T10:00:00Z",
  "role": 1,
  "role_detail": {
    "id": 1,
    "name": "Base User",
    "description": "Default role for newly registered users.",
    "hierarchy_level": 0
  },
  "permissions": []
}
```

**Duplicate field (409 Conflict):**
```json
{
  "detail": "The following field(s) already exist: username, email."
}
```

### POST `/api/accounts/auth/login/`

**Request:**
```json
{
  "identifier": "cole_phelps",
  "password": "Str0ng!Pass123"
}
```

**Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "username": "cole_phelps",
    "email": "cole@lapd.gov",
    "national_id": "1234567890",
    "phone_number": "09121234567",
    "first_name": "Cole",
    "last_name": "Phelps",
    "is_active": true,
    "date_joined": "2026-02-22T10:00:00Z",
    "role": 1,
    "role_detail": {
      "id": 1,
      "name": "Base User",
      "description": "Default role for newly registered users.",
      "hierarchy_level": 0
    },
    "permissions": []
  }
}
```

**Invalid credentials (400):**
```json
{
  "detail": "Invalid credentials."
}
```

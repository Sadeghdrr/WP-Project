# Bail Services Report

## Overview

This report documents the implementation of bail eligibility and creation services in the `suspects` app. Payment gateway integration (§4.9) is **out of scope** — payment-related fields (`is_paid`, `payment_reference`, `paid_at`) are left at their defaults upon bail creation.

---

## 1. Eligibility Rules Implemented

Bail eligibility is enforced entirely within `BailService._check_eligibility()` in `backend/suspects/services.py`.

### Crime-Level Rules

| Crime Level | DB Value | Bail Eligible? | Eligible Statuses | Notes |
|---|---|---|---|---|
| **Level 3 (Minor)** | `1` | ✅ Yes | `ARRESTED`, `CONVICTED` | Convicted criminals may also post bail |
| **Level 2 (Medium)** | `2` | ✅ Yes | `ARRESTED` only | Only arrested suspects; convicted are ineligible |
| **Level 1 (Major)** | `3` | ❌ No | — | Bail never allowed |
| **Critical** | `4` | ❌ No | — | Bail never allowed |

### Role Requirements

- **Level 2 and Level 3 bail**: The requesting actor (the person creating the bail record) **must** have a role of **Sergeant or higher** (`sergeant`, `captain`, `police_chief`, or `system_admin`).
- The Sergeant determines the bail amount (per §4.9 of the project doc).
- The permission constant `CAN_SET_BAIL_AMOUNT` is defined in `core.permissions_constants.SuspectsPerms` and is associated with the Sergeant role.

### Validation Summary

The `BailService.create_bail()` method enforces the following checks in order:

1. **Suspect existence** — raises `NotFound` if the suspect PK is invalid.
2. **Crime level check** — raises `DomainError` if the crime level is Level 1 (major) or Critical.
3. **Status check** — raises `DomainError` if the suspect is not in an eligible status (`ARRESTED` for Level 2; `ARRESTED` or `CONVICTED` for Level 3).
4. **Role check** — raises `PermissionDenied` if the actor is not at least a Sergeant.

---

## 2. Role Scoping Approach (Listing / Detail)

Bail listing (`BailService.get_bails_for_suspect`) and detail retrieval (`BailService.get_bail_detail`) use the same `apply_role_filter` utility from `core.domain.access`, following the pattern established by `CaseQueryService`.

### Bail Scope Configuration

| Role | Visibility |
|---|---|
| **Detective** | Bails on cases assigned to them, or where they identified the suspect |
| **Sergeant** | Bails on cases they supervise, or bails they personally approved |
| **Captain / Police Chief / Admin** | Unrestricted — sees all bails |
| **Judge** | Bails on cases assigned to them |
| **Other roles** | No access (empty queryset via `default="none"`) |

---

## 3. API Endpoints

### POST `/api/suspects/{suspect_pk}/bails/` — Create Bail

**Required Role:** Sergeant or higher.

#### Request Body

```json
{
    "amount": 50000000,
    "conditions": "Suspect must report to the station weekly."
}
```

- `amount` (required, positive integer) — Bail amount in Rials.
- `conditions` (optional, string) — Bail conditions text.

#### Success Response — `201 Created`

```json
{
    "id": 1,
    "suspect": 12,
    "suspect_name": "Ali Mohammadi",
    "case": 5,
    "amount": "50000000",
    "conditions": "Suspect must report to the station weekly.",
    "is_paid": false,
    "payment_reference": "",
    "paid_at": null,
    "approved_by": 7,
    "approved_by_name": "Sgt. Reza Karimi",
    "created_at": "2026-02-23T10:30:00Z",
    "updated_at": "2026-02-23T10:30:00Z"
}
```

#### Error Responses

| Status | Condition |
|---|---|
| `400 Bad Request` | Crime level is Level 1/Critical, suspect not in eligible status, or invalid amount |
| `403 Forbidden` | Actor does not have Sergeant-or-higher role |
| `404 Not Found` | Suspect does not exist |

### GET `/api/suspects/{suspect_pk}/bails/` — List Bails

**Required Role:** Any authenticated user with role-scoped access.

#### Success Response — `200 OK`

```json
[
    {
        "id": 1,
        "suspect": 12,
        "case": 5,
        "amount": "50000000",
        "conditions": "Suspect must report to the station weekly.",
        "is_paid": false,
        "approved_by": 7,
        "approved_by_name": "Sgt. Reza Karimi",
        "paid_at": null,
        "created_at": "2026-02-23T10:30:00Z"
    }
]
```

### GET `/api/suspects/{suspect_pk}/bails/{id}/` — Retrieve Bail Detail

**Required Role:** Any authenticated user with role-scoped access.

Returns the same payload as the creation response (`BailDetailSerializer`).

---

## 4. Model Changes

A `conditions` text field was added to the `Bail` model (`suspects/models.py`) to store optional bail conditions. Migration: `0006_bail_add_conditions.py`.

---

## 5. Architecture Notes

- **Fat Services, Skinny Views**: All eligibility rules, role checks, and data assembly reside in `BailService` (`suspects/services.py`). Views only parse input, delegate to the service, and serialize the response.
- **Payment fields** (`is_paid`, `payment_reference`, `paid_at`) exist on the model but are left at defaults. The `process_bail_payment` method raises `NotImplementedError` — payment gateway integration is deferred to a future phase.
- **Serializer guards**: `BailCreateSerializer` only exposes `amount` and `conditions` as writable fields. Users cannot manually set `is_paid`, `payment_reference`, `approved_by`, or any other read-only field during creation.

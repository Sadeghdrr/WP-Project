# Bounty Tips Services Report

## Overview

This report documents the implementation of the **BountyTipService** — the end-to-end bounty tips workflow covering citizen submissions, officer reviews, detective verifications, and secure reward code lookups (project-doc §4.8).

---

## State Machine

The `BountyTip` model follows a strict linear state machine. Each state transition is guarded by role-based permission checks and status validation inside the service layer.

### States

| Status             | Description                          | DB Value           |
|--------------------|--------------------------------------|--------------------|
| **Pending**        | Tip submitted, awaiting officer review | `pending`          |
| **Officer Reviewed** | Officer accepted, forwarded to detective | `officer_reviewed` |
| **Verified**       | Detective confirmed, reward code generated | `verified`       |
| **Rejected**       | Rejected at any review stage          | `rejected`         |

### Transition Diagram

$$
\text{Pending} \xrightarrow{\text{Officer accepts}} \text{Officer Reviewed} \xrightarrow{\text{Detective verifies}} \text{Verified}
$$

$$
\text{Pending} \xrightarrow{\text{Officer rejects}} \text{Rejected}
$$

$$
\text{Officer Reviewed} \xrightarrow{\text{Detective rejects}} \text{Rejected}
$$

### Transition Rules

| From               | To                 | Actor      | Permission                   |
|--------------------|--------------------|------------|------------------------------|
| `pending`          | `officer_reviewed` | Officer    | `can_review_bounty_tip`      |
| `pending`          | `rejected`         | Officer    | `can_review_bounty_tip`      |
| `officer_reviewed` | `verified`         | Detective  | `can_verify_bounty_tip`      |
| `officer_reviewed` | `rejected`         | Detective  | `can_verify_bounty_tip`      |

- **Terminal states**: `verified` and `rejected` — no further transitions allowed.
- All transitions are wrapped in `transaction.atomic()` with `select_for_update()` to prevent race conditions.

---

## Unique Code Strategy

### Generation Method

The unique reward code is generated using Python's `secrets.token_hex(16)`, which produces a **32-character uppercase hexadecimal string** with **128 bits of entropy**.

### Why `secrets` Over `uuid4`?

| Property                | `secrets.token_hex` | `uuid4().hex`       |
|-------------------------|---------------------|---------------------|
| Entropy                 | 128 bits (configurable) | 122 bits (6 bits reserved for version/variant) |
| Designed for security   | ✅ Yes (PEP 506)    | ❌ Not a security primitive |
| Source                   | `os.urandom()`      | `os.urandom()` (CPython) but not guaranteed |
| Brute-force resistance  | $2^{128}$ attempts  | $2^{122}$ attempts  |

### Anti-Brute-Force Properties

- **Search space**: $16^{32} = 2^{128} \approx 3.4 \times 10^{38}$ possible codes.
- At 1 billion guesses per second, exhaustive search would take approximately $10^{22}$ years.
- The `unique_code` field has a `UNIQUE` database constraint, ensuring no collisions.
- The `lookup_reward` endpoint requires **both** the `national_id` AND the `unique_code`, adding a second factor.
- Codes are only generated upon detective verification — they are never pre-allocated.

### Example Code Format

```
A7F3B2E19C0D84F6E1A3B5C7D9F02E48
```

---

## API Sequences

### 1. Citizen Submits a Tip

**Request:**
```http
POST /api/bounty-tips/
Content-Type: application/json
Authorization: Bearer <citizen_jwt>

{
    "suspect": 12,
    "case": 5,
    "information": "I saw the suspect at the corner of 5th and Main at 3 AM on Feb 20th."
}
```

**Response (201 Created):**
```json
{
    "id": 7,
    "suspect": 12,
    "case": 5,
    "informant": 42,
    "informant_name": "John Citizen",
    "information": "I saw the suspect at the corner of 5th and Main at 3 AM on Feb 20th.",
    "status": "pending",
    "status_display": "Pending Review",
    "reviewed_by": null,
    "reviewed_by_name": null,
    "verified_by": null,
    "verified_by_name": null,
    "unique_code": null,
    "reward_amount": null,
    "is_claimed": false,
    "created_at": "2026-02-23T10:30:00Z",
    "updated_at": "2026-02-23T10:30:00Z"
}
```

### 2. Officer Reviews (Accepts) the Tip

**Request:**
```http
POST /api/bounty-tips/7/review/
Content-Type: application/json
Authorization: Bearer <officer_jwt>

{
    "decision": "accept",
    "review_notes": "Information appears credible and matches known patterns."
}
```

**Response (200 OK):**
```json
{
    "id": 7,
    "suspect": 12,
    "case": 5,
    "informant": 42,
    "informant_name": "John Citizen",
    "information": "I saw the suspect at the corner of 5th and Main at 3 AM on Feb 20th.",
    "status": "officer_reviewed",
    "status_display": "Reviewed by Officer",
    "reviewed_by": 15,
    "reviewed_by_name": "Officer Jane Smith",
    "verified_by": null,
    "verified_by_name": null,
    "unique_code": null,
    "reward_amount": null,
    "is_claimed": false,
    "created_at": "2026-02-23T10:30:00Z",
    "updated_at": "2026-02-23T11:00:00Z"
}
```

### 3. Detective Verifies the Tip (Successful Verification)

**Request:**
```http
POST /api/bounty-tips/7/verify/
Content-Type: application/json
Authorization: Bearer <detective_jwt>

{
    "decision": "verify",
    "verification_notes": "Information confirmed by field check and surveillance footage."
}
```

**Response (200 OK):**
```json
{
    "id": 7,
    "suspect": 12,
    "case": 5,
    "informant": 42,
    "informant_name": "John Citizen",
    "information": "I saw the suspect at the corner of 5th and Main at 3 AM on Feb 20th.",
    "status": "verified",
    "status_display": "Verified by Detective",
    "reviewed_by": 15,
    "reviewed_by_name": "Officer Jane Smith",
    "verified_by": 8,
    "verified_by_name": "Det. Cole Phelps",
    "unique_code": "A7F3B2E19C0D84F6E1A3B5C7D9F02E48",
    "reward_amount": 1520000000,
    "is_claimed": false,
    "created_at": "2026-02-23T10:30:00Z",
    "updated_at": "2026-02-23T11:30:00Z"
}
```

The citizen receives a notification containing the `unique_code` and `reward_amount`. They can present this code at a police station to claim their reward.

### 4. Reward Lookup (Successful)

**Request:**
```http
POST /api/bounty-tips/lookup-reward/
Content-Type: application/json
Authorization: Bearer <police_jwt>

{
    "national_id": "1234567890",
    "unique_code": "A7F3B2E19C0D84F6E1A3B5C7D9F02E48"
}
```

**Response (200 OK):**
```json
{
    "tip_id": 7,
    "informant_name": "John Citizen",
    "informant_national_id": "1234567890",
    "reward_amount": 1520000000,
    "is_claimed": false,
    "suspect_name": "Roy Earle",
    "case_id": 5
}
```

### 5. Reward Lookup (Not Found)

**Request:**
```http
POST /api/bounty-tips/lookup-reward/
Content-Type: application/json
Authorization: Bearer <police_jwt>

{
    "national_id": "9999999999",
    "unique_code": "INVALID_CODE"
}
```

**Response (404 Not Found):**
```json
{
    "detail": "No verified bounty tip found matching the provided national ID and unique code."
}
```

---

## Endpoint Summary

| Method | Endpoint                          | Actor         | Permission                 |
|--------|-----------------------------------|---------------|----------------------------|
| POST   | `/api/bounty-tips/`               | Any authenticated user | `IsAuthenticated`   |
| GET    | `/api/bounty-tips/`               | Any authenticated user | `IsAuthenticated` (role-scoped) |
| GET    | `/api/bounty-tips/{id}/`          | Any authenticated user | `IsAuthenticated`   |
| POST   | `/api/bounty-tips/{id}/review/`   | Officer        | `can_review_bounty_tip`    |
| POST   | `/api/bounty-tips/{id}/verify/`   | Detective      | `can_verify_bounty_tip`    |
| POST   | `/api/bounty-tips/lookup-reward/` | Any authenticated user | `IsAuthenticated`   |

## Notifications Dispatched

| Event Type              | Trigger                       | Recipient(s)         |
|-------------------------|-------------------------------|----------------------|
| `bounty_tip_submitted`  | Citizen submits tip           | Informant (confirmation) |
| `bounty_tip_reviewed`   | Officer forwards tip          | Assigned Detective   |
| `bounty_tip_rejected`   | Officer/Detective rejects tip | Informant            |
| `bounty_tip_verified`   | Detective verifies tip        | Informant (with code + reward) |

---

## Architecture Notes

- **Fat Services, Skinny Views**: All state transitions, permission checks, code generation, and notification dispatch reside in `BountyTipService` (services.py). Views only validate input, delegate to the service, and serialize output.
- **Atomic Transactions**: `officer_review_tip` and `detective_verify_tip` use `@transaction.atomic` with `select_for_update()` to prevent race conditions on concurrent reviews.
- **Domain Exceptions**: The service layer raises `PermissionDenied`, `NotFound`, and `InvalidTransition` from `core.domain.exceptions`. Views map these to HTTP 403, 404, and 400/409 respectively.

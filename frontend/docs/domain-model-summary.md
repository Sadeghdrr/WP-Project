# Frontend Domain Model Summary

> Generated: Step 03 — Domain Model & Route Map  
> Branch: `agent/step-03-domain-model-and-routes`  
> Source: Backend models (accounts, cases, evidence, suspects, board, core)

---

## Entity Relationship Overview

```
User ──< Role (FK, SET_NULL)
  │
  ├──< Case (created_by, assigned_detective, assigned_sergeant, etc.)
  │     ├──< CaseComplainant (case + user, unique_together)
  │     ├──< CaseWitness (case FK)
  │     ├──< CaseStatusLog (case FK)
  │     ├──< Evidence (case FK, polymorphic subtypes)
  │     │     ├── TestimonyEvidence
  │     │     ├── BiologicalEvidence
  │     │     ├── VehicleEvidence
  │     │     ├── IdentityEvidence
  │     │     └──< EvidenceFile (evidence FK)
  │     ├──< Suspect (case FK)
  │     │     ├──< Warrant (suspect FK)
  │     │     ├──< Interrogation (suspect + case FKs)
  │     │     ├──< Trial (suspect + case FKs)
  │     │     ├──< BountyTip (suspect + case FKs, nullable)
  │     │     ├──< Bail (suspect + case FKs)
  │     │     └──< SuspectStatusLog (suspect FK)
  │     ├──< DetectiveBoard (case 1-to-1)
  │     │     ├──< BoardNote (board FK)
  │     │     ├──< BoardItem (board FK, GenericFK to any entity)
  │     │     └──< BoardConnection (board FK, from_item → to_item)
  │     └──< BountyTip (case FK, nullable)
  │
  └──< Notification (recipient FK, GenericFK to any entity)
```

---

## Core Entities

### 1. User (accounts.User)

Extended from Django's AbstractUser. Multi-field login (username / email / phone / national_id).

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| username | string | unique |
| email | string | unique |
| first_name | string | required |
| last_name | string | required |
| national_id | string | 10 chars, unique |
| phone_number | string | max 15, unique |
| role | Role \| null | FK |
| is_active | boolean | |
| is_staff | boolean | |
| date_joined | string (ISO) | |
| last_login | string (ISO) \| null | |

### 2. Role (accounts.Role)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| name | string | unique, max 100 |
| description | string | |
| hierarchy_level | number | 0–100 |
| permissions | Permission[] | M2M |

### 3. Permission (auth.Permission)

Django's built-in Permission model, referenced by Role.

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| codename | string | e.g. `can_review_complaint` |
| name | string | Human-readable label |
| content_type | number | FK to ContentType |

---

## Case Domain

### 4. Case (cases.Case)

Central entity. Tracks entire lifecycle from complaint → trial.

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| title | string | max 255 |
| description | string | |
| crime_level | CrimeLevel (1–4) | 1=Level3, 2=Level2, 3=Level1, 4=Critical |
| status | CaseStatus | 17 possible values |
| creation_type | `"complaint"` \| `"crime_scene"` | |
| rejection_count | number | 0–n, voided at 3 |
| incident_date | string (ISO) \| null | |
| location | string | |
| created_by | User (nested/id) | |
| approved_by | User \| null | |
| assigned_detective | User \| null | |
| assigned_sergeant | User \| null | |
| assigned_captain | User \| null | |
| assigned_judge | User \| null | |
| is_open | boolean | computed |
| created_at | string (ISO) | |
| updated_at | string (ISO) | |

**CaseStatus values**: `complaint_registered`, `cadet_review`, `returned_to_complainant`, `officer_review`, `returned_to_cadet`, `voided`, `pending_approval`, `open`, `investigation`, `suspect_identified`, `sergeant_review`, `arrest_ordered`, `interrogation`, `captain_review`, `chief_review`, `judiciary`, `closed`

**CrimeLevel values**: `1` (Level 3 — minor), `2` (Level 2 — medium), `3` (Level 1 — major), `4` (Critical)

### 5. CaseComplainant (cases.CaseComplainant)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| case | number | FK |
| user | User (nested/id) | FK |
| is_primary | boolean | |
| status | `"pending"` \| `"approved"` \| `"rejected"` | |
| reviewed_by | User \| null | |
| created_at | string (ISO) | |

### 6. CaseWitness (cases.CaseWitness)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| case | number | FK |
| full_name | string | |
| phone_number | string | |
| national_id | string | 10 chars |
| created_at | string (ISO) | |

### 7. CaseStatusLog (cases.CaseStatusLog)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| case | number | FK |
| from_status | CaseStatus | |
| to_status | CaseStatus | |
| changed_by | User \| null | |
| message | string | |
| created_at | string (ISO) | |

---

## Evidence Domain

### 8. Evidence (evidence.Evidence — base)

Polymorphic base. `evidence_type` discriminator determines subtype fields.

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| case | number | FK |
| evidence_type | EvidenceType | discriminator |
| title | string | max 255 |
| description | string | |
| registered_by | User (nested/id) | |
| files | EvidenceFile[] | nested |
| created_at | string (ISO) | |
| updated_at | string (ISO) | |

**EvidenceType values**: `"testimony"`, `"biological"`, `"vehicle"`, `"identity"`, `"other"`

### 9. TestimonyEvidence (extends Evidence)

| Additional Field | Type |
|------------------|------|
| statement_text | string |

### 10. BiologicalEvidence (extends Evidence)

| Additional Field | Type |
|------------------|------|
| forensic_result | string |
| verified_by | User \| null |
| is_verified | boolean |

### 11. VehicleEvidence (extends Evidence)

| Additional Field | Type | Notes |
|------------------|------|-------|
| vehicle_model | string | |
| color | string | |
| license_plate | string | XOR with serial_number |
| serial_number | string | XOR with license_plate |

### 12. IdentityEvidence (extends Evidence)

| Additional Field | Type | Notes |
|------------------|------|-------|
| owner_full_name | string | |
| document_details | Record<string, string> | key-value pairs, variable count |

### 13. EvidenceFile (evidence.EvidenceFile)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| evidence | number | FK |
| file | string (URL) | |
| file_type | `"image"` \| `"video"` \| `"audio"` \| `"document"` | |
| caption | string | |
| created_at | string (ISO) | |

---

## Suspects Domain

### 14. Suspect (suspects.Suspect)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| case | number | FK |
| user | User \| null | FK, linked account if exists |
| full_name | string | |
| national_id | string | |
| phone_number | string | |
| photo | string (URL) \| null | |
| address | string | |
| description | string | |
| status | SuspectStatus | 9 values |
| wanted_since | string (ISO) | |
| arrested_at | string (ISO) \| null | |
| identified_by | User | |
| approved_by_sergeant | User \| null | |
| sergeant_approval_status | `"pending"` \| `"approved"` \| `"rejected"` | |
| sergeant_rejection_message | string | |
| days_wanted | number | computed |
| is_most_wanted | boolean | computed (>30 days) |
| most_wanted_score | number | computed |
| reward_amount | number | computed (Rials) |
| created_at | string (ISO) | |

**SuspectStatus values**: `"wanted"`, `"arrested"`, `"under_interrogation"`, `"pending_captain_verdict"`, `"pending_chief_approval"`, `"under_trial"`, `"convicted"`, `"acquitted"`, `"released"`

### 15. Warrant (suspects.Warrant)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| suspect | number | FK |
| reason | string | |
| issued_by | User | |
| issued_at | string (ISO) | |
| status | `"active"` \| `"executed"` \| `"expired"` \| `"cancelled"` | |
| priority | `"normal"` \| `"high"` \| `"critical"` | |
| created_at | string (ISO) | |

### 16. Interrogation (suspects.Interrogation)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| suspect | number | FK |
| case | number | FK |
| detective | User | |
| sergeant | User | |
| detective_guilt_score | number | 1–10 |
| sergeant_guilt_score | number | 1–10 |
| notes | string | |
| created_at | string (ISO) | |

### 17. Trial (suspects.Trial)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| suspect | number | FK |
| case | number | FK |
| judge | User | |
| verdict | `"guilty"` \| `"innocent"` | |
| punishment_title | string | only if guilty |
| punishment_description | string | only if guilty |
| created_at | string (ISO) | |

### 18. BountyTip (suspects.BountyTip)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| suspect | number \| null | FK |
| case | number \| null | FK |
| informant | User | |
| information | string | |
| status | BountyTipStatus | |
| reviewed_by | User \| null | |
| verified_by | User \| null | |
| unique_code | string \| null | generated on verification |
| reward_amount | number \| null | in Rials |
| is_claimed | boolean | |
| created_at | string (ISO) | |

**BountyTipStatus values**: `"pending"`, `"officer_reviewed"`, `"verified"`, `"rejected"`

### 19. Bail (suspects.Bail)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| suspect | number | FK |
| case | number | FK |
| amount | number | Rials, decimal |
| approved_by | User | |
| conditions | string | |
| is_paid | boolean | |
| payment_reference | string | |
| paid_at | string (ISO) \| null | |
| created_at | string (ISO) | |

---

## Detective Board Domain

### 20. DetectiveBoard (board.DetectiveBoard)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| case | number | 1-to-1 with Case |
| detective | User | |
| created_at | string (ISO) | |

### 21. BoardNote (board.BoardNote)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| board | number | FK |
| title | string | |
| content | string | |
| created_by | User | |
| created_at | string (ISO) | |

### 22. BoardItem (board.BoardItem)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| board | number | FK |
| content_type | number | Django ContentType FK |
| object_id | number | Generic FK |
| position_x | number | float, default 0 |
| position_y | number | float, default 0 |
| created_at | string (ISO) | |

### 23. BoardConnection (board.BoardConnection)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| board | number | FK |
| from_item | number | FK → BoardItem |
| to_item | number | FK → BoardItem |
| label | string | |
| created_at | string (ISO) | |

---

## Notification

### 24. Notification (core.Notification)

| Frontend Field | Type | Notes |
|----------------|------|-------|
| id | number | PK |
| recipient | number | FK → User |
| title | string | |
| message | string | |
| is_read | boolean | |
| content_type | number \| null | Generic FK |
| object_id | number \| null | Generic FK |
| created_at | string (ISO) | |

---

## Auth / JWT

Login returns JWT token pair. Access token carries custom claims.

| Claim | Type | Source |
|-------|------|--------|
| user_id | number | User.id |
| role | string | User.role.name |
| hierarchy_level | number | User.role.hierarchy_level |
| permissions_list | string[] | `["app.codename", ...]` |

---

## Key Enumerations Summary

| Name | Values | Used In |
|------|--------|---------|
| CrimeLevel | 1, 2, 3, 4 | Case.crime_level |
| CaseStatus | 17 string values | Case.status, CaseStatusLog |
| CaseCreationType | complaint, crime_scene | Case.creation_type |
| ComplainantStatus | pending, approved, rejected | CaseComplainant.status |
| EvidenceType | testimony, biological, vehicle, identity, other | Evidence.evidence_type |
| FileType | image, video, audio, document | EvidenceFile.file_type |
| SuspectStatus | 9 string values | Suspect.status |
| WarrantStatus | active, executed, expired, cancelled | Warrant.status |
| WarrantPriority | normal, high, critical | Warrant.priority |
| VerdictChoice | guilty, innocent | Trial.verdict |
| BountyTipStatus | pending, officer_reviewed, verified, rejected | BountyTip.status |
| SergeantApproval | pending, approved, rejected | Suspect.sergeant_approval_status |

---

## Timestamps

All entities (except Django auth's Permission) inherit `TimeStampedModel` providing:
- `created_at` — auto-set on creation (ISO 8601 string in API responses)
- `updated_at` — auto-set on save

The frontend should always expect these as ISO 8601 date-time strings.

# Evidence Services — Files, Chain-of-Custody & Coroner Verification Report

> **Branch:** `feat/evidence-services`  
> **Generated:** 2026-02-23  
> **Status:** Fully implemented — services, views, and serializers wired

---

## 1. Custody Log Rules

### When Custody Logs Are Generated

`EvidenceCustodyLog` entries are created automatically by the service layer whenever a significant physical handling event occurs on an evidence item. The following events produce custody log records:

| Trigger                          | `action_type`     | Service Method                                        | Notes Field Content                                                    |
| -------------------------------- | ----------------- | ----------------------------------------------------- | ---------------------------------------------------------------------- |
| **File uploaded** to evidence    | `checked_in`      | `EvidenceFileService.upload_file()`                   | `"File uploaded: <FileType> — <caption>"`                              |
| **Biological evidence verified** | `analysed`        | `MedicalExaminerService.verify_biological_evidence()`  | `"Biological evidence <approved/rejected> by Coroner. <result/notes>"` |

### Custody Log Model Fields

Each `EvidenceCustodyLog` row stores:

- **`evidence`** — FK to the parent `Evidence` record.
- **`handled_by`** — FK to the `User` who performed the action.
- **`action_type`** — One of: `checked_out`, `checked_in`, `transferred`, `disposed`, `analysed`.
- **`timestamp`** — Auto-set on creation (`auto_now_add`).
- **`notes`** — Free-text description of what happened.

### Retrieval

The `ChainOfCustodyService.get_chain_of_custody(evidence_id, user)` method returns all `EvidenceCustodyLog` entries for a given evidence item, ordered chronologically (oldest first). It enforces `VIEW_EVIDENCE` permission before returning data.

A secondary method, `ChainOfCustodyService.get_custody_trail(evidence)`, builds a **hybrid** audit trail that combines:

1. The initial registration event (from `Evidence.created_at`).
2. File upload events (from `EvidenceFile` records).
3. Verification events (from `BiologicalEvidence` fields).
4. All explicit `EvidenceCustodyLog` entries.

---

## 2. Verification Invariants

### Prerequisites for Coroner Verification

| #   | Invariant                                             | Enforcement Mechanism                                                                      | Error on Violation                                                    |
| --- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------- |
| 1   | Actor must have `can_verify_evidence` permission      | `examiner_user.has_perm("evidence.can_verify_evidence")` checked first                     | `PermissionDenied`: "Only the Coroner can verify biological evidence" |
| 2   | Evidence must be of type `BiologicalEvidence`         | `BiologicalEvidence.objects.get(pk=evidence_id)` — raises `DoesNotExist` if wrong type     | `NotFound`: "Biological evidence with id {id} not found"              |
| 3   | Evidence must NOT already be verified                 | `if bio_evidence.is_verified: raise DomainError(...)` — checked AFTER acquiring row lock   | `DomainError`: "This evidence has already been verified..."           |
| 4   | `forensic_result` required when `decision == approve` | `if not forensic_result.strip(): raise DomainError(...)`                                   | `DomainError`: "Forensic result is required when approving"           |
| 5   | `notes` required when `decision == reject`            | `if not notes.strip(): raise DomainError(...)`                                             | `DomainError`: "A rejection reason is required"                       |

### Irreversibility Mechanism

Verification is **one-way**: once `is_verified = True` is persisted, the service rejects all subsequent verification attempts. The check happens within a `transaction.atomic()` block with `select_for_update()`, ensuring that concurrent requests cannot race past the guard.

```
Request A ──▶ BEGIN TRANSACTION ──▶ SELECT ... FOR UPDATE ──▶ is_verified=False ──▶ SET True ──▶ COMMIT
Request B ──▶ BEGIN TRANSACTION ──▶ SELECT ... FOR UPDATE (blocks until A commits) ──▶ is_verified=True ──▶ RAISE DomainError
```

Even rejection records the Coroner's identity (`verified_by`) for audit trail purposes, but does NOT set `is_verified = True`, so the evidence can still be re-examined later.

### Verification Metadata Stored

On **approval**:

| Field              | Value                              |
| ------------------ | ---------------------------------- |
| `is_verified`      | `True`                             |
| `forensic_result`  | The Coroner's report text          |
| `verified_by`      | FK to the Coroner user             |

On **rejection**:

| Field              | Value                              |
| ------------------ | ---------------------------------- |
| `is_verified`      | `False` (unchanged)                |
| `forensic_result`  | `"REJECTED: <notes>"`             |
| `verified_by`      | FK to the Coroner user             |

### Post-Verification Actions

After persisting verification metadata:

1. An `EvidenceCustodyLog` entry with `action_type=analysed` is created.
2. A notification with `event_type="bio_evidence_verified"` is dispatched to the case's assigned detective via `NotificationService.create()`.

---

## 3. API Sequences

### 3.1 Uploading a File to an Evidence Record

**Endpoint:** `POST /api/evidence/{id}/files/`  
**Content-Type:** `multipart/form-data`  
**Permission:** `add_evidencefile`

```bash
curl -X POST http://localhost:8000/api/evidence/7/files/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@/path/to/bloodstain_photo.jpg" \
  -F "file_type=image" \
  -F "caption=Bloodstain on doorframe, north entrance"
```

**Response (201 Created):**

```json
{
    "id": 12,
    "file": "/media/evidence_files/2026/02/bloodstain_photo.jpg",
    "file_type": "image",
    "file_type_display": "Image",
    "caption": "Bloodstain on doorframe, north entrance",
    "created_at": "2026-02-23T14:30:00Z"
}
```

**Side effect:** An `EvidenceCustodyLog` entry is created:

```json
{
    "action_type": "checked_in",
    "handled_by": "<uploader_user_id>",
    "notes": "File uploaded: Image — Bloodstain on doorframe, north entrance"
}
```

### 3.2 Retrieving the Chain of Custody

**Endpoint:** `GET /api/evidence/{id}/chain-of-custody/`  
**Permission:** `view_evidence`

```bash
curl -X GET http://localhost:8000/api/evidence/7/chain-of-custody/ \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK):**

```json
[
    {
        "id": 1,
        "timestamp": "2026-02-20T10:30:00Z",
        "action": "Checked In",
        "performed_by": 3,
        "performer_name": "Officer Jane Doe",
        "details": "File uploaded: Image — Bloodstain on doorframe, north entrance"
    },
    {
        "id": 2,
        "timestamp": "2026-02-21T09:15:00Z",
        "action": "Analysed",
        "performed_by": 8,
        "performer_name": "Dr. Malcolm Stone",
        "details": "Biological evidence approved by Coroner. Blood type O+, matches suspect DNA profile."
    }
]
```

### 3.3 Coroner Verification — Approve

**Endpoint:** `POST /api/evidence/{id}/verify/`  
**Permission:** `can_verify_evidence`

```bash
curl -X POST http://localhost:8000/api/evidence/7/verify/ \
  -H "Authorization: Bearer <coroner_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "approve",
    "forensic_result": "Blood type O+, matches suspect DNA profile from case #42. Analysis conducted at LAPD Forensics Lab, reference #2026-0220.",
    "notes": "Sample integrity confirmed."
  }'
```

**Response (200 OK):**

```json
{
    "id": 7,
    "title": "Bloodstain on Doorframe",
    "description": "Blood residue found on north entrance doorframe",
    "evidence_type": "biological",
    "evidence_type_display": "Biological / Medical",
    "case": 5,
    "registered_by": 3,
    "registered_by_name": "Officer Jane Doe",
    "forensic_result": "Blood type O+, matches suspect DNA profile from case #42. Analysis conducted at LAPD Forensics Lab, reference #2026-0220.",
    "is_verified": true,
    "verified_by": 8,
    "verified_by_name": "Dr. Malcolm Stone",
    "files": [],
    "created_at": "2026-02-20T10:30:00Z",
    "updated_at": "2026-02-23T14:45:00Z"
}
```

### 3.4 Coroner Verification — Reject

```bash
curl -X POST http://localhost:8000/api/evidence/7/verify/ \
  -H "Authorization: Bearer <coroner_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "reject",
    "forensic_result": "",
    "notes": "Sample contaminated during transport — request a new collection from the crime scene."
  }'
```

**Response (200 OK):**

```json
{
    "id": 7,
    "forensic_result": "REJECTED: Sample contaminated during transport — request a new collection from the crime scene.",
    "is_verified": false,
    "verified_by": 8,
    "verified_by_name": "Dr. Malcolm Stone"
}
```

### 3.5 Error — Re-verification Attempt

```bash
# After evidence #7 has already been approved:
curl -X POST http://localhost:8000/api/evidence/7/verify/ \
  -H "Authorization: Bearer <coroner_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve", "forensic_result": "Updated result"}'
```

**Response (400 Bad Request):**

```json
{
    "detail": "This evidence has already been verified. Verification is irreversible."
}
```

---

## 4. Architecture Summary

### Modified Files

| File                              | Changes                                                                                     |
| --------------------------------- | ------------------------------------------------------------------------------------------- |
| `evidence/services.py`           | `EvidenceFileService.list_files()`, `upload_file()` with custody logging; `ChainOfCustodyService.get_chain_of_custody()` with permission checks; `MedicalExaminerService.verify_biological_evidence()` with `select_for_update()`, custody logging, and `bio_evidence_verified` notification |
| `evidence/views.py`              | Updated `files` and `chain_of_custody` actions to use new service signatures                |
| `evidence/serializers.py`        | `ChainOfCustodyEntrySerializer` converted to `ModelSerializer` for `EvidenceCustodyLog`     |
| `core/domain/notifications.py`   | Added `bio_evidence_verified` event template                                                |

### Separation of Concerns

All business logic — permission checks, race-condition prevention, custody log creation, notification dispatch — resides exclusively in `services.py`. Views remain thin wrappers that parse input, delegate to services, and serialize output.

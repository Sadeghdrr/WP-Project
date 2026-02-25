# Evidence Services — Polymorphic CRUD Implementation Report

## 1. Evidence Type Mapping Table

| `evidence_type` value | Django Model             | Required Fields                                                         | Notes                                                                 |
|------------------------|--------------------------|-------------------------------------------------------------------------|-----------------------------------------------------------------------|
| `testimony`            | `TestimonyEvidence`      | `case`, `title`, `statement_text`                                       | Transcript required; optional media files via `/files/` endpoint      |
| `biological`           | `BiologicalEvidence`     | `case`, `title`                                                         | `forensic_result` must be empty on creation (pending Coroner review)  |
| `vehicle`              | `VehicleEvidence`        | `case`, `title`, `vehicle_model`, `color`, **one of** `license_plate` / `serial_number` | XOR constraint: exactly one identifier required                |
| `identity`             | `IdentityEvidence`       | `case`, `title`, `owner_full_name`                                      | `document_details` (JSON key-value) optional, zero pairs valid        |
| `other`                | `Evidence` (base model)  | `case`, `title`                                                         | No child table; `evidence_type` set explicitly to `"other"`           |

All types also accept an optional `description` field.

---

## 2. Validation Rules

### 2.1 Vehicle — XOR Constraint (`license_plate` ⊕ `serial_number`)

- **Rule**: Exactly one of `license_plate` or `serial_number` must be non-empty. Providing both or neither is rejected.
- **Enforced at**:
  1. `VehicleEvidenceCreateSerializer.validate()` — serializer-level (HTTP 400 before hitting the DB).
  2. `EvidenceProcessingService._validate_vehicle()` — service-level (defence in depth).
  3. `VehicleEvidence.Meta.constraints` — DB-level `CheckConstraint` (`vehicle_plate_xor_serial`).
- **On update (PATCH)**: `VehicleEvidenceUpdateSerializer.validate()` merges incoming values with existing instance data before applying the same XOR check.

### 2.2 Biological / Medical — Forensic Result Guard

- `forensic_result` must be **empty** on creation. It is populated exclusively through the Coroner verification workflow (`POST /api/evidence/{id}/verify/`).
- A `DomainError` is raised if a non-empty `forensic_result` is submitted during creation.

### 2.3 Testimony — Transcript Required

- `statement_text` (the witness transcript) must be a non-empty string.
- A `DomainError` is raised if it is blank or omitted.

### 2.4 Identity Document — Owner Name + Dynamic Key-Value

- `owner_full_name` is required and must be non-empty.
- `document_details` (if provided) must be a flat JSON object where every key and every value is a string. Zero pairs is valid.

### 2.5 Permission Checks

All service methods verify the requesting user's permissions via `user.has_perm()`:

| Operation        | Required Permission                      |
|------------------|------------------------------------------|
| Create evidence  | `evidence.add_evidence`                  |
| Update evidence  | `evidence.change_evidence`               |
| Delete evidence  | `evidence.delete_evidence`               |
| Upload file      | `evidence.add_evidencefile`              |
| Delete file      | `evidence.delete_evidencefile`           |
| Verify (Coroner) | `evidence.can_verify_evidence`           |

### 2.6 Delete Guard — Verified Biological Evidence

Verified biological evidence (`is_verified == True`) cannot be deleted unless the requesting user is a superuser.

---

## 3. API Sequences — Sample Payloads

### 3.1 Create Vehicle Evidence

```bash
curl -X POST /api/evidence/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "evidence_type": "vehicle",
    "case": 42,
    "title": "Blue Sedan Near Alley",
    "description": "Found parked 50m from the crime scene.",
    "vehicle_model": "Ford Sedan 1947",
    "color": "Blue",
    "license_plate": "LA-4521"
  }'
```

**Response (201 Created):**
```json
{
  "id": 1,
  "title": "Blue Sedan Near Alley",
  "description": "Found parked 50m from the crime scene.",
  "evidence_type": "vehicle",
  "evidence_type_display": "Vehicle",
  "case": 42,
  "registered_by": 12,
  "registered_by_name": "John Smith",
  "vehicle_model": "Ford Sedan 1947",
  "color": "Blue",
  "license_plate": "LA-4521",
  "serial_number": "",
  "files": [],
  "created_at": "2026-02-23T10:30:00Z",
  "updated_at": "2026-02-23T10:30:00Z"
}
```

### 3.2 Create Biological / Medical Evidence

```bash
curl -X POST /api/evidence/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "evidence_type": "biological",
    "case": 42,
    "title": "Bloodstain on Doorframe",
    "description": "Found at scene entrance, approximately 5cm diameter."
  }'
```

**Response (201 Created):**
```json
{
  "id": 2,
  "title": "Bloodstain on Doorframe",
  "description": "Found at scene entrance, approximately 5cm diameter.",
  "evidence_type": "biological",
  "evidence_type_display": "Biological / Medical",
  "case": 42,
  "registered_by": 12,
  "registered_by_name": "John Smith",
  "forensic_result": "",
  "is_verified": false,
  "verified_by": null,
  "verified_by_name": null,
  "files": [],
  "created_at": "2026-02-23T10:35:00Z",
  "updated_at": "2026-02-23T10:35:00Z"
}
```

### 3.3 Create Testimony Evidence

```bash
curl -X POST /api/evidence/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "evidence_type": "testimony",
    "case": 42,
    "title": "Eyewitness Account — Mrs. Flores",
    "description": "Neighbor who saw the suspect leaving the building.",
    "statement_text": "I saw a tall man in a dark coat leave through the back door at approximately 11:30 PM. He was carrying a briefcase."
  }'
```

**Response (201 Created):**
```json
{
  "id": 3,
  "title": "Eyewitness Account — Mrs. Flores",
  "description": "Neighbor who saw the suspect leaving the building.",
  "evidence_type": "testimony",
  "evidence_type_display": "Witness / Local Testimony",
  "case": 42,
  "registered_by": 12,
  "registered_by_name": "John Smith",
  "statement_text": "I saw a tall man in a dark coat leave through the back door at approximately 11:30 PM. He was carrying a briefcase.",
  "files": [],
  "created_at": "2026-02-23T10:40:00Z",
  "updated_at": "2026-02-23T10:40:00Z"
}
```

### 3.4 Create Identity Document Evidence

```bash
curl -X POST /api/evidence/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "evidence_type": "identity",
    "case": 42,
    "title": "Driver License Found at Scene",
    "description": "Found near the victim.",
    "owner_full_name": "Robert J. Morrison",
    "document_details": {
      "ID Number": "D-1947-0812",
      "Issue Date": "1945-03-15",
      "Issuing State": "California"
    }
  }'
```

---

## 4. Architecture Notes

- **Fat Services, Skinny Views**: All polymorphic dispatch, validation, permission checks, DB transactions, and notifications reside in `services.py`. Views only parse input, delegate, and serialize responses.
- **`transaction.atomic()`**: Every create/update/delete operation is wrapped in an atomic transaction to ensure the base `Evidence` row and its child subtype are created safely.
- **Notifications**: When new evidence is added, a notification is dispatched to the case's `assigned_detective` (if any) via `NotificationService.create()` with `event_type="evidence_added"`.
- **Role-Scoped Queries**: `EvidenceQueryService.get_filtered_queryset()` first enforces `evidence.view_evidence`, then scopes evidence by the requester's visible case set (from case-query RBAC rules) with a fallback role-scope map for roles outside case scope config.
- **Domain Exceptions**: Service methods raise `core.domain.exceptions.PermissionDenied`, `NotFound`, or `DomainError`. These are automatically mapped to HTTP 403, 404, or 400 by the global `domain_exception_handler` registered in DRF settings.

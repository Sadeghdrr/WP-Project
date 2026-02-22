# Evidence App — API Design Report

> **Branch:** `feat/evidence-api-drafts`  
> **Generated:** 2026-02-22  
> **Status:** Structural drafts — `raise NotImplementedError` stubs only

---

## 1. Endpoint Table

| HTTP Method | URL                                    | Purpose                                               | Access Level                                                              |
| ----------- | -------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------- |
| `GET`       | `/api/evidence/`                       | List all evidence (filtered, role-scoped)             | Authenticated (role-scoped visibility)                                    |
| `POST`      | `/api/evidence/`                       | Create new evidence (polymorphic by `evidence_type`)  | `add_evidence` permission                                                 |
| `GET`       | `/api/evidence/{id}/`                  | Retrieve full evidence detail (type-specific fields)  | `view_evidence` permission                                                |
| `PATCH`     | `/api/evidence/{id}/`                  | Partially update mutable evidence fields              | `change_evidence` permission                                              |
| `DELETE`    | `/api/evidence/{id}/`                  | Delete evidence item permanently                      | `delete_evidence` permission                                              |
| `POST`      | `/api/evidence/{id}/verify/`           | Coroner verifies biological evidence (approve/reject) | **Coroner role** — `can_verify_evidence` + `can_register_forensic_result` |
| `POST`      | `/api/evidence/{id}/link-case/`        | Link evidence to a (different) case                   | `change_evidence` permission                                              |
| `POST`      | `/api/evidence/{id}/unlink-case/`      | Unlink evidence from its current case                 | `change_evidence` permission                                              |
| `GET`       | `/api/evidence/{id}/files/`            | List all file attachments for an evidence item        | `view_evidencefile` permission                                            |
| `POST`      | `/api/evidence/{id}/files/`            | Upload a new file attachment                          | `add_evidencefile` permission                                             |
| `GET`       | `/api/evidence/{id}/chain-of-custody/` | Read-only audit trail of evidence handling history    | `view_evidence` permission                                                |

### URL Registration

All routes are registered via DRF's `DefaultRouter` under the `evidence` prefix:

```python
# evidence/urls.py
router = DefaultRouter()
router.register(prefix=r"evidence", viewset=EvidenceViewSet, basename="evidence")
urlpatterns = router.urls
```

Included in the project root at `backend/urls.py`:

```python
path('api/', include('evidence.urls')),
```

Workflow-specific endpoints (`verify`, `link-case`, `unlink-case`, `files`, `chain-of-custody`) use DRF's `@action` decorator on the `EvidenceViewSet`, so they are automatically routed by the router.

---

## 2. Vehicle XOR Validation — Technical Implementation

### Business Rule (project-doc §4.3.3)

> A vehicle connected to the crime scene must have its license plate registered. If a vehicle **lacks** a license plate, its serial number must be entered. The license plate number and the serial number **cannot both have a value** at the same time.

This is a strict **XOR (exclusive-or) constraint**: exactly one of `license_plate` or `serial_number` must be non-empty.

### Three-Layer Defence

The XOR constraint is enforced at **three levels**, each serving a distinct purpose:

#### Layer 1: Serializer Validation (API Boundary)

**File:** `evidence/serializers.py` — `VehicleEvidenceCreateSerializer.validate()`

This is the **first line of defence**. When the frontend submits a vehicle evidence payload, the serializer's `validate()` method inspects both fields _before_ the request reaches the service layer or database:

```python
def validate(self, attrs):
    plate = attrs.get("license_plate", "").strip()
    serial = attrs.get("serial_number", "").strip()
    has_plate = bool(plate)
    has_serial = bool(serial)

    if has_plate and has_serial:
        raise ValidationError(
            "Provide either a license plate or a serial number, not both."
        )
    if not has_plate and not has_serial:
        raise ValidationError(
            "Either a license plate or a serial number must be provided."
        )
    return attrs
```

**On update (PATCH)**, the `VehicleEvidenceUpdateSerializer.validate()` handles partial payloads by merging incoming values with the existing instance:

```python
def validate(self, attrs):
    plate = attrs.get("license_plate", self.instance.license_plate).strip()
    serial = attrs.get("serial_number", self.instance.serial_number).strip()
    # same XOR check as create...
```

This ensures that updating _only_ the `license_plate` on a vehicle that already has a `serial_number` is correctly rejected.

#### Layer 2: Service Layer Guard

**File:** `evidence/services.py` — `EvidenceProcessingService.process_new_evidence()`

The service layer receives already-validated data from the serializer, but an additional guard exists as a defence-in-depth measure. If a vehicle evidence object somehow reaches `process_new_evidence` with both fields populated (e.g., from an internal API call bypassing serializers), the database constraint (Layer 3) will catch it.

#### Layer 3: Database CHECK Constraint

**File:** `evidence/models.py` — `VehicleEvidence.Meta.constraints`

```python
constraints = [
    models.CheckConstraint(
        condition=(
            models.Q(license_plate="", serial_number__gt="")
            | models.Q(license_plate__gt="", serial_number="")
        ),
        name="vehicle_plate_xor_serial",
    ),
]
```

This is the **last line of defence**. Even if all application-level validation is bypassed (e.g., raw SQL, Django shell), the database itself will reject the row and raise an `IntegrityError`.

### Error Response Examples

**Both provided:**

```json
{
  "non_field_errors": [
    "Provide either a license plate or a serial number, not both."
  ]
}
```

**Neither provided:**

```json
{
  "non_field_errors": [
    "Either a license plate or a serial number must be provided."
  ]
}
```

---

## 3. Medical Examiner (Coroner) Verification Workflow

### Business Rule (project-doc §3.1.2 + §4.3.2)

> The **Coroner** is responsible for examining and either verifying or rejecting biological and medical evidence. Evidence such as bloodstains, hair strands, or fingerprints must be examined and verified by the Coroner or the national identity database.

### Workflow Diagram

```
┌──────────────┐     Registered by      ┌───────────────────┐
│  Any Officer │  ──────────────────────▶│ BiologicalEvidence │
│  / Detective │     (is_verified=False) │  (Pending Review)  │
└──────────────┘                         └─────────┬─────────┘
                                                   │
                                    ┌──────────────┴──────────────┐
                                    │  Coroner Reviews Evidence   │
                                    │  POST /evidence/{id}/verify/│
                                    └──────────────┬──────────────┘
                                                   │
                              ┌────────────────────┼────────────────────┐
                              │                                        │
                    ┌─────────▼─────────┐                ┌─────────────▼─────────┐
                    │   decision:       │                │   decision:            │
                    │   "approve"       │                │   "reject"             │
                    │                   │                │                        │
                    │ is_verified=True  │                │ is_verified=False      │
                    │ forensic_result=  │                │ forensic_result=       │
                    │   <lab report>    │                │   "REJECTED: <reason>" │
                    │ verified_by=      │                │ verified_by=           │
                    │   <coroner_user>  │                │   <coroner_user>       │
                    └─────────┬─────────┘                └─────────────┬─────────┘
                              │                                        │
                    ┌─────────▼─────────┐                ┌─────────────▼─────────┐
                    │ Notification sent │                │ Notification sent      │
                    │ to Detective      │                │ to Detective           │
                    └───────────────────┘                └───────────────────────┘
```

### Endpoint Details

**URL:** `POST /api/evidence/{id}/verify/`

**Request Body:**

```json
{
  "decision": "approve",
  "forensic_result": "Blood type O+, matches suspect DNA profile from case #42.",
  "notes": "Analysis conducted at LAPD Forensics Lab, reference #2026-0220."
}
```

**Successful Response (200):**

```json
{
    "id": 7,
    "title": "Bloodstain on Doorframe",
    "evidence_type": "biological",
    "forensic_result": "Blood type O+, matches suspect DNA profile from case #42.",
    "is_verified": true,
    "verified_by": 8,
    "verified_by_name": "Dr. Malcolm Stone",
    "case": 5,
    "files": [...],
    "created_at": "2026-02-20T10:30:00Z",
    "updated_at": "2026-02-21T09:15:00Z"
}
```

### Service Layer Enforcement

**File:** `evidence/services.py` — `MedicalExaminerService.verify_biological_evidence()`

The service method enforces the following checks in order:

| #   | Check                                                           | Error Type        | Message                                            |
| --- | --------------------------------------------------------------- | ----------------- | -------------------------------------------------- |
| 1   | User has `evidence.can_verify_evidence` permission              | `PermissionError` | "Only the Coroner can verify biological evidence." |
| 2   | Evidence PK exists and is `BiologicalEvidence`                  | `DoesNotExist`    | HTTP 404                                           |
| 3   | Evidence is not already verified (`is_verified == False`)       | `ValidationError` | "This evidence has already been verified."         |
| 4   | If `decision == "approve"`: `forensic_result` must be non-blank | `ValidationError` | "Forensic result is required when approving."      |
| 5   | If `decision == "reject"`: `notes` must be non-blank            | `ValidationError` | "A rejection reason is required."                  |

### Permission Chain

```
User.role  ──FK──▶  Role  ──M2M──▶  Permission
                      │
                      │  (setup_rbac assigns these to Coroner role)
                      ├── evidence.can_verify_evidence
                      └── evidence.can_register_forensic_result
```

The `User.has_perm()` override in `accounts.models` resolves permission checks through the role's M2M relationship to Django's `Permission` model. The service checks `has_perm("evidence.can_verify_evidence")` — this is a **defence-in-depth** check (the view restricts the endpoint to authenticated users, but the service verifies the specific Coroner permission).

### Key Design Decisions

1. **Verification is irreversible:** Once `is_verified = True`, the service rejects subsequent verification attempts. Admin-level intervention (direct DB edit) is required to un-verify.

2. **Rejection records the examiner:** Even on rejection, `verified_by` is set to the Coroner so there is an audit trail of who examined the evidence and when.

3. **Forensic result on rejection:** The `forensic_result` field is set to `"REJECTED: <notes>"` so the rejection reason is permanently stored alongside the evidence record.

4. **Notification dispatch:** After verification, the service dispatches a `Notification` to the case's assigned detective to inform them of the outcome (per §4.4: "a notification must be sent to the Detective").

---

## 4. Architecture Summary

### File Structure

```
backend/evidence/
├── models.py        — Evidence, TestimonyEvidence, BiologicalEvidence,
│                      VehicleEvidence, IdentityEvidence, EvidenceFile
├── serializers.py   — Filter, Read (list + 5 detail), Write (5 create + 5 update),
│                      Workflow (verify, link/unlink), File, ChainOfCustody
├── services.py      — EvidenceQueryService, EvidenceProcessingService,
│                      MedicalExaminerService, EvidenceFileService,
│                      ChainOfCustodyService
├── views.py         — EvidenceViewSet (thin — delegates to services)
├── urls.py          — DefaultRouter registration
└── admin.py         — Admin registrations (pre-existing)
```

### Separation of Concerns

| Layer          | Responsibility                                                       | Example                                               |
| -------------- | -------------------------------------------------------------------- | ----------------------------------------------------- |
| **Serializer** | Input parsing, field validation, XOR constraint check                | `VehicleEvidenceCreateSerializer.validate()`          |
| **View**       | HTTP plumbing, serializer dispatch, response wrapping                | `EvidenceViewSet.create()`                            |
| **Service**    | Business logic, permission enforcement, state changes, notifications | `MedicalExaminerService.verify_biological_evidence()` |
| **Model**      | Data schema, DB constraints, `save()` hooks                          | `VehicleEvidence.Meta.constraints`                    |

### Polymorphic Strategy

Evidence creation uses a **discriminator-based dispatch** pattern:

1. Frontend sends `evidence_type` in the request body.
2. `EvidencePolymorphicCreateSerializer` validates the discriminator.
3. The view resolves the appropriate child serializer via `_SERIALIZER_MAP`.
4. The validated data is passed to `EvidenceProcessingService.process_new_evidence()`.
5. The service resolves the appropriate model class via `_MODEL_MAP`.
6. The correct child table row is created via multi-table inheritance.

This avoids separate endpoints per evidence type while maintaining strong type safety through dedicated serializers.

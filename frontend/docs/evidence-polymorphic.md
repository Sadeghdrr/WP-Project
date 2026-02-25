# Evidence Polymorphic Create — Frontend Integration Guide

> Mapping frontend form → backend `POST /api/evidence/` (polymorphic).

## Endpoint

| Method | URL              | Auth | Content-Type       |
|--------|------------------|------|--------------------|
| POST   | `/api/evidence/` | JWT  | `application/json` |

The backend `EvidencePolymorphicCreateSerializer` dispatches to the correct
child serializer based on the `evidence_type` discriminator field.

---

## Evidence Types & Field Matrix

### Common Fields (all types)

| Field            | Type    | Required | Notes                         |
|------------------|---------|----------|-------------------------------|
| `evidence_type`  | string  | ✔        | Discriminator (see below)     |
| `case`           | integer | ✔        | FK to Case                    |
| `title`          | string  | ✔        | max_length=200                |
| `description`    | string  | ✘        | May be blank / omitted        |

### Type-Specific Fields

#### `testimony`

| Field            | Type   | Required | Notes              |
|------------------|--------|----------|--------------------|
| `statement_text` | string | ✘        | Witness statement  |

#### `biological`

No additional fields. The `forensic_result` and `is_verified` fields are
set post-creation via the `/verify/` endpoint by a Coroner.

#### `vehicle`

| Field            | Type   | Required | Default | Constraint                |
|------------------|--------|----------|---------|---------------------------|
| `vehicle_model`  | string | ✔        | —       | max_length=150            |
| `color`          | string | ✔        | —       | max_length=50             |
| `license_plate`  | string | ✘        | `""`    | XOR with `serial_number`  |
| `serial_number`  | string | ✘        | `""`    | XOR with `license_plate`  |

**XOR Constraint** (DB CHECK + serializer validation):

- Provide **exactly one** of `license_plate` or `serial_number`.
- Both filled → `"Provide either a license plate or a serial number, not both."`
- Both empty → `"Either a license plate or a serial number must be provided."`
- These are raised as `non_field_errors` by the backend.

**Frontend handling**: The form uses a radio toggle (Plate / Serial) and always
sends both fields — the selected one with its value, the other as `""`.

#### `identity`

| Field              | Type              | Required | Notes                     |
|--------------------|-------------------|----------|---------------------------|
| `owner_full_name`  | string            | ✔        | max_length=200            |
| `document_details` | `Record<str,str>` | ✘        | Flat dict, string→string  |

Backend validation on `document_details`:
- Must be a flat dict (no nested structures)
- Both keys and values must be strings
- Error: `"document_details must be a flat dictionary of string→string."`

#### `other`

No additional fields.

---

## Example Payloads

### Testimony

```json
{
  "evidence_type": "testimony",
  "case": 42,
  "title": "Eyewitness Statement",
  "description": "Witness saw the suspect at 10pm.",
  "statement_text": "I saw a man wearing a black jacket..."
}
```

### Vehicle (license plate)

```json
{
  "evidence_type": "vehicle",
  "case": 42,
  "title": "Suspect Vehicle",
  "vehicle_model": "Honda Civic 2019",
  "color": "Silver",
  "license_plate": "ABC-1234",
  "serial_number": ""
}
```

### Vehicle (serial number)

```json
{
  "evidence_type": "vehicle",
  "case": 42,
  "title": "Abandoned Car",
  "vehicle_model": "Toyota Camry",
  "color": "White",
  "license_plate": "",
  "serial_number": "1HGBH41JXMN109186"
}
```

### Identity

```json
{
  "evidence_type": "identity",
  "case": 42,
  "title": "Suspect Passport",
  "owner_full_name": "Ali Hosseini",
  "document_details": {
    "passport_number": "P12345678",
    "issuing_country": "IR",
    "expiry_date": "2028-01-15"
  }
}
```

---

## Error Response Mapping

Backend returns DRF standard validation errors:

```json
{
  "title": ["This field is required."],
  "non_field_errors": ["Provide either a license plate or a serial number, not both."]
}
```

The `normaliseError()` function in `api/client.ts` maps this into:

```ts
{
  ok: false,
  status: 400,
  error: {
    message: "Provide either a license plate or a serial number, not both.",
    fieldErrors: {
      title: ["This field is required."],
      non_field_errors: ["..."]
    }
  }
}
```

`AddEvidencePage` then:
1. Maps `fieldErrors` (excluding `non_field_errors`) into inline field errors
2. Sets the `error.message` as the form-level general error

---

## Frontend Files

| File | Purpose |
|------|---------|
| `src/types/evidence.ts` | TypeScript types matching backend models & serializers |
| `src/api/evidence.ts` | API service layer (all evidence endpoints) |
| `src/hooks/useEvidence.ts` | React Query hooks (list, detail, mutations) |
| `src/pages/Evidence/AddEvidencePage.tsx` | Polymorphic create form |
| `src/pages/Evidence/EvidenceListPage.tsx` | Case-filtered evidence list |
| `src/pages/Evidence/EvidenceDetailPage.tsx` | Detail view (type-specific rendering) |
| `src/lib/evidenceHelpers.ts` | Labels, colors, icons for evidence types |
| `src/pages/Cases/CaseDetailPage.tsx` | EvidenceSection component (inline list + register) |

---

## Backend Source (authoritative)

| File | Key classes |
|------|------------|
| `backend/evidence/models.py` | `Evidence`, `TestimonyEvidence`, `BiologicalEvidence`, `VehicleEvidence`, `IdentityEvidence` |
| `backend/evidence/serializers.py` | `EvidencePolymorphicCreateSerializer` + per-type create serializers |
| `backend/evidence/views.py` | `EvidenceViewSet.create()` — two-phase validation then `EvidenceProcessingService` |

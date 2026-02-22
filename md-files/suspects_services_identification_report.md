# Suspects Services — Identification & Sergeant Approval Report

## 1. State Transitions

### 1.1 Suspect Status Lifecycle (Identification Slice)

```
Detective creates suspect
        │
        ▼
┌─────────────────────────┐
│  status = WANTED        │
│  sergeant_approval =    │
│       "pending"         │
└────────────┬────────────┘
             │
     Sergeant reviews
             │
    ┌────────┴────────┐
    ▼                 ▼
┌──────────┐   ┌───────────┐
│ APPROVED │   │ REJECTED  │
│          │   │           │
│ approval │   │ approval  │
│ ="approved"  │ ="rejected"│
│          │   │ + message │
└──────────┘   └───────────┘
```

### 1.2 Field Changes Per Transition

| Action | `status` | `sergeant_approval_status` | `approved_by_sergeant` | `sergeant_rejection_message` | `wanted_since` |
|--------|----------|---------------------------|------------------------|------------------------------|----------------|
| **Detective creates suspect** | `wanted` | `pending` | `NULL` | `""` | Auto-set (now) |
| **Sergeant approves** | `wanted` (unchanged) | `approved` | Set to sergeant user | `""` (unchanged) | Unchanged |
| **Sergeant rejects** | `wanted` (unchanged) | `rejected` | Set to sergeant user | Set to rejection message | Unchanged |

> **Note:** On rejection, the `status` field remains `wanted`. The case stays open for the Detective to gather more evidence and potentially re-identify suspects. The `sergeant_approval_status` tracks the approval workflow independently from the suspect lifecycle status.

---

## 2. Notification Events

### 2.1 `suspect_needs_review`

**Trigger:** Detective creates a new suspect (`SuspectProfileService.create_suspect`).

**Recipient:** The Sergeant assigned to the case (`case.assigned_sergeant`).

**Payload structure:**
```json
{
    "suspect_id": 42,
    "suspect_name": "Roy Earle",
    "case_id": 5,
    "case_title": "Hollywood Murder",
    "identified_by": "Det. Cole Phelps"
}
```

**Notification record fields:**
| Field | Value |
|-------|-------|
| `title` | `"Suspect Pending Review"` |
| `message` | `"A new suspect has been identified and requires your review."` |
| `content_type` | `ContentType` for `Suspect` model |
| `object_id` | Suspect PK |

---

### 2.2 `suspect_approved`

**Trigger:** Sergeant approves a suspect identification (`ArrestAndWarrantService.approve_or_reject_suspect` with `decision="approve"`).

**Recipient:** The Detective who identified the suspect (`suspect.identified_by`).

**Payload structure:**
```json
{
    "suspect_id": 42,
    "suspect_name": "Roy Earle",
    "case_id": 5,
    "case_title": "Hollywood Murder",
    "approved_by": "Sgt. Rusty Galloway"
}
```

**Notification record fields:**
| Field | Value |
|-------|-------|
| `title` | `"Suspect Approved"` |
| `message` | `"A suspect in your case has been approved."` |
| `content_type` | `ContentType` for `Suspect` model |
| `object_id` | Suspect PK |

---

### 2.3 `suspect_rejected`

**Trigger:** Sergeant rejects a suspect identification (`ArrestAndWarrantService.approve_or_reject_suspect` with `decision="reject"`).

**Recipient:** The Detective who identified the suspect (`suspect.identified_by`).

**Payload structure:**
```json
{
    "suspect_id": 42,
    "suspect_name": "Roy Earle",
    "case_id": 5,
    "case_title": "Hollywood Murder",
    "rejected_by": "Sgt. Rusty Galloway",
    "rejection_message": "Insufficient evidence linking suspect to case."
}
```

**Notification record fields:**
| Field | Value |
|-------|-------|
| `title` | `"Suspect Rejected"` |
| `message` | `"A suspect in your case has been rejected."` |
| `content_type` | `ContentType` for `Suspect` model |
| `object_id` | Suspect PK |

---

## 3. API Sequences

### 3.1 Detective Creates a Suspect

```bash
curl -X POST http://localhost:8000/api/suspects/suspects/ \
  -H "Authorization: Bearer <detective_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "case": 5,
    "full_name": "Roy Earle",
    "national_id": "1234567890",
    "phone_number": "+1-213-555-0147",
    "address": "742 S. Broadway, Los Angeles",
    "description": "Tall, dark hair, scar on left cheek."
  }'
```

**Response (201 Created):**
```json
{
    "id": 42,
    "full_name": "Roy Earle",
    "national_id": "1234567890",
    "phone_number": "+1-213-555-0147",
    "photo": null,
    "address": "742 S. Broadway, Los Angeles",
    "description": "Tall, dark hair, scar on left cheek.",
    "status": "wanted",
    "status_display": "Wanted",
    "case": 5,
    "case_title": "Hollywood Murder",
    "user": null,
    "wanted_since": "2026-02-23T10:30:00Z",
    "days_wanted": 0,
    "is_most_wanted": false,
    "most_wanted_score": 0,
    "reward_amount": 0,
    "identified_by": 12,
    "identified_by_name": "Cole Phelps",
    "approved_by_sergeant": null,
    "approved_by_name": null,
    "sergeant_approval_status": "pending",
    "sergeant_rejection_message": "",
    "interrogations": [],
    "trials": [],
    "bails": [],
    "bounty_tip_count": 0,
    "created_at": "2026-02-23T10:30:00Z",
    "updated_at": "2026-02-23T10:30:00Z"
}
```

**Side effect:** A `suspect_needs_review` notification is dispatched to the Sergeant assigned to Case #5.

---

### 3.2 Sergeant Rejects the Suspect with a Message

```bash
curl -X POST http://localhost:8000/api/suspects/suspects/42/approve/ \
  -H "Authorization: Bearer <sergeant_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "reject",
    "rejection_message": "Insufficient evidence. Only one witness places suspect near the scene."
  }'
```

**Response (200 OK):**
```json
{
    "id": 42,
    "full_name": "Roy Earle",
    "status": "wanted",
    "status_display": "Wanted",
    "sergeant_approval_status": "rejected",
    "sergeant_rejection_message": "Insufficient evidence. Only one witness places suspect near the scene.",
    "approved_by_sergeant": 8,
    "approved_by_name": "Rusty Galloway",
    "...": "..."
}
```

**Side effect:** A `suspect_rejected` notification is dispatched to the Detective (user #12) with the rejection message.

**Validation errors:**
- If `rejection_message` is blank when `decision="reject"` → HTTP 400:
  ```json
  {"rejection_message": ["A rejection message is required."]}
  ```
- If suspect is not in `pending` approval status → HTTP 400:
  ```json
  {"detail": "Suspect approval has already been processed."}
  ```
- If user lacks `CAN_APPROVE_SUSPECT` permission → HTTP 403:
  ```json
  {"detail": "Only a Sergeant (or higher) can approve/reject suspects."}
  ```

---

### 3.3 Sergeant Approves the Suspect

```bash
curl -X POST http://localhost:8000/api/suspects/suspects/42/approve/ \
  -H "Authorization: Bearer <sergeant_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve"}'
```

**Response (200 OK):**
```json
{
    "id": 42,
    "full_name": "Roy Earle",
    "status": "wanted",
    "status_display": "Wanted",
    "sergeant_approval_status": "approved",
    "sergeant_rejection_message": "",
    "approved_by_sergeant": 8,
    "approved_by_name": "Rusty Galloway",
    "...": "..."
}
```

**Side effect:** A `suspect_approved` notification is dispatched to the Detective (user #12). The suspect is now eligible for arrest warrant issuance.

---

## 4. Permission Matrix

| Action | Required Permission | Typical Role |
|--------|-------------------|--------------|
| Create suspect | `suspects.can_identify_suspect` | Detective |
| Update suspect profile | `suspects.change_suspect` | Detective+ |
| Approve/reject suspect | `suspects.can_approve_suspect` | Sergeant |

---

## 5. Files Modified

| File | Changes |
|------|---------|
| `backend/suspects/services.py` | Implemented `SuspectProfileService.create_suspect`, `update_suspect`, `get_filtered_queryset`, `get_suspect_detail`, `get_most_wanted_list`; Implemented `ArrestAndWarrantService.approve_or_reject_suspect` |
| `backend/suspects/views.py` | Implemented `SuspectViewSet._get_suspect`, `list`, `create`, `retrieve`, `partial_update`, `most_wanted`, `approve` |
| `backend/suspects/serializers.py` | Implemented `SuspectFilterSerializer.validate`, `SuspectApprovalSerializer.validate`, all `get_*` methods on `SuspectListSerializer`, `SuspectDetailSerializer`, `InterrogationInlineSerializer`, `TrialInlineSerializer`, `BailInlineSerializer`, `MostWantedSerializer` |
| `backend/core/domain/notifications.py` | Added `suspect_needs_review` event type to `_EVENT_TEMPLATES` |
